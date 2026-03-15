"""
evaluation.py

Evaluation helpers for the ML-AUTOC thesis website backend.

This module is intentionally evaluation-only:
- no directory walking
- no file loading loops
- no plotting
- no command-line execution

Inputs
------
delta : ndarray of shape (n, L)
    Marginal benefit matrix.

policy_outputs : dict[str, ndarray]
    Outputs returned by solvers.py.

Conventions
-----------
Ranking-based policies return arrays of shape (B, 2), where each row is
[i, level_index].

PAG* returns a cumulative allocation-by-budget matrix of shape (B, n*L),
where row b-1 is the allocation after budget b.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from solvers import compute_random_baseline

POLICY_DISPLAY_NAMES: dict[str, str] = {
    "lfp": "LFP",
    "pag": "PAG",
    "pag_star": "PAG*",
    "ifp": "IFP",
    "pgp": "PGP",
}


def _validate_delta(delta: np.ndarray) -> tuple[int, int, int]:
    if not isinstance(delta, np.ndarray):
        raise TypeError("delta must be a numpy ndarray.")

    if delta.ndim != 2:
        raise ValueError("delta must be 2D with shape (n, L).")

    n, L = delta.shape

    if n <= 0:
        raise ValueError("delta must have at least one patient.")
    if L <= 0:
        raise ValueError("delta must have at least one treatment level.")

    B = n * L
    return n, L, B


def _validate_baseline(baseline: np.ndarray, B: int) -> np.ndarray:
    baseline = np.asarray(baseline, dtype=float)

    if baseline.ndim != 1:
        raise ValueError("baseline must be a 1D array.")

    if baseline.shape[0] != B:
        raise ValueError(f"baseline must have length {B}, got {baseline.shape[0]}.")

    return baseline


def toc_from_alloc_matrix(
    alloc: np.ndarray,
    delta: np.ndarray,
    baseline: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Evaluate a cumulative allocation-by-budget matrix.

    Parameters
    ----------
    alloc : ndarray
        Either shape (B, n*L) or (B, n, L).
    delta : ndarray
        Shape (n, L).
    baseline : ndarray
        Shape (B,).

    Returns
    -------
    toc : ndarray
        ML-AUTOC curve = average ATE minus random baseline.
    avg : ndarray
        Average ATE at each budget.
    total : ndarray
        Total realized treatment effect at each budget.
    """
    n, L, B = _validate_delta(delta)
    baseline = _validate_baseline(baseline, B)

    delta_flat = delta.reshape(B)

    if alloc.ndim == 3 and alloc.shape == (B, n, L):
        alloc2 = alloc.reshape(B, B)
    elif alloc.ndim == 2 and alloc.shape == (B, B):
        alloc2 = alloc
    else:
        raise ValueError(
            f"alloc has unexpected shape {alloc.shape}; "
            f"expected (B, B) or (B, n, L) with B={B}, n={n}, L={L}."
        )

    total = alloc2 @ delta_flat
    budgets = np.arange(1, B + 1, dtype=float)
    avg = total / budgets
    toc = avg - baseline

    return toc, avg, total


def evaluate_action_ranking(
    actions: np.ndarray,
    delta: np.ndarray,
    baseline: np.ndarray,
) -> dict[str, Any]:
    """
    Evaluate a ranking-style policy output.

    Parameters
    ----------
    actions : ndarray
        Shape (K, 2), typically K = B = n*L.
        Each row is [patient_index, level_index].
    delta : ndarray
        Shape (n, L).
    baseline : ndarray
        Shape (B,).

    Returns
    -------
    dict
        Contains avg_ate, toc, total_effect, area, and metadata.
    """
    n, L, B = _validate_delta(delta)
    baseline = _validate_baseline(baseline, B)

    actions = np.asarray(actions)

    if actions.ndim != 2 or actions.shape[1] != 2:
        raise ValueError("actions must have shape (K, 2).")

    total = np.zeros(B, dtype=float)
    avg = np.zeros(B, dtype=float)
    allocation_by_level = np.zeros((B, L), dtype=int)

    running_total = 0.0
    K = min(B, actions.shape[0])
    level_counts = np.zeros(L, dtype=int)

    for b in range(K):
        i = int(actions[b, 0])
        ell = int(actions[b, 1])

        if not (0 <= i < n):
            raise ValueError(f"Invalid patient index at row {b}: {i}")
        if not (0 <= ell < L):
            raise ValueError(f"Invalid level index at row {b}: {ell}")

        running_total += float(delta[i, ell])
        total[b] = running_total
        avg[b] = running_total / (b + 1)
        level_counts[ell] += 1
        allocation_by_level[b] = level_counts

    if K > 0 and K < B:
        total[K:] = total[K - 1]
        avg[K:] = avg[K - 1]
        allocation_by_level[K:] = allocation_by_level[K - 1]

    toc = avg - baseline
    area = float(np.sum(toc) / B)

    return {
        "output_type": "ranking",
        "num_steps_used": int(K),
        "avg_ate": avg.tolist(),
        "toc": toc.tolist(),
        "total_effect": total.tolist(),
        "allocation_by_level": allocation_by_level.tolist(),
        "area": area,
    }


