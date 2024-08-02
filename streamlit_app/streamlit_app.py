import os.path

import pandas as pd
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from typing import List

import streamlit.components.v1 as components
from streamlit_ace import st_ace

from background_compute import already_tested
from read_data import read_bench_df, get_result_from_disk, get_result_time_from_disk
from results.run_single_example import run_single_example, get_new_content
from test_progress import show_test_progress, get_results

from config import *
from view import *
from utils import *


@dataclass
class Selection:
    bench_v: str = "bench-v0.6"
    repository: str = "bullet3"
    selected_fn: str = "79D9B4DB619F85EB"
    generated_i: str = "0"
    tags: List[str] = field(default_factory=list)
    in_progress: bool = False
    model: str = ""
    orig_checkbox: bool = False
    preprocess_checkbox: bool = True
    customize_checkbox: bool = False
    show_setting: str = "Default"


def stylize_gen_i(s, i=None):
    if i is None:
        i = s.generated_i

    if i == "Original":
        model, gen_i = "original", None
    else:
        model, gen_i = s.model, i

    r = get_result_from_disk(s.bench_v, model, s.repository, s.selected_fn, gen_i)
    if "passed" in r and r["passed"]:
        r = "passed"
    elif "built" in r and r["built"]:
        r = "built"
    elif "built" in r and not r["built"]:
        r = "failed"
    else:
        r = None

    colors = {
        "failed": "red",
        "built": "orange",
        "passed": "green"
    }
    return f":{colors[r]}[{i}]" if r is not None else f"{i}"


def reset_gen_i():
    # st.session_state.to_be_set = None
    st.session_state.generated_i = "0"


def choose_fn_arrows(d):
    gen_i = st.session_state.generated_i
    if d == -1 and gen_i == "0":
        gen_i = "Original"
    elif d == -1 and gen_i == "Original":
        gen_i = "9"
    elif d == 1 and gen_i == "Original":
        gen_i = "0"
    elif d == 1 and gen_i == "9":
        gen_i = "Original"
    else:
        gen_i = str(int(gen_i) + d)
    st.session_state.generated_i = gen_i


def csv_preconditions(bench, df, dfs, bench_v, model, options, gen_k):
    st.session_state.csv_error_msg = ""

    if "Unnamed: 0" not in df.columns:
        st.session_state.csv_error_msg += "Missing function id column: \"Unnamed: 0\"\n"
    if "repository" not in df.columns:
        df["repository"] = df.apply(
            lambda row: next(
                bench[bench_v][bench[bench_v]["Unnamed: 0"] == row["Unnamed: 0"]].iterrows()
            )[1]["repository"],
            axis=1,
        )
    if "fname" not in df.columns:
        df["fname"] = df.apply(
            lambda row: next(
                bench[bench_v][bench[bench_v]["Unnamed: 0"] == row["Unnamed: 0"]].iterrows()
            )[1]["fname"],
            axis=1,
        )
        # error_msg += "Missing function name column: \"fname\"\n"

    missing_columns = [f"{i}" for i in range(gen_k) if f"{i}" not in df.columns]
    if missing_columns:
        st.session_state.csv_error_msg += f"Missing generated code columns: {', '.join(missing_columns)}\n"

    def df_equal(d1, d2):
        d1 = d1.loc[:, [f"{i}" for i in range(gen_k)]]
        d2 = d2.loc[:, [f"{i}" for i in range(gen_k)]]
        return d1.equals(d2)

    identical = [i for x in dfs.values() for i, d in x.items() if df_equal(d, df)]
    if identical:
        st.session_state.csv_error_msg += f"Already uploaded: {identical[0]}.\n\n"

    if os.path.isfile(f"{BENCH_PATH}/{bench_v}/{model}-{options}.csv"):
        st.session_state.csv_error_msg += f"This combination of model and options is already occupied."

    return df


def update_all_metrics(bench_v, path, **kwargs):
    bench, bench_js, df = read_bench_df()

    cols = {
        "model": [],
        "repo": [],
        "pass@10": [],
        "pass@5": [],
        "pass@1": [],
        "ES": [],
        "EM": [],
    }

    for model in df[bench_v]:
        metrics = get_results(bench_v, bench, bench_js[bench_v], df, model, gen_k=10)[-1]
        for repo in ["bullet3", "llvm", "openssl", "redis"]:
            cols["model"].append(model)
            cols["repo"].append(repo)
            cols["pass@10"].append(metrics[repo]["pass_k"])
            cols["pass@5"].append(metrics[repo]["pass_5"])
            cols["pass@1"].append(metrics[repo]["pass_1"])
            cols["ES"].append(metrics[repo]["es"])
            cols["EM"].append(metrics[repo]["em"])

    res = pd.DataFrame(cols)
    res.to_csv(path)


