"""
Dataset generation file for strictly decreasing marginal benefits.
There is no need to execute this file directly; it is imported by createdatasets.py.
-----------------------------------------------

-----------------------------------------------
"""

import numpy as np


def generatestrictlydecreasing(
    n: int,
    L: int,
    sigma: float,
    seed: int,
    gap: float = 1.0,
    mu: float = 0.0,
    d: int = 10,
):
    """
    X : (n, d) ndarray
        Covariates
    delta : (n, L) ndarray
        Marginal benefits
    """

    if seed is not None:
        np.random.seed(seed)

    # Covariates
    X = np.random.normal(0, 1, size=(n, d))

    # Raw draws
    Z = np.random.normal(mu, sigma, size=(n, L))

    delta = np.zeros((n, L))

    # Level 1 (ensure positive start)
    delta[:, 0] = np.maximum(0.0, Z[:, 0]) + gap * (L - 1)

    # Enforce strict decrease
    for l in range(1, L):
        delta[:, l] = np.minimum(Z[:, l], delta[:, l - 1] - gap)

    costs = np.ones(L)

    return X, delta, costs