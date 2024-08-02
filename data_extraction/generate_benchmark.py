import json
import os.path
import re
from collections import Counter, defaultdict
from datetime import datetime

import pandas as pd
from nltk.translate.bleu_score import sentence_bleu
from pandas import DataFrame
from tqdm import tqdm

VERSION = "bench-v0.6"
REPOSITORIES = ["bullet3", "openssl", "redis", "llvm"]
EDGES = ["stdlib", "same_file", "same_package", "project"]

EXAMPLES_PER_REPO = 155
EXAMPLES_PER_BENCH = 70
EXAMPLES_PROPORTIONS = {  # "bench-v0.1a"
    "none": 0.2,
    "stdlib": 0.2,
    "same_file": 0.2,
    "same_package": 0.2,
    "project": 0.2,
}
# EXAMPLES_PROPORTIONS = {  # "bench-v0.1b"
#     "none": 0.1,
#     "stdlib": 0.1,
#     "same_file": 0.35,
#     "same_package": 0.35,
#     "project": 0.1,
# }
EXAMPLES_PROPORTIONS = {k: v / s for k, v in EXAMPLES_PROPORTIONS.items() if (s := sum(EXAMPLES_PROPORTIONS.values()))}


def edge_level(f):
    for e in EDGES[::-1]:
        if f[e] > 0:
            return e
    return "none"


def has_test_hits(f):
    return f.test_cov_hits > 0


def has_docstring(f, length=3):
    if "Copyright" in f.doc:
        return False
    if "====" in f.doc:
        return False
    if re.search(r"[a-zA-Z0-9_]+[ \n\t\r]?\([ \n\t\r&,_a-zA-Z0-9]+\)[ \n\t\r]*{", f.doc) and "}" in f.doc:
        return False
    return f.doc and len(str(f.doc).split()) > length


def has_proper_code_len(f, low=2, high=15):
    # in lines of code
    code = extract_code(f.file, f.pos - 1, f.code_length)
    i = code.find("{")
    j = code.rfind("}")
    code_length = len(code[i+1:j].strip().split("\n"))
    return low <= code_length <= high


def is_not_test(f):
    return "test" not in f.file and "test" not in f.fname


def docstring_ok():
    docstring_215 = pd.read_csv("bench/docstring_215.csv")
    docstring_215["bad"] = docstring_215.apply(lambda x: f"{x.reviewer1}{x.reviewer2}{x.reviewer3}".count("-") >= 2, axis=1)
    docstring_labels = {x["Unnamed: 0.1.1"]: x["bad"] for _, x in docstring_215.iterrows()}

    def docstring_ok_(f):
        bad = docstring_labels.get(f["Unnamed: 0"], False)
        return not bad
    return docstring_ok_


def has_few_calls(f, max_num_calls=7):
    return f.calls_num <= max_num_calls


def filter_duplicates_weak(df: DataFrame, window=3000, bleu_thresh=0.2):
    df = df.sort_values(by="code_length")
    rows_txt = df.apply(lambda x: f"{x['fname']} {x['doc']}", axis=1).values
    code = []
    for _, row in df.iterrows():
        code.append(extract_code(row.file, row.pos - 1, row.code_length))

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


def extract_code(path, start, length):
    with open(f"repos/{path}", encoding="utf-8") as f:
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


def generate_json(df, path):
    jsons = {}
    for repo in REPOSITORIES:
        with open(f"final_table_wHits/{repo}.json", "r") as f:
            jsons[repo] = json.load(f)
    final = defaultdict(dict)
    for _, row in df.iterrows():
        i = row["Unnamed: 0"]
        final[i]["calls"] = jsons[row.repository][i]
        for c in final[i]["calls"]:
            if c["path"] and "/usr/include" not in c["path"]:
                c["path"] = "/".join(c["path"].split("/")[5:])
                if os.path.exists(f"repos/{c['path']}"):
                    c["code"] = extract_code(c["path"], c["start"]["line"], c["end"]["line"])
                else:
                    print(f"Path {c['path']} not found for {i}")
        final[i]["code"] = extract_code(row.file, row.pos - 1, row.code_length)

    with open(path, "w") as f:
        json.dump(final, f)


