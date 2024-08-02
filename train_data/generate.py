import json
import re

import pandas as pd
from nltk.translate.bleu_score import sentence_bleu
from pandas import DataFrame
from tqdm import tqdm

VERSION = "bench-v0.6"
REPOSITORIES = ["bullet3", "openssl", "redis", "llvm"]
EDGES = ["stdlib", "same_file", "same_package", "project"]


def has_docstring(f, length=3):
    if "Copyright" in f.doc:
        return False
    if "====" in f.doc:
        return False
    if re.search(r"[a-zA-Z0-9_]+[ \n\t\r]?\([ \n\t\r&,_a-zA-Z0-9]+\)[ \n\t\r]*{", f.doc) and "}" in f.doc:
        return False
    return f.doc and len(str(f.doc).split()) > length


def has_proper_code_len(f, low=2, high=50):
    # in lines of code
    try:
        code = extract_fn(f.file, f.pos - 1, f.code_length)
    except:
        return False

    i = code.find("{")
    j = code.rfind("}")
    code_length = len(code[i+1:j].strip().split("\n"))
    return low <= code_length <= high


def is_not_test(f):
    return "test" not in f.file and "test" not in f.fname


def has_few_calls(f, max_num_calls=10):
    return f.calls_num <= max_num_calls


def extract_fn(path, start, length):
    with open(f"../pipeline/repos/{path}", encoding="utf-8") as f:
        lines = f.readlines()
    code = lines[start:start + length + 1]
    result = "".join(code)
    if "#if" in result and "#else" in result:
        result = []
        macros = 0
        for line in code:
            if "#endif" in line:
                continue
            if "#if" in line:
                macros += 1
                continue
            elif macros and "#else" in line:
                macros -= 1
                continue
            elif macros:
                continue
            result.append(line)
        result = "".join(result)

    return result


def extract_code(df):
    code = []
    for _, row in df.iterrows():
        try:
            code.append(extract_fn(row.file, row.pos - 1, row.code_length))
        except:
            code.append(None)
    return code


def filter_duplicates_weak(df: DataFrame, window=3000, bleu_thresh=0.2):
    df = df.sort_values(by="code_length")
    rows_txt = df.apply(lambda x: f"{x['fname']} {x['doc']}", axis=1).values
    code = extract_code(df)

    rows_txt = [re.sub(r"[^a-zA-Z0-9]", " ", f"{s} {c}") for s, c in zip(rows_txt, code)]
    rows_txt = [re.sub(r"\s+", " ", s).split() for s in rows_txt]
    calls_num = df.calls_num.values

    df = df.reset_index(drop=True)
    duplicates = set()
    for i, row in tqdm(df.iterrows(), total=len(df)):
        if not isinstance(i, int):
            print("warning: df index type")
            continue

        if i in duplicates:
            continue

        candidate_ids = [
            j for j in range(i + 1, i + window)
            if j < len(rows_txt) and abs(calls_num[i] - calls_num[j]) <= 3 and len(set(rows_txt[i]) & set(rows_txt[j])) >= 5
        ]
        for j in candidate_ids:
            if sentence_bleu([rows_txt[i]], rows_txt[j], weights=(0.5, 0.5)) >= bleu_thresh:
                duplicates.add(j)

    df = df[~df.index.isin(duplicates)]
    df = df.reset_index(drop=True)
    return df


def get_ids(path, repo):
    df = pd.read_csv(path)
    df = df[df.repository == repo]
    return set(df["Unnamed: 0"].values)


def get_test_dev(repo):
    return get_ids("../pipeline/bench/bench-v0.6.csv", repo) | get_ids("../pipeline/bench/bench-v0.6_dev.csv", repo)


def get_all(repo):
    df = pd.read_csv(f"../pipeline/final_tables/{repo}_final.csv")
    df["doc"] = df["doc"].astype(str)
    if "file" not in df.columns:
        df["file"] = df["path"].astype(str)
    if "fname" not in df.columns:
        df["fname"] = df["name"].astype(str)
    return df


def get_prev(repo, ids):
    with open(f"prev/{repo}-prev.json") as f:
        prev = json.load(f)

    result = []
    for i in ids:
        r = [p for p in prev[i] if p["id"] not in ids]
        result.extend(r)
    return result


def print_filtered(fn, text, df):
    before = len(df)
    if before == 0:
        print("No examples left!")
        return df

    df = fn(df)
    d = before - len(df)
    print(f"FILTER: {text}\n\tfiltered {d} rows (-{100*d/before:.1f}%), {len(df)} rows left")
    return df


def process_repo(repo):
    print(f"REPO: {repo}")
    df = get_all(repo)
    test_dev_ids = get_test_dev(repo)
    prev = get_prev(repo, test_dev_ids)
    prev_ids = {p["id"] for p in prev}

    filter_list = [has_docstring, has_proper_code_len, is_not_test, has_few_calls]
    for f in filter_list:
        df = print_filtered(lambda d: d[d.apply(f, axis=1)], f.__name__, df)

    for n, s in [("is_test_dev", test_dev_ids), ("is_test_dev_prev", prev_ids)]:
        df = print_filtered(lambda d: d[d.apply(lambda row: row["Unnamed: 0"] not in s, axis=1)], n, df)

    df = print_filtered(filter_duplicates_weak, "filter_duplicates_weak", df)

    if len(df) > 0:
        df.to_csv(f"train_functions/{repo}-train.csv")


def main():
    for repo in REPOSITORIES:
        process_repo(repo)


if __name__ == "__main__":
    main()
