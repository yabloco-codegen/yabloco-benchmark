import itertools
import json
import re
from typing import List, Union

import pandas as pd
import numpy as np
from fuzzywuzzy import fuzz


def get_ground_truths(version="bench-v0.4"):
    df = pd.read_csv(f"{version}.csv")
    with open(f"{version}.json", "r") as f:
        js = json.load(f)

    result = []
    for _, row in df.iterrows():
        i = row["Unnamed: 0"]
        result.append((i, js[i]["code"]))
    return result


def exact_match_score(predictions, ground_truths):
    if not predictions:
        return 0

    exact_match = 0
    for pred, gt in zip(predictions, ground_truths):
        if re.sub(r"[\s\t\n\r]+", "", pred) == re.sub(r"[\s\t\n\r]+", "", gt):
            exact_match += 1

    return 100 * round(exact_match / len(predictions), 3)


def edit_similarity_score(predictions, ground_truths):
    if not predictions:
        return 0

    edit_sim = 0.0
    for pred, gt in zip(predictions, ground_truths):
        edit_sim += fuzz.ratio(pred, gt)

    return round(edit_sim / len(predictions), 2)


def accuracy_at_k(predictions_list, ground_truths):
    exact_match_k = 0
    for preds, gt in zip(predictions_list, ground_truths):
        if any(pred.split() == gt.split() for pred in preds):
            exact_match_k += 1

    return round(exact_match_k / len(predictions_list), 2)


def estimate_pass_at_k(
    num_samples: Union[int, List[int], np.ndarray],
    num_correct: Union[List[int], np.ndarray],
    k: int
) -> np.ndarray:
    """
    Estimates pass@k of each problem and returns them in an array.
    """
    def estimator(n: int, c: int, k: int) -> float:
        """
        Calculates 1 - comb(n - c, k) / comb(n, k).
        """
        if c == 0 and n < k:
            return 0.0
        if n - c < k:
            return 1.0
        return 1.0 - np.prod(1.0 - k / np.arange(n - c + 1, n + 1))

    if isinstance(num_samples, int):
        num_samples_it = itertools.repeat(num_samples, len(num_correct))
    else:
        assert len(num_samples) == len(num_correct)
        num_samples_it = iter(num_samples)

    return np.array([estimator(int(n), int(c), k) for n, c in zip(num_samples_it, num_correct)])


def pass_at_k(results, k=10):
    """ [ [0/1 for k] for n ]"""
    if not results:
        return 0

    total, correct = [], []
    for passed in results:
        total.append(len(passed[:k]))
        correct.append(sum(passed[:k]))
    total = np.array(total)
    correct = np.array(correct)
    return round(100 * estimate_pass_at_k(total, correct, k).mean(), 2)


def main():
    pred = pd.read_csv("generated_code-v0.4.csv")
    pred_list = []
    gt = []
    for _, row in pred.iterrows():
        gt.append(row["original"])
        pred_list.append([row[f"{i}"] for i in range(10)])
    print(accuracy_at_k(pred_list, gt))
    pred = [p[0] for p in pred_list]
    print(exact_match_score(pred, gt))
    print(edit_similarity_score(pred, gt))
    scores = sorted([fuzz.ratio(p, g) for p, g in zip(pred, gt)], reverse=True)
    print(scores[:10])
