import json
import os
import shutil
import subprocess
import time
from datetime import datetime, timedelta
from glob import glob

from read_data import read_bench_df, read_results, get_result_from_disk
from metrics import exact_match, estimate_pass_at_k#, edit_similarity
from results.run_single_example import run_single_example


REPOS = ["bullet3", "llvm", "openssl", "redis"]

# compute consts
PREFIX = "yabloco_"
NUM_INSTANCES = 8  # docker containers to run simultaneously, containers allow multiprocessing inside already
NUM_INSTANCES_REDIS = 4  # redis fails if more than 4 containers run simultaneously due to some tests being response time sensitive
DOCKER_CHECK_PERIOD = 5
TIMEOUT_CHECK_PERIOD = 300

TIMEOUT = {
    "bullet3": timedelta(minutes=10),
    "llvm": timedelta(minutes=30),
    "openssl": timedelta(minutes=10),
    "redis": timedelta(minutes=30),
}


def get_identifier(repo, fn, gen_i=None):
    identifier = f"{repo}/{fn}"
    if gen_i is not None:
        identifier += f"-{gen_i}"
    return identifier


def parse_generation(text):
    print(text)
    if not isinstance(text, str):
        return ""

    # most probably code is tagged with ```
    sections = text.split('```')
    generated_code = "-"
    if len(sections) >= 3:
        generated_code = sections[1]
    if len(sections) == 1:
        generated_code = sections[0]

    remove_prefix = ["cpp", "c++", "c", "++"]
    for pref in remove_prefix:
        generated_code = generated_code.removeprefix(pref)
    generated_lines = generated_code.split('\n')

    # remove redundant code around the target function
    generated_lines = [
        line
        for line in generated_lines
        if not line.startswith("#include")
    ]
    ind_of_main = [
        ind
        for ind, s in enumerate(generated_lines)
        if s.startswith("void main(") or s.startswith("int main(")
    ]

    if len(ind_of_main) != 0:
        generated_lines = generated_lines[:ind_of_main[0]]

    return "\n".join(generated_lines) + "\n"