def upload_csv(bench, dfs, s):
    gen_k = 10

    unsafe_md()
    popover = st.popover("⏏", use_container_width=True)
    with popover:
        bench_v = st.selectbox("Benchmark version", reversed(bench.keys()))
        unsafe_md("##### **Download model results**")
        unsafe_md("<hr>")
        path = f"{RESULTS_PATH}/{s.bench_v}/{s.model}/metadata.json"
        if os.path.isfile(path):
            with open(path, "rb") as file:
                st.download_button(
                    label=f"{s.model}.json",
                    data=file,
                    file_name=f"{s.model}.json",
                    use_container_width=True,
                )
        else:
            unsafe_md("Testing in progress...")

        unsafe_md("##### **Download all metrics**")
        unsafe_md("<hr>")
        path = f"{RESULTS_PATH}/all_metrics_{bench_v}_{datetime.now().date()}.csv"
        st.button("Compute all metrics csv", key="compute_all_csv", on_click=update_all_metrics,
                  args=(bench_v, path), use_container_width=True)
        if os.path.isfile(path):
            with open(path, "rb") as file:
                st.download_button(
                    label=f"all_metrics_{bench_v}_{datetime.now().date()}.csv",
                    data=file,
                    file_name=f"all_metrics_{bench_v}_{datetime.now().date()}.csv",
                    use_container_width=True,
                )

        unsafe_md("<br>")
        unsafe_md("##### **Upload csv to test**")
        unsafe_md("<hr>")
        model = st.text_input("Model", placeholder="CodeLlama-13B")
        options = st.text_input("Options", placeholder="method-repo-hyperparams")
        options = options.replace("_", "-").replace(" ", "-")

        def on_uploaded_file(*args, **kwargs):
            st.session_state.csv_uploaded = True

        uploaded_file = st.file_uploader("Choose a file", on_change=on_uploaded_file)

        if uploaded_file is not None and st.session_state.csv_uploaded:
            try:
                df = pd.read_csv(uploaded_file)
                csv_preconditions(bench, df, dfs, bench_v, model, options, gen_k)
            except Exception as e:
                st.session_state.csv_error_msg = str(e)

            def upload_btn():
                model_name = f"{model}-{options}" if options else model
                df.to_csv(f"{BENCH_PATH}/{bench_v}/{model_name}.csv")
                st.session_state.csv_uploaded = False
                success("Success!", sucs)

            if st.session_state.csv_error_msg:
                error(st.session_state.csv_error_msg)
            else:
                st.button("Upload", on_click=upload_btn, use_container_width=True)
            sucs = st.container()


def model_options(bench, model):
    unsafe_md()
    popover = st.popover("**⋮**", use_container_width=True)
    model_path = f"{BENCH_PATH}/{bench}/{model}.csv"
    model_results_path = f"{RESULTS_PATH}/{bench}/{model}/"
    with popover:
        unsafe_md("**Uploaded date:**")
        uploaded_date = datetime.fromtimestamp(os.path.getmtime(model_path))
        unsafe_md(uploaded_date.strftime("%d.%m.%y %H:%M"))

        unsafe_md("**Rename:**")
        if os.path.isfile(f"{RESULTS_PATH}/{bench}/{model}/metadata.json"):
            unsafe_md("<span style=\"font-size:14px;\">Current name</span>")
            unsafe_md(f"<span style=\"margin: ; background-color: rgb(240, 242, 246);\">{model}</span>")
            model_new = st.text_input("New name", placeholder="CodeLlama-13B-options")

            def rename_btn():
                os.rename(model_path, f"{BENCH_PATH}/{bench}/{model_new}.csv")
                os.rename(model_results_path, f"{RESULTS_PATH}/{bench}/{model_new}/")
                success("Success!", sucs)

            if os.path.isfile(f"{BENCH_PATH}/{bench}/{model_new}.csv"):
                error("Name is occupied")
            elif model_new:
                st.button("Rename", on_click=rename_btn, use_container_width=True)
        else:
            unsafe_md("Testing in progress...")
        sucs = st.container()


