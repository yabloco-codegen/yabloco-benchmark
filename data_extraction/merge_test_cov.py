import argparse
import re
from collections import defaultdict

import pandas as pd


def read(args, print_head=False):
    final = pd.read_csv(args.table_path, delimiter=args.table_delim)
    coverage = pd.read_csv(args.test_cov_path, delimiter=args.test_cov_delim)

    final["file_"] = final["path"]
    final.path = final.path.apply(lambda s: s.replace(args.table_path_prefix, ""))
    final.rename(columns={'path': 'file', "name": "fname"}, inplace=True)
    coverage.file = coverage.file.apply(lambda s: s.replace(args.test_cov_path_prefix, ""))

    if print_head:
        pd.set_option('display.expand_frame_repr', False)
        pd.set_option('max_colwidth', 400)
        print(final.head(5))
        print(coverage.head(5))
    return final, coverage


def print_files_stats(table, coverage):
    print("Files:")
    table_set = set(table.file.values)
    cov_set = set(coverage.file.values)
    print("\tTable:", len(table_set))
    print("\tCoverage:", len(cov_set))
    print("\tIntersection:", len(table_set & cov_set))


def get_cov_dict(coverage):
    cov_dict = defaultdict(lambda: defaultdict(int))
    for _, line in coverage.iterrows():
        f = line.fname.split("(")[0].strip().replace("void ", "")
        f = re.sub(r"<.*>", "", f).strip()
        if "test" not in f and ".inc" not in line.file:
            cov_dict[line.file.strip()][f] += line.hits

    return cov_dict


def print_fn_stats(table, cov_dict):
    print("Functions:")
    print("\tTable:", len(table))
    print("\tCoverage:", sum(len(v) for v in cov_dict.values()))
    intersection = set(table.fname.values) & set([k for d in cov_dict.values() for k in d])
    print("\tIntersection:", len(intersection))


def merge_hits(table, cov_dict, args):
    hits = []
    for _, row in table.iterrows():
        h = None
        p, n = row.file.strip(), row.fname.strip()
        if p in cov_dict:
            if n in cov_dict[p]:
                h = int(cov_dict[p][n])
        hits.append(h)

    if args.print:
        print("Functions with hits:", sum(x is not None for x in hits), "/", len(hits))

    table = table.assign(test_cov_hits=pd.Series(hits).values)
    return table


def main():
    # parser.add_argument('--table-path', default="final_tables/bullet3_final.csv")
    # parser.add_argument('--table-delim', default=",")
    # parser.add_argument('--table-path-prefix', default="bullet3/")
    # parser.add_argument('--test-cov-path', default="test_covs/bullet3_test_cov.csv")
    # parser.add_argument('--test-cov-delim', default="\t")
    # parser.add_argument('--test-cov-path-prefix', default="")
    # parser.add_argument('--project', default="bullet3")
    # 'system': 96, 'binary': 96, 'project': 6424

    # parser.add_argument('--table-path', default="final_tables/llvm_final.csv")
    # parser.add_argument('--table-delim', default=",")
    # parser.add_argument('--table-path-prefix', default="llvm-project/llvm/")
    # parser.add_argument('--test-cov-path', default="test_covs/llvm_test_cov.csv")
    # parser.add_argument('--test-cov-delim', default="\t")
    # parser.add_argument('--test-cov-path-prefix', default="build_cove/")
    # parser.add_argument('--project', default="llvm")
    # 'system': 2038, 'binary': 2038, 'project': 607668

    # parser.add_argument('--table-path', default="final_tables/redis_final.csv")
    # parser.add_argument('--table-delim', default=",")
    # parser.add_argument('--table-path-prefix', default="redis/src/")
    # parser.add_argument('--test-cov-path', default="test_covs/redis_test_cov.csv")
    # parser.add_argument('--test-cov-delim', default="\t")
    # parser.add_argument('--test-cov-path-prefix', default="")
    # parser.add_argument('--project', default="redis")
    # 'system': 2149, 'binary': 2149, 'project': 33356

    # parser.add_argument('--table-path', default="final_tables/libuv_final.csv")
    # parser.add_argument('--table-delim', default=",")
    # parser.add_argument('--table-path-prefix', default="libuv/")
    # parser.add_argument('--test-cov-path', default="test_covs/libuv_test_cov.csv")
    # parser.add_argument('--test-cov-delim', default="\t")
    # parser.add_argument('--test-cov-path-prefix', default="")
    # parser.add_argument('--project', default="libuv")
    # 'system': 972, 'binary': 972, 'project': 7188

    # parser.add_argument('--table-path', default="final_tables/openssl_final.csv")
    # parser.add_argument('--table-delim', default=",")
    # parser.add_argument('--table-path-prefix', default="openssl/")
    # parser.add_argument('--test-cov-path', default="test_covs/openssl_test_cov.csv")
    # parser.add_argument('--test-cov-delim', default="\t")
    # parser.add_argument('--test-cov-path-prefix', default="")
    # parser.add_argument('--project', default="openssl")
    # 'system': 2301, 'binary': 2301, 'project': 78013

    parser = argparse.ArgumentParser()

    parser.add_argument('--table-path', default="final_tables/bullet3_final.csv")
    parser.add_argument('--table-delim', default=",")
    parser.add_argument('--table-path-prefix', default="bullet3/")
    parser.add_argument('--test-cov-path', default="test_covs/bullet3_test_cov.csv")
    parser.add_argument('--test-cov-delim', default="\t")
    parser.add_argument('--test-cov-path-prefix', default="")
    parser.add_argument('--project', default="bullet3")
    parser.add_argument('--print', default=True)

    args = parser.parse_args()
    table, coverage = read(args, print_head=args.print)
    if args.print:
        print_files_stats(table, coverage)

    cov_dict = get_cov_dict(coverage)
    if args.print:
        print_fn_stats(table, cov_dict)

    final = merge_hits(table, cov_dict, args)
    if args.print:
        print(final.head(5))

    final["file"] = final["file_"]
    final.drop("file_", axis=1, inplace=True)
    final.to_csv(f"final_table_wHits/{args.project}_wTestCovHits.csv")


if __name__ == "__main__":
    main()
