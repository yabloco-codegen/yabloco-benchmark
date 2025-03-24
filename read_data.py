import json
import os
from collections import defaultdict

import pandas as pd


def read_json(path):
    if os.path.isfile(path):
        with open(path, "r", encoding='utf-8') as f:
            return json.load(f)
    return {}


def read_fn_results(fn, path):
    try:
        f = read_json(f"{path}/{fn}.json")
    except Exception as e:
        print(fn, path)
        raise e

    if f:
        f.update(read_json(f"{path}/{fn}-res.json") or {})
        return f
    return {}


def get_result_from_disk(results_path, repo, fn, gen_i=None):
    c = f"{fn}-{gen_i}" if gen_i is not None else fn
    return read_fn_results(c, f"{results_path}/{repo}/")


def read_repo_results(path):
    n_format = 2
    configs = sorted([
        f.rsplit(".", 1)[0]
        for f in os.listdir(path)
        if "-res" not in f and len(f.split("-")) == n_format
    ])
    result = defaultdict(dict)
    for c in configs:
        f = c.split("-")[0]
        r = read_fn_results(c, path)
        if r:
            result[f][c] = r

    return result


def read_results(results_path):
    results = {
        repo: read_repo_results(f"{results_path}/{repo}")
        for repo in os.listdir(f"{results_path}")
        if os.path.isdir(f"{results_path}/{repo}")
    }
    return results


def read_bench_df(bench_path_v):
    bench = pd.read_csv(f"{bench_path_v}.csv")
    bench_js = read_json(f"{bench_path_v}.json")
    bench["id"] = bench["Unnamed: 0"]
    bench.set_index("Unnamed: 0", inplace=True)
    return bench, bench_js