def header_left(bench, df, s, bench_select, repo_select, model_select, model_options_btn, upload, tags_select,
                in_progress, fn_select):
    s.bench_v = bench_select.selectbox("Benchmark", df.keys(), key="bench_v", on_change=reset_gen_i, index=1)
    s.repository = repo_select.selectbox("Repository", REPOS, key="repo", on_change=reset_gen_i)

    models_list = df[s.bench_v].keys()
    counts = Counter([x for m in models_list for x in m.split("-")])
    counts_sorted = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    tags = set(x for x, c in counts_sorted if re.search(r"\d+", x) is None and c > 1 and len(x) > 2)

    s.tags = tags_select.multiselect("Tag filter", tags)
    models_list_filtered = [m for m in models_list if all(x in m for x in s.tags)] if s.tags else models_list

    unsafe_md("", in_progress)
    unsafe_md("", in_progress)
    in_progress_models = [
        m for m in models_list_filtered
        if not os.path.isfile(f"{RESULTS_PATH}/{s.bench_v}/{m}/metadata.json")
    ]
    s.in_progress = in_progress.toggle("In progress", disabled=not in_progress_models)
    if s.in_progress:
        models_list_filtered = in_progress_models

    s.model = model_select.selectbox("Model", models_list_filtered, key="model", on_change=reset_gen_i)

    with upload:
        upload_csv(bench, df, s)

    with model_options_btn:
        model_options(s.bench_v, s.model)

    b = bench[s.bench_v]
    with fn_select:
        filtered_df = b.loc[b["repository"] == s.repository]
        df_fns = set(df[s.bench_v][s.model]["Unnamed: 0"].values)
        functions = [f"{x['Unnamed: 0']}: {x['fname']}" for _, x in filtered_df.iterrows()]
        functions = [f for f in functions if f.split(": ")[0] in df_fns] + \
                    [f"{f} (absent)" for f in functions if f.split(": ")[0] not in df_fns]

        i = 0
        if "to_be_set" in st.session_state and st.session_state.to_be_set is not None:
            to_be_set_fn, gen_i = st.session_state.to_be_set
            if gen_i is not None:
                st.session_state.generated_i = gen_i
                st.session_state.to_be_set = (to_be_set_fn, None)
                i = [f.split(":")[0] for f in functions].index(to_be_set_fn)
            elif st.session_state.selected_fn in functions:
                i = functions.index(st.session_state.selected_fn)
            else:
                i = 0

        selected_fn = st.selectbox('Function', functions, key="selected_fn", index=i, on_change=reset_gen_i)
        s.selected_fn = selected_fn.split(": ")[0]


def header_right(bench, bench_js, df, s, generated, settings, left_btn, right_btn, test_progress):
    # todo: generation using LLM
    # input_text = st.text_input('Enter text here', value='', max_chars=100, key='input_text')
    # submit_button = st.button('Generate')

    with generated:
        s.generated_i = st.radio("Generation",
                                 options=[f"{i}" for i in range(10)] + ["Original"],
                                 format_func=lambda i: stylize_gen_i(s, i),
                                 key="generated_i", horizontal=True)
        s.orig_checkbox = s.generated_i == "Original"

    with settings:
        unsafe_md()
        popover = st.popover("Settings", use_container_width=True)
        s.preprocess_checkbox = popover.toggle("Preprocess", True)
        s.customize_checkbox = popover.toggle("Customize", False)
        unsafe_md("<br>", popover)
        _, row = next(bench[s.bench_v][bench[s.bench_v]["Unnamed: 0"] == s.selected_fn].iterrows())
        if os.path.isfile(f"{REPOS_PATH}/{row['file']}"):
            s.show_setting = popover.radio("Function display mode",
                                           options=["Default", "Show in file", "Show original file"])

    unsafe_md(left_btn)
    left_btn.button("←", on_click=lambda: choose_fn_arrows(-1), use_container_width=True)

    unsafe_md(right_btn)
    right_btn.button("→", on_click=lambda: choose_fn_arrows(1), use_container_width=True)

    with test_progress:
        unsafe_md()
        show_test_progress(s, bench[s.bench_v], bench_js[s.bench_v], df)


def header(bench, bench_js, df):
    bench_select, repo_select, tags_select, in_progress, test_progress = st.columns([
        6, 5, 7, 6,
        24,
    ])
    model_select, model_options_btn, upload, generated = st.columns([
        12, 2, 2,
        16,
    ])
    fn_select, left_btn, right_btn, settings = st.columns([
        16,
        3, 3, 10,
    ])

    s = Selection()
    s.model = list(df[s.bench_v].keys())[0]
    if "generated_i" not in st.session_state:
        st.session_state.generated_i_format = stylize_gen_i(s)
        st.session_state.csv_uploaded = False
        st.session_state.csv_error_msg = ""

    header_left(bench, df, s, bench_select, repo_select, model_select, model_options_btn, upload, tags_select,
                in_progress, fn_select)
    header_right(bench, bench_js, df, s, generated, settings, left_btn, right_btn, test_progress)
    return s


def show_built(has_built, has_passed, error_msg, edit_sim, spent_time):
    b, p, es, t = st.columns([1, 1, 1, 1])
    with b:
        _ = success('Build: Successful') if has_built else error('Build: Failed')
    with p:
        _ = success('Pass: Successful') if has_passed else error('Pass: Failed')
    with es:
        info(f"Edit Similarity: {edit_sim}")
    with t:
        start, finish = spent_time
        info(f"Time: {format_time(finish - start, short=True)}")

    if error_msg:
        exception(error_msg)


