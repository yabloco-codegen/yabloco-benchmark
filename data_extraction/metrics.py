import itertools
import json

import numpy as np
import pandas as pd
from fuzzywuzzy import fuzz


def get_ground_truths(version="bench-v0.5"):
    df = pd.read_csv(f"{version}.csv")
    with open(f"{version}.json", "r") as f:
        js = json.load(f)

    result = []
    for _, row in df.iterrows():
        i = row["Unnamed: 0"]
        result.append((i, js[i]["code"]))
    return result


def exact_match_score(predictions, ground_truths):
    exact_match = 0
    for pred, gt in zip(predictions, ground_truths):
        if pred.split() == gt.split():
            exact_match += 1

    return round(exact_match / len(predictions), 5)


def edit_similarity_score(predictions, ground_truths):
    edit_sim = 0.0
    for pred, gt in zip(predictions, ground_truths):
        edit_sim += fuzz.ratio(pred, gt)

    return round(edit_sim / len(predictions), 5)


def accuracy_at_k(predictions_list, ground_truths):
    exact_match_k = 0
    for preds, gt in zip(predictions_list, ground_truths):
        if any(pred.split() == gt.split() for pred in preds):
            exact_match_k += 1

    return round(exact_match_k / len(predictions_list), 5)


def estimate_pass_at_k(results, k) -> np.ndarray:
    """
    Estimates pass@k of each problem and returns them in an array.
    results: [0, 1, 10 ...] with len(bench) elements where each is num samples passed
    """

    def estimator(n: int, c: int, k: int) -> float:
        """
        Calculates 1 - comb(n - c, k) / comb(n, k).
        """
        if n - c < k:
            return 1.0
        return 1.0 - np.prod(1.0 - k / np.arange(n - c + 1, n + 1))

    num_samples_it = itertools.repeat(k, len(results))
    return np.mean([estimator(int(n), int(c), k) for n, c in zip(num_samples_it, results)])


def main():
    pred = pd.read_csv("with_code_0-5-gpt4.csv")

    pred_list = []
    gt = []
    print(len(pred))
    for _, row in pred.iterrows():
        gt.append(row["original"])
        pred_list.append([row[f"{i}"] for i in range(10)])

    print(accuracy_at_k(pred_list, gt))
    pred = [p[0] for p in pred_list]
    print(exact_match_score(pred, gt))
    print(edit_similarity_score(pred, gt))
    scores = sorted([fuzz.ratio(p, g) for p, g in zip(pred, gt)], reverse=True)
    print(scores[:10])


def main2():
    with open("redis_res.json") as f:
        r = json.load(f)

    b, p = r
    n = len(b)
    b = sum(0 in v for v in b.values()) / n
    p = sum(0 in v.values() for v in p.values()) / n
    print(f"{b:.4f}, {p:.4f}")


if __name__ == "__main__":
    main()
