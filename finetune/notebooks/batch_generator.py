import random
import time

from utils import *


GET_SIZE = {
    "tokens": lambda tokenizer: (lambda f: len(tokenizer.tokenize(f['code']))),
    "lines": lambda f: len(f['code'].split("\n")),
    "symbols": lambda f: len(f['code']),
    "functions": lambda _: 1,
}


def get_formatted_function(fn) -> str:
    doc = fn.doc.replace('\n', '\n//')
    result = f"// File name: {fn['file']}\n// Comment: {doc}\n{fn['code']}"
    return result


def get_oracle_context(fn, next_json, all_df, all_df_ids, same_file=False):  # , fn2file, file2fns
    context = {x["id"] for x in next_json[fn["id"]] if x["id"] in all_df_ids}  # function calls
    if same_file:
        same_file = {x["id"] for _, x in all_df.iterrows() if fn["file"] == x["file"]}  # files2fns[fn2file[fn.id]]
        context.union(same_file)

    return context


def get_random_context(fn, oracle, df, size, size_in="functions", tokenizer=None):
    df = df[df.apply(lambda x: x["id"] != fn["id"] and x["id"] not in oracle, axis=1)]
    df = df.sample(frac=1)

    get_size_ = GET_SIZE[size_in]
    if size_in == "tokens" and tokenizer is None:
        raise ValueError("Tokenizer must be passed when using tokens.")
    elif size_in == "tokens":
        get_size_ = get_size_(tokenizer)

    result = []
    size_so_far = 0
    for _, row in df.iterrows():
        if not row["code"]:
            continue
        s = get_size_(row)
        if size_so_far + s <= size:
            result.append(row["id"])
            size_so_far += s
        else:
            # smarter inclusion by skipping long functions
            break

    return set(result)


def truncate(fns, proportion, max_context_size, all_df, size_in, tokenizer=None):
    get_size_ = GET_SIZE[size_in]
    if size_in == "tokens" and tokenizer is None:
        raise ValueError("Tokenizer must be passed when using tokens.")
    elif size_in == "tokens":
        get_size_ = get_size_(tokenizer)

    size = sum([get_size_(next(all_df[all_df["id"] == f].iterrows())[1]) for f in fns]) if fns else 0
    if size > proportion * max_context_size:
        sizes = sorted([(get_size_(next(all_df[all_df["id"] == f].iterrows())[1]), f) for f in fns], reverse=True)
        while size > proportion * max_context_size and sizes:
            size -= sizes[0][0]
            sizes = sizes[1:]
            if not sizes and size > proportion * max_context_size:
                print(size, proportion, max_context_size, fns)
        fns = set(f[1] for f in sizes)
    return fns


def get_context(fn, oracle_proportion, max_context_size, all_df, all_df_ids,
                next_json, size_in="functions", tokenizer=None, **kwargs):
    oracle = get_oracle_context(fn, next_json, all_df, all_df_ids)
    context = truncate(oracle, oracle_proportion, max_context_size, all_df, size_in, tokenizer)

    if oracle_proportion < 1:
        rnd = get_random_context(fn, oracle, all_df, size=2 * max_context_size,
                                 size_in=size_in, tokenizer=tokenizer)
        rnd = truncate(rnd, 1 - oracle_proportion, max_context_size, all_df, size_in, tokenizer)
        context = context.union(rnd)

    result = [get_formatted_function(next(all_df[all_df["id"] == i].iterrows())[1]) for i in context]
    return result


def generator(oracle_proportion, max_context_size, train_df, all_df, next_json, size_in, tokenizer=None, seed=0):
    all_df_ids = {row.id for _, row in all_df.iterrows()}
    for _, row in train_df.iterrows():
        ctx = get_context(row, oracle_proportion, max_context_size, all_df, all_df_ids, next_json, size_in, tokenizer)

        random.seed(seed)
        random.shuffle(ctx)
        ctx = "\n\n".join(ctx)
        code = extract_fn(row["file"], row["pos"], row["code_length"])

        yield {
            "context": ctx,
            "signature": extract_signature(code),
            "doc": row["doc"],
            "code": code,
            "repo": row["repository"]
        }


def get_all_df_filtered(repo, next_json):
    all_df = read_df(f"/train_data/train_functions/final_tables/{repo}_final.csv")
    for _, row in all_df.iterrows():
        code = extract_fn(row["file"], row["pos"], row["code_length"])
        if code:
            row["code"] = code

    bench = {row.id for _, row in read_df("/bench/bench-v0.6.1.csv").iterrows()}
    dev = {row.id for _, row in
           read_df(f"/bench/bench-v0.6_dev.csv").iterrows()}

    all_df["id"] = all_df["Unnamed: 0"].astype(str)
    bench_dev_next_ids = {
        row.id for _, row in all_df.iterrows()
        if row.id in next_json and any(n["id"] in bench | dev for n in next_json[row.id])
    }
    all_df_filtered = all_df[all_df.apply(lambda row: row.id not in bench | dev | bench_dev_next_ids, axis=1)]
    return all_df_filtered