def body_left(orig_code, row):
    st.code(orig_code, language="cpp", line_numbers=True)
    info(f"Comment:\n {row['doc']}", center=False)
    info(f"Path:\n{row['file']}:{row['pos']}-{row['pos'] + row['code_length']}", center=False)
    info(f"Last commit:\n{row['last_commit']}", center=False)
    info(f"Test Coverage Hits:\n{int(row['test_cov_hits'])}", center=False)
    info(f"External Context:\nstdlib: {row['stdlib']}, same_file: {row['same_file']}, "
         f"same_package: {row['same_package']}, project: {row['project']}", center=False)


def body_right_code(row, gen_code, s):
    orig_file = f"{REPOS_PATH}/{row['file']}"
    if s.show_setting == "Show in file":
        with open(orig_file) as f:
            lines = f.readlines()

        new_code = gen_code if s.orig_checkbox or s.preprocess_checkbox else parse_generation(gen_code)
        show_code = get_new_content(lines, row, new_code)
    elif s.show_setting == "Show original file":
        with open(orig_file) as f:
            show_code = "".join(f.readlines())
    else:
        show_code = gen_code.strip()

    if s.customize_checkbox:
        gen_code = st_ace(value=show_code, height=400, font_size=15, language="c_cpp",
                          theme="dawn", auto_update=True, show_gutter=True)
    else:
        st.code(show_code, language="cpp", line_numbers=True)

    if not s.orig_checkbox and not s.preprocess_checkbox:
        gen_code = parse_generation(gen_code)

    return gen_code


def body_right_results(row, gen_code, s, model, edit_sim):
    # default menu with build button
    pre_build = st.empty()
    with pre_build:
        btn, es, _, _ = st.columns([1, 1, 1, 1])
        build_btn = btn.button("Build & Run", key="build_btn", use_container_width=True)
        info(f"Edit Similarity: {edit_sim}", module=es)

    ind = get_ind(s.bench_v, model, s.repository, s.selected_fn,
                  s.generated_i if not s.customize_checkbox else "custom")

    # if results already present for this generated code
    gen_i = None if model == "original" else s.generated_i
    args = (s.bench_v, model, row["repository"], s.selected_fn, gen_i)
    if not s.customize_checkbox and already_tested(
            None, s.bench_v, model, row, s.selected_fn, gen_code, gen_i, ind
    ):
        r = get_result_from_disk(*args)
        has_built, has_passed, error_msg = r["built"], r["passed"], r.get("error", "")
        spent_time = get_result_time_from_disk(*args)

        pre_build.empty()
        show_built(has_built, has_passed, error_msg, edit_sim, spent_time)

    # when build button clicked
    if build_btn:
        pre_build.empty()
        with st.spinner("Building project and running tests..."):
            start = int(time.time())
            has_built, has_passed, error_msg = run_single_example(row, gen_code, s.repository, ind)
            finish = int(time.time())
            show_built(has_built, has_passed, error_msg, edit_sim, (start, finish))


def body(bench, bench_js, df, s):
    bench = bench[s.bench_v]
    bench_js = bench_js[s.bench_v]

    orig_code = bench_js[s.selected_fn]["code"]
    curr_df = df[s.bench_v][s.model]
    _, row = next(bench[bench["Unnamed: 0"] == s.selected_fn].iterrows())

    if len(curr_df[curr_df["Unnamed: 0"] == s.selected_fn]) == 0:
        error(f"{s.selected_fn} is present in {s.bench_v} but not in the csv-file of {s.model}.", False)
        return

    if s.orig_checkbox:
        gen_code = orig_code
        model = "original"
    else:
        gen_code = curr_df[curr_df["Unnamed: 0"] == s.selected_fn][f"{s.generated_i}"].values[0]
        model = s.model
        if s.preprocess_checkbox:
            gen_code = parse_generation(gen_code)

    left, right = st.columns([1, 1])
    with left:
        body_left(orig_code, row)

    with right:
        gen_code = body_right_code(row, gen_code, s)
        edit_sim = edit_similarity_score(gen_code, orig_code)
        body_right_results(row, gen_code, s, model, edit_sim)


def inspect(bench, bench_js, df):
    selection = header(bench, bench_js, df)
    body(bench, bench_js, df, selection)
    components.html(COMPONENTS_CONFIGURATION)


def main():
    bench, bench_js, df = read_bench_df()
    setup()
    inspect(bench, bench_js, df)


if __name__ == "__main__":
    main()
