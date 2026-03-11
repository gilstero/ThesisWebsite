"""
solvers.py

Core policy solvers for the ML-AUTOC thesis website backend.

This file is intentionally solver-only:
- no dataset-directory loops
- no CSV saving
- no plotting

All functions take a marginal benefit matrix delta of shape (n, L).

Conventions
-----------
For ranking-based policies, the returned array has shape (B, 2),
where B = n * L and each row is [unit_index, level_index].

For PAG*, the returned array has shape (B, n * L), where row b-1
is the flattened allocation vector after budget b has been used.
"""

from __future__ import annotations

from typing import Callable, Dict

import numpy as np


PolicyOutput = np.ndarray


def _validate_delta(delta: np.ndarray) -> tuple[int, int, int]:
    """
    Validate delta and return (n, L, B).
    """
    if not isinstance(delta, np.ndarray):
        raise TypeError("delta must be a numpy ndarray.")

    if delta.ndim != 2:
        raise ValueError("delta must be a 2D array of shape (n, L).")

    n, L = delta.shape

    if n <= 0:
        raise ValueError("delta must have at least one patient.")
    if L <= 0:
        raise ValueError("delta must have at least one treatment level.")

    B = n * L
    return n, L, B


def solve_pag(delta: np.ndarray) -> np.ndarray:
    """
    PAG (no flips).

    At each budget step, choose the best currently feasible frontier action.
    Precedence is respected by only allowing the next untreated level
    for each individual.
    """
    n, L, B = _validate_delta(delta)

    ranking = np.zeros((B, 2), dtype=int)
    next_level = np.zeros(n, dtype=int)

    for b in range(B):
        best_i = -1
        best_val = -np.inf

        for i in range(n):
            l = next_level[i]
            if l < L and delta[i, l] > best_val:
                best_val = delta[i, l]
                best_i = i

        l = next_level[best_i]
        ranking[b] = (best_i, l)
        next_level[best_i] += 1

    return ranking


def solve_pag_star(delta: np.ndarray) -> np.ndarray:
    """
    PAG* (allows flips).

    Dynamic program over individuals and budget.
    Returns allocations-by-budget as a binary matrix of shape (B, n*L),
    where each row gives the cumulative allocation after that budget step.
    """
    n, L, B = _validate_delta(delta)

    prefix = np.zeros((n, L + 1), dtype=np.float64)
    prefix[:, 1:] = np.cumsum(delta, axis=1)

    dp_prev = np.full(B + 1, -np.inf, dtype=np.float64)
    dp_prev[0] = 0.0

    choice = np.zeros((n, B + 1), dtype=np.uint8)

    for i in range(n):
        best = dp_prev.copy()
        best_m = np.zeros(B + 1, dtype=np.uint8)

        for m in range(1, L + 1):
            cand = np.full(B + 1, -np.inf, dtype=np.float64)
            cand[m:] = dp_prev[:-m] + prefix[i, m]

            better = cand > best
            best = np.where(better, cand, best)
            best_m = np.where(better, m, best_m)

        choice[i, :] = best_m
        dp_prev = best

    allocs_by_budget = np.zeros((B, n * L), dtype=np.uint8)

    for b in range(1, B + 1):
        bb = b
        alloc_flat = np.zeros(n * L, dtype=np.uint8)

        for i in range(n - 1, -1, -1):
            m = int(choice[i, bb])
            bb -= m
            if m > 0:
                start = i * L
                alloc_flat[start:start + m] = 1

        allocs_by_budget[b - 1, :] = alloc_flat

    return allocs_by_budget


def solve_lfp(delta: np.ndarray) -> np.ndarray:
    """
    LFP: Level-First Policy.

    For each level, rank individuals by that level's marginal benefit,
    then exhaust that level before moving to the next level.
    """
    n, L, B = _validate_delta(delta)

    ranking = np.zeros((B, 2), dtype=int)
    k = 0

    for l in range(L):
        ind_order = np.argsort(-delta[:, l])
        for i in ind_order:
            ranking[k, 0] = i
            ranking[k, 1] = l
            k += 1

    return ranking


def solve_ifp(delta: np.ndarray) -> np.ndarray:
    """
    IFP: Individual-First Policy.

    Compute a total score for each individual by summing marginals across levels,
    rank individuals by total score descending, then assign all levels of the
    highest-ranked individual before moving to the next individual.
    """
    n, L, B = _validate_delta(delta)

    scores = delta.sum(axis=1)
    ind_order = np.argsort(-scores)

    ranking = np.zeros((B, 2), dtype=int)
    k = 0

    for i in ind_order:
        for l in range(L):
            ranking[k, 0] = i
            ranking[k, 1] = l
            k += 1

    return ranking


def solve_pgp(delta: np.ndarray) -> np.ndarray:
    """
    PGP: Pooled Global Policy.

    Rank all unit-level pairs globally by marginal benefit, ignoring precedence.
    """
    n, L, B = _validate_delta(delta)

    flat = delta.reshape(-1)
    order = np.argsort(-flat)

    ranking = np.zeros((B, 2), dtype=int)
    ranking[:, 0] = order // L
    ranking[:, 1] = order % L

    return ranking


def compute_random_baseline(
    delta: np.ndarray,
    n_mc: int = 200,
    seed: int | None = None,
) -> np.ndarray:
    """
    Monte Carlo random baseline under precedence.

    Returns
    -------
    baseline_avg : ndarray of shape (B,)
        baseline_avg[b-1] is the expected cumulative average treatment effect
        after budget b.
    """
    n, L, B = _validate_delta(delta)

    rng = np.random.default_rng(seed)
    baseline_sum = np.zeros(B, dtype=float)

    for _ in range(n_mc):
        next_level = np.zeros(n, dtype=np.int16)
        cum = 0.0

        for b in range(1, B + 1):
            feasible = np.flatnonzero(next_level < L)
            i = int(rng.choice(feasible))
            l = int(next_level[i])

            cum += float(delta[i, l])
            next_level[i] += 1

            baseline_sum[b - 1] += cum / b

    return baseline_sum / n_mc


POLICY_SOLVERS: Dict[str, Callable[[np.ndarray], np.ndarray]] = {
    "lfp": solve_lfp,
    "pag": solve_pag,
    "pag_star": solve_pag_star,
    "ifp": solve_ifp,
    "pgp": solve_pgp,
}


POLICY_DISPLAY_NAMES: Dict[str, str] = {
    "lfp": "LFP",
    "pag": "PAG",
    "pag_star": "PAG*",
    "ifp": "IFP",
    "pgp": "PGP",
}


def run_all_policies(delta: np.ndarray) -> dict[str, np.ndarray]:
    """
    Run all thesis policies on a single delta matrix.

    Returns
    -------
    dict[str, np.ndarray]
        {
            "lfp": ...,
            "pag": ...,
            "pag_star": ...,
            "ifp": ...,
            "pgp": ...,
        }
    """
    return {
        "lfp": solve_lfp(delta),
        "pag": solve_pag(delta),
        "pag_star": solve_pag_star(delta),
        "ifp": solve_ifp(delta),
        "pgp": solve_pgp(delta),
    }