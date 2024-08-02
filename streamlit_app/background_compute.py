import json
import os.path
import subprocess
import time
from datetime import datetime
from random import randint

from read_data import read_bench_df, read_results, read_cached_results, get_result_from_disk
from results.run_single_example import run_single_example
from utils import get_ind, parse_generation

from config import *


def rerun(fns, bench, model, repo):
    path = f"{RESULTS_PATH}/{bench}/{model}"
    if repo != "overall":
        path += f"/{repo}"
    for fn in fns:
        p = f"{path}/{fn}-res.json"
        if os.path.isfile(p):
            os.remove(p)
        p = f"{path}/metadata.json"
        if os.path.isfile(p):
            os.remove(p)
    read_cached_results(randint(0, 10000))


def get_result(results, bench, model, repo, fn, gen_i=None):
    c = f"{fn}-{gen_i}" if gen_i is not None else fn
    r = results.get(bench, {}).get(model, {}).get(repo, {}).get(fn, {}).get(c, {})
    return r


def save_identical(config, result, ind):
    path = f"{RESULTS_PATH}/{ind}.json"
    folder = path.rsplit("/", 1)[0]
    if not os.path.isdir(folder):
        os.makedirs(folder)

    with open(path, "w") as f:
        json.dump(config, f)

    with open(path.replace(".json", "-res.json"), "w") as f:
        json.dump(result, f)


def already_tested(results, bench, model, row, fn, code, gen_i, ind):
    if "built" in get_result_from_disk(bench, model, row["repository"], fn, gen_i):
        return True

    return False


def populate_from_model(q, results, row, bench, model, fn, code, gen_i=None):
    ind = get_ind(bench, model, row["repository"], fn, gen_i)
    if not already_tested(results, bench, model, row, fn, code, gen_i, ind):
        q.append((ind, fn, row, bench, model, code, gen_i))


def populate_queue(containers):
    bench, bench_js, df = read_bench_df()
    results = read_results()

    versions = sorted(bench.keys(), reverse=True)
    functions = {
        v: sorted([
            (x['repository'], x['Unnamed: 0'])
            for _, x in bench[v].iterrows()
        ])
        for v in versions
    }
    models = {v: sorted(df[v].keys()) for v in versions}

    q = []
    for v in versions:
        # original
        for _, fn in functions[v]:
            _, row = next(bench[v][bench[v]["Unnamed: 0"] == fn].iterrows())
            orig_code = bench_js[v][fn]["code"]
            populate_from_model(q, results, row, v, "original", fn, orig_code)

        # generations
        for m in models[v]:
            for _, fn in functions[v]:
                rows = df[v][m][df[v][m]["Unnamed: 0"] == fn]
                if len(rows) == 0:
                    continue

                _, row = next(bench[v][bench[v]["Unnamed: 0"] == fn].iterrows())
                _, row_gen = next(rows.iterrows())
                for gen_i in range(10):
                    generated_code = row_gen[f"{gen_i}"]
                    generated_code = parse_generation(generated_code, fn)
                    populate_from_model(q, results, row, v, m, fn, generated_code, gen_i)

    q = list(reversed(q))

    running = {c["Names"].replace("_", "/") for c in containers}
    q = [x for x in q if x[0] not in running]
    return q, results


def merge_queues(q, new_q):
    old = {x[0] for x in q}
    new = [x for x in new_q if x[0] not in old]
    return q + new


def run_last_from_q(results, q, to_run=1):
    while to_run > 0 and q:
        (ind, fn, row, v, m, code, gen_i) = q[-1]
        q = q[:-1]
        if not already_tested(results, v, m, row, fn, code, gen_i, ind):
            run_single_example(row, code, row["repository"], ind, bg=True)
            print(f"{datetime.now()}: {ind}")
            to_run -= 1
    return q


def docker_ps():
    child = subprocess.run(f"docker ps --format json --no-trunc", shell=True, text=True,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    result = child.stdout.split("\n")
    result = [json.loads(line) for line in result if "bench-v" in line]
    return result


def mark_timeout(ind):
    with open(f"{RESULTS_PATH}/{ind}.json", "r") as f:
        config = json.load(f)
    config.update({
        "built": False,
        "passed": False,
        "error": "Timeout",
    })
    with open(f"{RESULTS_PATH}/{ind}-res.json", "w", encoding="utf-8") as f:
        json.dump(config, f)


def kill_timeouts(timeout, containers):
    def to_datetime(created):
        return datetime.strptime(created.split("+")[0].strip(), "%Y-%m-%d %X")

    containers = [
        c for c in containers
        if datetime.now() - to_datetime(c["CreatedAt"]) > timeout[c["Names"].split("_")[2]]
    ]

    containers_str = " ".join(c['Names'] for c in containers)
    subprocess.run(f"docker rm -f {containers_str}", shell=True, text=True,
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    for c in containers:
        mark_timeout(c["Names"].replace("_", "/"))


def print_q(q):
    versions = {v for (_, _, _, v, m, _, _) in q}
    models = {
        v: {m for (_, _, _, v_, m, _, _) in q if v_ == v}
        for v in versions
    }
    result = {
        v: {
            m: {
                r: 0 for r in REPOS
            } for m in models[v]
        } for v in versions
    }

    for (_, _, row, v, m, _, _) in q:
        result[v][m][row["repository"]] += 1
    for v in sorted(versions, reverse=True):
        print(v)
        for m in result[v]:
            print(f"{m}: {', '.join([f'{r}: {n}' for r, n in result[v][m].items() if n])}")
        print()


def main():
    containers = docker_ps()
    q, results = populate_queue(containers)
    print(len(q))
    print_q(q)

    q_last = time.time()
    d_last = time.time()
    containers = docker_ps()

    while True:
        if time.time() - q_last > UPDATE_PERIOD or (containers != -1 and len(containers) == 0 and time.time() - q_last > UPDATE_PERIOD / 5):
            containers = docker_ps()
            kill_timeouts(TIMEOUT, containers)
            new_q, results = populate_queue(containers)
            old = len(q)
            q = merge_queues(q, new_q)
            q_last = time.time()
            print(old, "->", len(q))
            print_q(q)

        if time.time() - d_last > DOCKER_CHECK_PERIOD:
            containers = docker_ps()
            d_last = time.time()

        if containers != -1 and len(containers) <= NUM_INSTANCES:
            to_run = NUM_INSTANCES - len(containers)
            if any("redis" in c['Names'] for c in containers) or (q and "redis" in q[-1][0]):
                to_run = NUM_INSTANCES_REDIS - len(containers)
            if to_run > 0:
                q = run_last_from_q(results, q, to_run=to_run)
            containers = -1
        else:
            time.sleep(1)


if __name__ == "__main__":
    main()
