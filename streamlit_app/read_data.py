import json
import os
import time
from collections import defaultdict
from functools import lru_cache

import pandas as pd

from config import *


def read_json(path):
    if os.path.isfile(path):
        with open(path, "r") as f:
            return json.load(f)
    return {}


def get_result_from_disk(bench, model, repo, fn, gen_i=None):
    c = f"{fn}-{gen_i}" if gen_i is not None else fn
    return read_fn_results(c, f"{RESULTS_PATH}/{bench}/{model}/{repo}/")


def read_fn_results(fn, path):
    try:
        f = read_json(f"{path}{fn}.json")
    except Exception as e:
        print(fn, path)
        raise e

    if f:
        f.update(read_json(f"{path}{fn}-res.json") or {})
        return f
    return {}


def read_repo_results(path, model):
    n_format = 1 if model == "original" else 2
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


def read_results(bench=None, model=None):
    """ {bench}/{model}/{repo}/{fn_id}-{i} """
    versions = [
        v for v in os.listdir(RESULTS_PATH)
        if v.startswith("bench-v") and os.path.isdir(f"{RESULTS_PATH}/{v}")
    ]
    results = {
        v: {
            m: {
                repo: read_repo_results(f"{RESULTS_PATH}/{v}/{m}/{repo}/", m)
                for repo in os.listdir(f"{RESULTS_PATH}/{v}/{m}")
                if os.path.isdir(f"{RESULTS_PATH}/{v}/{m}/{repo}")
            }
            for m in os.listdir(f"{RESULTS_PATH}/{v}")
            if (model is None and os.path.isdir(f"{RESULTS_PATH}/{v}/{m}")) or m == model
        }
        for v in versions
        if (bench is None and os.path.isdir(f"{RESULTS_PATH}/{v}")) or v == bench
    }
    return results


def read_bench_df():
    versions = [
        v for v in os.listdir(BENCH_PATH)
        if v.startswith("bench-v") and os.path.isdir(f"{BENCH_PATH}/{v}")
    ]
    bench = {
        v: pd.read_csv(f"{v}/{v}.csv")
        for v in versions
    }
    bench_js = {
        v: read_json(f"{BENCH_JS_PATH}/{v}.json")
        for v in versions
    }
    df = {
        v: {
            model: pd.read_csv(f"{BENCH_PATH}/{v}/{m}")
            for m in os.listdir(f"{BENCH_PATH}/{v}")
            if (model := m.rsplit(".", 1)[0]) and v not in m
        } for v in versions
    }
    return bench, bench_js, df


def get_result_time_from_disk(bench, model, repo, fn, gen_i=None):
    config = f"{fn}-{gen_i}" if gen_i is not None else fn
    path = f"{RESULTS_PATH}/{bench}/{model}/{repo}/{config}"

    if os.path.isfile(f"{path}-res.json"):
        start = os.path.getmtime(f"{path}.json")
        finish = os.path.getmtime(f"{path}-res.json")
        return start, finish
    return None


def read_repo_results_time(path):
    all_files = os.listdir(path)
    configs = sorted([
        f.rsplit(".", 1)[0]
        for f in all_files
        if "-res" not in f
    ])
    result = defaultdict(dict)
    for c in configs:
        f = c.split("-")[0]
        if f"{c}-res.json" in all_files:
            start = os.path.getmtime(f"{path}{c}.json")
            finish = os.path.getmtime(f"{path}{c}-res.json")
            result[f][c] = (start, finish)

    return result


def read_results_time(bench=None, model=None):
    versions = [
        v for v in os.listdir(RESULTS_PATH)
        if v.startswith("bench-v") and os.path.isdir(f"{RESULTS_PATH}/{v}")
    ]
    results = {
        v: {
            m: {
                repo: read_repo_results_time(f"{RESULTS_PATH}/{v}/{m}/{repo}/")
                for repo in os.listdir(f"{RESULTS_PATH}/{v}/{m}")
                if os.path.isdir(f"{RESULTS_PATH}/{v}/{m}/{repo}/")
            }
            for m in os.listdir(f"{RESULTS_PATH}/{v}")
            if model is None or m == model
        }
        for v in versions
        if bench is None or v == bench
    }
    return results


@lru_cache(maxsize=1)
def _read_cached_results(ttl_hash=None):
    del ttl_hash  # to emphasize we don't use it and to shut pylint up
    return read_results(), read_results_time()


def get_ttl_hash(seconds=CACHE_TIMEOUT):
    """Return the same value withing `seconds` time period"""
    return round(time.time() / seconds)


def read_cached_results(ttl_hash=None):
    return _read_cached_results(ttl_hash=ttl_hash or get_ttl_hash())


def read_cached_model_results(bench, model, total, gen_k):
    path = f"{RESULTS_PATH}/{bench}/{model}/metadata.json"
    if os.path.isfile(path):
        with open(path, "r") as f:
            results = json.load(f)
        return results["model_results"], results["results_time"]

    model_results, results_time = read_results(bench, model), read_results_time(bench, model)
    model_results = model_results.get(bench, {}).get(model, {})
    results_time = results_time.get(bench, {}).get(model, {})

    processed_fns = sum(
        len([
            c for gens in model_results.get(r, {}).values()
            for c, res in gens.items()
            if "built" in res
        ]) for r in REPOS
    )
    total_fns = sum(total.values())
    progress = processed_fns / total_fns / gen_k

    if progress >= 1:
        for fns in model_results.values():
            for cs in fns.values():
                for c in cs.values():
                    error_lines = c["error"].split("\n")
                    if len(error_lines) > 10:
                        c["error"] = "\n".join(error_lines[:5] + ["..."] + error_lines[-5:])
        results = {
            "model_results": model_results,
            "results_time": results_time,
        }
        with open(path, "w") as f:
            json.dump(results, f)

    return model_results, results_time


def read_cached_only_results(df):
    results, results_time = defaultdict(dict), defaultdict(dict)
    for b, models in df.items():
        for m in models:
            path = f"{RESULTS_PATH}/{b}/{m}/metadata.json"
            if os.path.isfile(path):
                with open(path, "r") as f:
                    results = json.load(f)
                results[b][m] = results["model_results"]
                results_time[b][m] = results["results_time"]

    return results, results_time
