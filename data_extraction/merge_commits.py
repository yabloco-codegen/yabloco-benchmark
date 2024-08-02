import argparse
import datetime
import json

import pandas as pd
from tqdm import tqdm

from db_stat import get_func_info


def add_pos(csv, db_path):
    pos_col = []
    for _, row in tqdm(csv.iterrows()):
        func_info = get_func_info(row[0], db_path)
        pos_col.append(func_info[0]['pos']['line'])

    csv["pos"] = pos_col


def add_commits(main_table, commits):
    commit_date = []
    for index, row in tqdm(main_table.iterrows()):
        if row["path"] in commits.keys():
            com = commits[row["path"]]
            if len(com) != 0:
                start = row["pos"]
                end = start + row["code_length"]
                func_lines = com[start-1:end-1]
                func_lines = sorted(func_lines, key=lambda x: datetime.datetime.strptime(x, '%d.%m.%Y'))
                last_commit = ""
                if len(func_lines) != 0:
                    last_commit = func_lines[-1]
                commit_date.append(last_commit)
        else:
            commit_date.append("")
    main_table["last_commit"] = commit_date


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--table-path')
    parser.add_argument('--db-path')
    parser.add_argument('--commits-path')
    parser.add_argument('--out-path')

    args = parser.parse_args()

    table = pd.read_csv(args.table_path)

    with open(args.commits_path, 'r') as f:
        commits = json.load(f)
        commits = {k.replace("\\", '/'): v for k, v in commits.items()}
        commits = {k: [date for _, date in v.items()] for k, v in commits.items()}

    add_pos(table, args.db_path)
    add_commits(table, commits)

    table.to_csv(args.out_path)


if __name__ == "__main__":
    main()