def evaluate_pag_star_output(
    alloc: np.ndarray,
    delta: np.ndarray,
    baseline: np.ndarray,
) -> dict[str, Any]:
    """
    Evaluate PAG* output represented as a cumulative allocation-by-budget matrix.
    """
    _, L, _ = _validate_delta(delta)
    toc, avg, total = toc_from_alloc_matrix(alloc, delta, baseline)
    allocation_by_level = alloc.reshape(alloc.shape[0], -1, L).sum(axis=1)
    _, _, B = _validate_delta(delta)
    area = float(np.sum(toc) / B)

    return {
        "output_type": "allocation_matrix",
        "avg_ate": avg.tolist(),
        "toc": toc.tolist(),
        "total_effect": total.tolist(),
        "allocation_by_level": allocation_by_level.tolist(),
        "area": area,
    }


def evaluate_policy_output(
    policy_name: str,
    output: np.ndarray,
    delta: np.ndarray,
    baseline: np.ndarray,
) -> dict[str, Any]:
    """
    Evaluate one policy output using the correct evaluator.
    """
    if policy_name == "pag_star":
        result = evaluate_pag_star_output(output, delta, baseline)
    else:
        result = evaluate_action_ranking(output, delta, baseline)

    result["policy_key"] = policy_name
    result["policy_name"] = POLICY_DISPLAY_NAMES.get(policy_name, policy_name)
    return result


def evaluate_policy_outputs(
    policy_outputs: dict[str, np.ndarray],
    delta: np.ndarray,
    *,
    n_mc_random: int = 200,
    random_seed: int | None = None,
) -> dict[str, Any]:
    """
    Compute the random baseline once, then evaluate all policy outputs.

    Returns
    -------
    dict
        {
            "shape": {"patients": n, "levels": L, "budget": B},
            "baseline": [...],
            "policies": {
                "lfp": {...},
                "pag": {...},
                "pag_star": {...},
                "ifp": {...},
                "pgp": {...}
            },
            "summary": {
                "lfp": area,
                ...
            }
        }
    """
    n, L, B = _validate_delta(delta)

    baseline = compute_random_baseline(
        delta,
        n_mc=n_mc_random,
        seed=random_seed,
    )

    policies: dict[str, Any] = {}
    summary: dict[str, float] = {}

    for policy_name, output in policy_outputs.items():
        result = evaluate_policy_output(policy_name, output, delta, baseline)
        policies[policy_name] = result
        summary[policy_name] = float(result["area"])

    return {
        "shape": {
            "patients": int(n),
            "levels": int(L),
            "budget": int(B),
        },
        "baseline": baseline.tolist(),
        "policies": policies,
        "summary": summary,
    }


def rank_policies_by_area(evaluation_result: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Return policies sorted from highest ML-AUTOC area to lowest.
    """
    summary = evaluation_result.get("summary", {})

    ranked = sorted(
        (
            {
                "policy_key": key,
                "policy_name": POLICY_DISPLAY_NAMES.get(key, key),
                "area": float(area),
            }
            for key, area in summary.items()
        ),
        key=lambda x: x["area"],
        reverse=True,
    )

    return ranked
