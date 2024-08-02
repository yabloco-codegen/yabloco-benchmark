import argparse
import json
import os
import subprocess

import pandas as pd
from tqdm import tqdm


STATS = {
    "system": 0,
    "binary": 0,
    "project": 0,
    "empty": 0,
    "other": 0,
}


def get_callgraph(func_id, w_path, path="", i=""):
    json_query = {"query": "callgraph",
                  "function": func_id,
                  "path": path,
                  "macros": False}

    with open(f"tmp{i}.json", "w") as outfile:
        json.dump(json_query, outfile)

    command = f"./codegraph_tool query --index-database-path {w_path} --pretty-print  < tmp{i}.json"
    out = ""

    try:
        out = subprocess.run(command, shell=True, capture_output=True, encoding='utf-8', timeout=10).stdout
    except subprocess.TimeoutExpired:
        print("Timeout reached.")
        return json.loads("{}")
    except Exception as exp:
        print(f"Unexpected exception: {exp}")

    if out:
        return json.loads(out)

    # print("Return null info about func")
    return json.loads("{}")


def get_func_info(func_id, w_path, i=""):
    with open(f"query{i}.json", "w") as f:
        json.dump({"query": "goto", "id": func_id}, f)

    command = f"./codegraph_tool query --index-database-path {w_path} --pretty-print  < query{i}.json > query_answer{i}.json"
    subprocess.run(command, shell=True, capture_output=True, encoding='utf-8')

    with open(f"query_answer{i}.json", "r") as f:
        file = "\n".join(f.readlines())

    json_dump = json.loads("{}")
    try:
        with open(f"query_answer{i}.json", "r") as f:
            json_dump = json.load(f)
    except Exception as exp:
        print(f"Unexpected exception in get_func_info: {exp}\n{file}")
    return json_dump


def process_callgraph(main_func_info, db_path, i=""):
    if set(main_func_info).difference(['id', 'name', 'pos', 'prev', 'next', 'doc']):
        print(main_func_info.keys())

    edge_dirs = ['prev', 'next']
    func_num = {k: 0 for k in edge_dirs}
    funcs_id = {k: [] for k in edge_dirs}
    for direction in edge_dirs:
        if direction not in main_func_info:
            continue

        func_num[direction] = len(main_func_info[direction])
        for func_id in main_func_info[direction]:
            func = get_func_info(func_id["id"], db_path, i) or [dict()]
            func = func[0]

            name = func.get("name", "")
            path = func.get("pos", {}).get("path", "")
            system = func.get("system", False)
            if "pos" in func and "line" in func["pos"] and "col" in func["pos"]:
                func["start"] = {"line": func["pos"]["line"], "col": func["pos"]["col"]}

            funcs_id[direction].append([func_id["id"], name, path, system, func.get("start", {}), func.get("end", {})])

            if system:
                STATS["system"] += 1
            if "/home" in path:
                STATS["project"] += 1
            elif "/usr/include" in path:
                STATS["binary"] += 1
            elif path == "":
                STATS["empty"] += 1
            else:
                STATS["other"] += 1
                print("!!", path)

    try:
        return {
            'name': main_func_info['name'],
            'path': main_func_info['pos']['path'],
            'doc': main_func_info.get("doc", ""),
            'calls_num': func_num['prev'],
            'prev_funcs': funcs_id['prev'],
            'dep_num': func_num['next'],
            'next_funcs':  funcs_id['next']
        }
    except Exception as e:
        print(f"Unexpected exception in get_func_info: {e}\n{main_func_info}")
        return None


def parse_groups(data, length):
    file_path = data["path"]
    same_file = 0
    same_package = 0
    another_package = 0
    stdlib = 0
    external_binaries = 0

    def _get_dir(path):
        if "/" in path:
            return "/".join(path.split("/")[:-1])
        elif "\\" in path:
            return "\\".join(path.split("\\")[:-1])
        return path

    for next_ in data['next_funcs']:
        next_path = next_[2]
        if len(next_path) > 1:
            if next_[3]:
                stdlib += 1
            elif next_path.startswith("/usr/include"):
                external_binaries += 1
            elif next_path == file_path:
                same_file += 1
            elif _get_dir(next_path) == _get_dir(file_path):
                same_package += 1
            else:
                another_package += 1

    data["same_file"] = same_file
    data["same_package"] = same_package
    data["project"] = another_package
    data["stdlib"] = stdlib
    data["external_binaries"] = external_binaries
    data["code_length"] = length


def get_dataset(functions, project_path, project_root, db_path, i=""):
    project_path = os.path.abspath(project_path)
    final_dataset = {}

    for func in tqdm(functions):
        func_info = get_func_info(func['_key'], db_path, i=i)
        is_valid = False
        length = 0

        if len(func_info) != 0:
            func_info = func_info[0]
            if project_root in func_info["pos"]["path"]:
                length = func_info["end"]["line"] - func_info["pos"]["line"]
                if length != 0:
                    is_valid = True

        if is_valid:
            func_callgraph = get_callgraph(func_info["id"], db_path, func_info["pos"]["path"], i=i)
            if func_callgraph:
                data = process_callgraph(func_callgraph[0], db_path, i=i)
                if data is not None:
                    parse_groups(data, length)
                    data["path"] = data["path"].replace(project_path, "", 1)[1:]
                    final_dataset.update({func_info["id"]: data})
    return final_dataset


def get_json(data, d):
    result = {}
    for _, fn in data.iterrows():
        result[fn.name] = []
        for next_ in fn[f'{d}_funcs']:
            res = {
                "id": next_[0],
                "name": next_[1],
                "path": next_[2],
                "start": next_[4],
                "end": next_[5],
            }
            result[fn.name].append(res)

    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--nodes-path')
    parser.add_argument('--db-path')
    parser.add_argument('--project-path')
    parser.add_argument('--project-root')
    parser.add_argument('--out_path')
    parser.add_argument('--parallel', type=int, default=-1)
    parser.add_argument('--parallel-i', type=int, default=-1)

    args = parser.parse_args()

    if args.parallel == -1:
        with open(args.nodes_path, 'r') as file:
            functions = json.load(file)

        dataset = get_dataset(functions, args.project_path, args.project_root, args.db_path)
        data = pd.DataFrame.from_dict(dataset).transpose()

        # next_json = get_json(data, d="next")
        # with open(f"{args.out_path}.json", "w") as f:
        #     json.dump(next_json, f)

        prev_json = get_json(data, d="prev")
        with open(f"{args.out_path}-prev.json", "w") as f:
            json.dump(prev_json, f)

        # data = data.drop("next_funcs", axis=1)
        # data = data.drop("prev_funcs", axis=1)
        # data.to_csv(f"{args.out_path}")
        # print(STATS)


if __name__ == '__main__':
    main()
