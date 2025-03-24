import re

import numpy as np


def exact_match(prediction, ground_truth):
    return float(
        prediction and re.sub(r'\W+', "", prediction) == re.sub(r'\W+', "", ground_truth)
    )


def estimate_pass_at_k(n: int, c: int, k: int) -> float:
    """
    Calculates 1 - comb(n - c, k) / comb(n, k).
    """
    if c == 0 and n < k:
        return 0.0
    if n - c < k:
        return 1.0
    return 1.0 - np.prod(1.0 - k / np.arange(n - c + 1, n + 1))
