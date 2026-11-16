"""Statistics used in the paper, standard library only."""
from math import comb, sqrt


def binom_pmf(k, n, p=0.5):
    return comb(n, k) * p**k * (1 - p) ** (n - k)


def binom_two_sided(k, n, p=0.5):
    """Exact two-sided binomial test: total probability of the outcomes no more likely than k."""
    pk = binom_pmf(k, n, p)
    return min(1.0, sum(binom_pmf(i, n, p) for i in range(n + 1) if binom_pmf(i, n, p) <= pk * (1 + 1e-9)))


def chance_region(n, alpha=0.05):
    """Counts of correct decisions (of n) that the exact binomial test does not separate from chance (0.5)."""
    keep = [k for k in range(n + 1) if binom_two_sided(k, n) >= alpha]
    return keep[0], keep[-1]


def power(n, accuracy, alpha=0.05):
    """Probability that the test rejects chance when the true accuracy is `accuracy`."""
    lo, hi = chance_region(n, alpha)
    return sum(binom_pmf(k, n, accuracy) for k in range(n + 1) if k < lo or k > hi)


def wilson(k, n, z=1.959964):
    p = k / n
    centre, half = p + z * z / (2 * n), z * sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (centre - half) / (1 + z * z / n), (centre + half) / (1 + z * z / n)


def mcnemar_exact(b, c):
    """Exact McNemar test from the two discordant counts (two-sided)."""
    n = b + c
    return 1.0 if n == 0 else min(1.0, 2 * sum(binom_pmf(i, n) for i in range(min(b, c) + 1)))


def kappa(items, a, b, both):
    """Cohen's kappa for two binary raters: `a` and `b` items flagged by each, `both` flagged by both."""
    po = (both + (items - a - b + both)) / items
    pe = (a * b + (items - a) * (items - b)) / items**2
    return 0.0 if pe == 1 else (po - pe) / (1 - pe)