def docker_build(docker_path):
    child = subprocess.run(f"docker images --format json --no-trunc",
                           shell=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    result = child.stdout.split("\n")
    result = [json.loads(line)["Repository"] for line in result if PREFIX in line]
    if len(set(result) & {f"{PREFIX}{repo}" for repo in REPOS}) == len(REPOS):
        return

    for i, repo in enumerate(REPOS):
        print(f"Building docker {PREFIX}{repo} ({i + 1}/{len(REPOS)})...")
        subprocess.run(f"docker build -f {docker_path}/{repo}.Dockerfile -t {PREFIX}{repo} .",
                       shell=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def docker_ps():
    child = subprocess.run(f"docker ps --format json --no-trunc",
                           shell=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    result = child.stdout.split("\n")
    result = [json.loads(line) for line in result if PREFIX in line]
    return result


def mark_timeout(identifier, results_path):
    with open(f"{results_path}/{identifier}.json", "r") as f:
        config = json.load(f)

    config.update({
        "built": False,
        "passed": False,
        "error": "Timeout",
    })
    with open(f"{results_path}/{identifier}-res.json", "w", encoding="utf-8") as f:
        json.dump(config, f)


def kill_timeouts(results_path, timeout, containers):
    def to_datetime(created):
        return datetime.strptime(created.split("+")[0].strip(), "%Y-%m-%d %X")

    containers = [
        c for c in containers
        if PREFIX in c["Names"] and datetime.now() - to_datetime(c["CreatedAt"]) > timeout[c["Names"].split("_")[1]]
    ]

    containers_str = " ".join(c['Names'] for c in containers)
    subprocess.run(f"docker rm -f {containers_str}", shell=True, text=True,
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    for c in containers:
        mark_timeout(c["Names"].replace(PREFIX, "").replace("_", "/"), results_path)


def run_last_from_q(q, results_path, to_run=1):
    while to_run > 0 and q:
        (identifier, fn, row, code, gen_i) = q[-1]
        q = q[:-1]
        if not already_tested(results_path, row, fn, gen_i):
            run_single_example(row, code, row["repository"], results_path, identifier, PREFIX)
            print(f"{datetime.now()}: {identifier}")
            to_run -= 1
    return q


def already_tested(results_path, row, fn, gen_i):
    return "built" in get_result_from_disk(results_path, row["repository"], fn, gen_i)


def populate_from_model(q, row, results_path, fn, code, gen_i=None):
    identifier = get_identifier(row["repository"], fn, gen_i)
    if not already_tested(results_path, row, fn, gen_i):
        q.append((identifier, fn, row, code, gen_i))


def populate_queue(results_path, bench, generations, containers):
    functions = sorted([
        (x['repository'], x["id"])
        for _, x in bench.iterrows()
    ], reverse=True)

    q = []
    for _, fn in functions:
        gens = generations.get(fn)
        if gens is None or not gens:
            continue
        elif not isinstance(gens, list):
            gens = [gens]

        row = bench.loc[fn]
        for gen_i, generated_code in enumerate(gens):
            generated_code = parse_generation(generated_code)
            populate_from_model(q, row, results_path, fn, generated_code, gen_i)

    running = {c["Names"].replace(PREFIX, "").replace("_", "/") for c in containers}
    q = [x for x in q if x[0] not in running]
    return q


def rm_results_for_fns(fns, results_path):
    fn_paths = [p for fn in fns for p in glob(f"{results_path}/*/{fn}*-res.json")]
    for p in fn_paths:
        os.remove(p)


def run_tests_with_queue(results_path, generations, bench):
    containers = docker_ps()
    q = populate_queue(results_path, bench, generations, containers)

    d_last = time.time()
    t_last = time.time()
    containers = docker_ps()
    last_len = -1

    while q or containers:
        if len(q) != last_len:
            last_len = len(q)
            print("Instances in queue:", last_len)

        if time.time() - t_last > TIMEOUT_CHECK_PERIOD:
            containers = docker_ps()
            kill_timeouts(results_path, TIMEOUT, containers)
            t_last = time.time()

        if time.time() - d_last > DOCKER_CHECK_PERIOD:
            containers = docker_ps()
            d_last = time.time()
            if not q and not containers:
                break

        if containers != -1 and len(containers) <= NUM_INSTANCES:
            to_run = NUM_INSTANCES - len(containers)
            if any("redis" in c['Names'] for c in containers) or (q and "redis" in q[-1][0]):
                to_run = NUM_INSTANCES_REDIS - len(containers)
            if to_run > 0:
                q = run_last_from_q(q, results_path, to_run=to_run)
            containers = -1
        else:
            time.sleep(1)


def run_tests(generations, working_dir, bench_v, pass_k=1):
    bench_path_v = f"{working_dir}/bench/bench-{bench_v}"
    docker_path = f"{working_dir}/docker"
    results_path = f"{working_dir}/results/{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"
    shutil.copy(f"{working_dir}/results/run_single_example.py", f"{results_path}/run_single_example.py")

    docker_build(docker_path)
    bench, bench_js = read_bench_df(bench_path_v)

    # run tests
    run_tests_with_queue(results_path, generations, bench)

    # retry failed
    results = read_results(results_path)
    failed = {
        fn for repo, repo_res in results.items()
        for fn, fn_res in repo_res.items()
        if sum(int(res_dict.get("passed", False)) for res_dict in fn_res.values()) == 0
    }
    rm_results_for_fns(failed, results_path)
    generations_retry = {fn: gens for fn, gens in generations.items() if fn in failed}
    run_tests_with_queue(results_path, generations_retry, bench)

    # compute metrics
    results = read_results(results_path)
    results = {
        fn: {
            f"pass@{pass_k}": estimate_pass_at_k(n=len(fn_res), k=pass_k,
                                                 c=sum(int(res_dict.get("passed", False)) for res_dict in fn_res.values())),
            "exact_match": sum(exact_match(res_dict["generated_code"], bench_js[fn]["code"])
                               for res_dict in fn_res.values()) / len(fn_res),
            # "edit_similarity": sum(edit_similarity(res_dict["generated_code"], bench_js[fn]["code"])
            #                        for res_dict in fn_res.values()) / len(fn_res),
        }
        for repo, repo_res in results.items()
        for fn, fn_res in repo_res.items()
    }
    return [[results.get(fn, {f"pass@{pass_k}": 0, "exact_match": 0})] for fn in generations]