def plot_len_hist(code):
    import matplotlib.pyplot as plt
    lens = [len(c.split("\n")) for c in code]
    plt.hist(lens, range=(0, 50),bins=20)
    plt.show()


def main():
    tables = []
    for repository in REPOSITORIES:
        table = pd.read_csv(f"final_table_wHits/{repository}_wTestCovHits.csv")
        table["repository"] = repository
        tables.append(table)
    df = pd.concat(tables)
    df = df.dropna(subset="last_commit")
    df["doc"] = df["doc"].astype(str)

    code = []
    for _, row in df.iterrows():
        code.append(extract_code(row.file, row.pos - 1, row.code_length))

    # plot_len_hist(code)
    # raise

    def print_filtered(before_, after, text):
        d = before_ - after
        print(f"FILTER: {text}\n\tfiltered {d} rows (-{100*d/before_:.1f}%), {after} rows left")

    filter_list = [
        has_test_hits, has_docstring, has_proper_code_len, is_not_test, docstring_ok(), has_few_calls
    ]
    for f in filter_list:
        before = len(df)
        df = df[df.apply(lambda row: f(row), axis=1)]
        print_filtered(before, len(df), f.__name__)

    before = len(df)
    df = filter_duplicates_weak(df)
    print_filtered(before, len(df), "filter_duplicates_weak")

    df["commit_stamp"] = df.apply(lambda row: datetime.strptime(row.last_commit, '%d.%m.%Y').timestamp(), axis=1)

    final = []
    dev = []
    for repo in REPOSITORIES:
        table = df[df.repository == repo]
        edges = Counter(table.apply(lambda row: edge_level(row), axis=1).values)
        edges = sorted(edges.items(), key=lambda x: x[1])
        edges = [x[0] for x in edges]
        for e in edges:
            level_rows = table[table.apply(lambda row: edge_level(row), axis=1) == e]
            level_rows = level_rows.sort_values(by=["commit_stamp", "test_cov_hits"], ascending=[False, False])
            level_rows = level_rows.reset_index(drop=True)
            level_rows = level_rows.head(int(EXAMPLES_PER_REPO * EXAMPLES_PROPORTIONS[e]))

            level_rows_bench = level_rows.head(int(EXAMPLES_PER_BENCH * EXAMPLES_PROPORTIONS[e]))
            final.append(level_rows_bench)

            level_rows_dev = level_rows.tail(len(level_rows) - len(level_rows_bench))
            dev.append(level_rows_dev)
    df = pd.concat(final)
    df = df.reset_index(drop=True)

    print("BENCH")
    print(len(df))
    print(Counter(df.repository.values))
    print(Counter(df.apply(lambda row: edge_level(row), axis=1).values))
    for repo in REPOSITORIES:
        print(repo, "\n\t", Counter(df[df["repository"] == repo].apply(lambda row: edge_level(row), axis=1).values))

    df.drop("commit_stamp", axis=1, inplace=True)
    generate_json(df, f"{VERSION}.json")
    df.to_csv(f"{VERSION}.csv")

    df_dev = pd.concat(dev)
    df_dev = df_dev.reset_index(drop=True)

    print("DEV")
    print(len(df_dev))
    print(Counter(df_dev.repository.values))
    print(Counter(df_dev.apply(lambda row: edge_level(row), axis=1).values))
    for repo in REPOSITORIES:
        print(repo, "\n\t", Counter(df_dev[df_dev["repository"] == repo].apply(lambda row: edge_level(row), axis=1).values))

    df_dev.drop("commit_stamp", axis=1, inplace=True)
    generate_json(df_dev, f"{VERSION}_dev.json")
    df_dev.to_csv(f"{VERSION}_dev.csv")


if __name__ == "__main__":
    main()
