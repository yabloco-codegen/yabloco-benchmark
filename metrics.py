import re

import numpy as np
# from fuzzywuzzy import fuzz


def exact_match(prediction, ground_truth):
    if not prediction:
        return 0
    return re.sub(r'\W+', "", prediction) == re.sub(r'\W+', "", ground_truth)


def estimate_pass_at_k(n: int, c: int, k: int) -> float:
    """
    Calculates 1 - comb(n - c, k) / comb(n, k).
    """
    if c == 0 and n < k:
        return 0.0
    if n - c < k:
        return 1.0
    return 1.0 - np.prod(1.0 - k / np.arange(n - c + 1, n + 1))


# def edit_similarity(predictions, ground_truths):
#     if not predictions:
#         return 0
#
#     edit_sim = 0.0
#     for pred, gt in zip(predictions, ground_truths):
#         edit_sim += fuzz.ratio(pred, gt)
#
#     return round(edit_sim / len(predictions), 2)

