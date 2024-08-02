import json
import os
import re

import pandas as pd


REPOS_PATH = "/repos"


def read_json(path):
    if os.path.isfile(path):
        with open(path, "r") as f:
            return json.load(f)
    return {}


def extract_fn(path, start, length):
    if not os.path.isfile(f"{REPOS_PATH}/{path}"):
        return None

    with open(f"{REPOS_PATH}/{path}", encoding="utf-8") as f:
        lines = f.readlines()

    if start + length + 1 < len(lines) and lines[start + length].strip() != "}" and lines[start + length + 1].strip() == "}" and "}" not in lines[start + length]:
        start += 1
    elif start + length < len(lines) and lines[start + length].strip() != "}" and lines[start + length - 1].strip() == "}":
        start -= 1

    lines = lines[start:start + length + 1]
    result = "".join(lines)
    if "#if" in result and "#else" in result:
        result = []
        macros = 0
        els = False
        for line in lines:
            if "#endif" in line:
                macros -= 1
                els = False
                continue
            if "#if" in line:
                macros += 1
                continue
            elif macros and "#else" in line:
                els = True
                continue
            elif macros and not els:
                continue
            result.append(line)
        result = "".join(result)

    if not result or result.strip()[0] == "{" or result.strip()[-1] != "}":
        return None

    return result


def extract_code(df):
    code = []
    for _, row in df.iterrows():
        try:
            code.append(extract_fn(row.file, row.pos, row.code_length))
        except:
            code.append(None)
    return code


def extract_signature(code):
    signature = code.split('{')[0]
    return re.sub(f"[\r\n\t]+", "", signature)


def read_df(path):
    df = pd.read_csv(path)
    df["id"] = df["Unnamed: 0"].astype(str)
    df["doc"] = df["doc"].astype(str)
    df["code"] = extract_code(df)
    if "file" not in df.columns:
        df["file"] = df["path"].astype(str)
    if "fname" not in df.columns:
        df["fname"] = df["name"].astype(str)
    if "repository" not in df.columns:
        df["repository"] = df.apply(lambda row: row["file"].split("/")[0].split("-")[0], axis=1)
    return df
