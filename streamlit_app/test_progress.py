import numpy as np
import streamlit as st

from background_compute import rerun
from read_data import read_cached_model_results, read_cached_only_results

from config import REPOS
from metrics import edit_similarity_score, exact_match_score, pass_at_k
from view import unsafe_md
from utils import format_time


COLUMNS_RESULTS = [3, 4, 3, 3, 2, 2]
COLUMNS_METRICS = [2, 2, 2, 2, 3]
LAMBDAS = {
    "all": lambda res: "built" in res,
    "failed": lambda res: "built" in res and not res["built"] and res.get("error", "") != "Timeout",
    "built": lambda res: "built" in res and res["built"] and "passed" in res and not res["passed"],
    "passed": lambda res: "built" in res and res["built"] and "passed" in res and res["passed"],
    "timeout": lambda res: res.get("error", "") == "Timeout",
}


def get_avg_time(repo, label_lambda, model_results, results_time):
    fns = results_time.get(repo, {})
    times = [
        t[1] - t[0]
        for c, gens in fns.items()
        for gen, t in gens.items()
        if label_lambda(model_results.get(repo, {}).get(c, {}).get(gen, {})) and isinstance(t, (tuple, list)) and len(t) == 2
    ]
    return np.mean(times) if times else -1


def get_total_time(repo, label_lambda, model_results, results_time):
    fns = results_time.get(repo, {})
    times = sorted([
        t
        for c, gens in fns.items()
        for gen, t in gens.items()
        if label_lambda(model_results.get(repo, {}).get(c, {}).get(gen, {})) and isinstance(t, (tuple, list)) and len(t) == 2
    ])
    result, last_start, last_finish = 0, -1, -1
    for start, finish in times:
        if last_start == -1:
            last_start = start
            last_finish = finish
        elif start >= last_finish:
            result += last_finish - last_start
            last_start = start
            last_finish = finish
        elif finish >= last_finish:
            last_finish = finish
    result += last_finish - last_start
    return result


def get_model_time(*args):
    times = {
        r: {
            k: (get_avg_time(r, fn, *args), get_total_time(r, fn, *args))
            for k, fn in LAMBDAS.items()
        }
        for r in REPOS
    }
    return times


def get_stats(model_results):
    def _iter(repo, cond):
        return [
            c for gens in model_results.get(repo, {}).values() for c, res in gens.items()
            if cond(res)
        ]

    result = {
        r: {
            k: _iter(r, fn)
            for k, fn in LAMBDAS.items()
        }
        for r in REPOS
    }
    result["overall"] = {k: [f"{r}/{x}" for r in REPOS for x in result[r][k]] for k in LAMBDAS}
    return result


def get_metrics(results, bench_js):
    results["overall"] = {k: v for r in results.values() for k, v in r.items()}
    passed_or_not = {
        r: [[int(g.get("passed", False)) for g in gens.values()] for fn, gens in fns.items()]
        for r, fns in results.items()
    }
    predictions = {
        r: [g["generated_code"] for fn, gens in fns.items() for g in gens.values()]
        for r, fns in results.items()
    }
    ground_truths = {
        r: [bench_js[fn]["code"] for fn, gens in fns.items() for _ in gens]
        for r, fns in results.items()
    }
    result = {
        r: {
            "pass_k": pass_at_k(passed_or_not[r]) if r in predictions else 0,
            "pass_5": pass_at_k(passed_or_not[r], k=5) if r in predictions else 0,
            "pass_1": pass_at_k(passed_or_not[r], k=1) if r in predictions else 0,
            "es": edit_similarity_score(predictions[r], ground_truths[r]) if r in predictions else 0,
            "em": exact_match_score(predictions[r], ground_truths[r]) if r in predictions else 0,
        }
        for r in ["overall"] + REPOS
    }
    return result


def get_results(bench_v, bench, bench_js, df, model, gen_k):
    curr_df = bench if model == "original" else df[bench_v][model]
    total = {r: len(curr_df[curr_df["repository"] == r]) for r in REPOS}

    model_results, results_time = read_cached_model_results(bench_v, model, total, gen_k)

    stats = get_stats(model_results)
    times = get_model_time(model_results, results_time)
    metrics = get_metrics(model_results, bench_js)
    return stats, times, total, metrics


def progress_bar(stats, total, gen_k):
    processed_fns = sum(len(s["all"]) for r, s in stats.items() if r != "overall")
    total_fns = sum(total.values())
    progress = processed_fns / total_fns / gen_k
    st.progress(progress, text="Testing in progress..." if progress < 1 else "Testing finished.")


def text_repo(r, stats, total, times, gen_k):
    smiles = {
        "failed": "❌", "built": "⚠️", "passed": "✅", "timeout": "🕑"
    }
    result = {}
    for k in LAMBDAS:
        if k == "all":
            result.update({"all": [
                r,
                f"**{len(stats['all'])}** out of **{total}**{'x10' if gen_k == 10 else ''}",
                f"<ins>**{format_time(times['all'][0], short=True)}**</ins>",
                f"<ins>**{format_time(times['all'][1], short=True)}**</ins>",
            ]})
        else:
            result.update({k: [
                "",
                f"{smiles[k]} **{len(stats[k])}**",
                f"**{format_time(times[k][0], short=True)}**",
                f"**{format_time(times[k][1], short=True)}**",
            ]})
    return result


def text_content(stats, total, times, gen_k):
    result = {
        r: text_repo(r, stats[r], total[r], times[r], gen_k)
        for r in REPOS
    }

    # merge repos stats for overall
    times = {
        k: (
            sum(times[r][k][0] * len(stats[r][k]) for r in REPOS) / len_stat
            if (len_stat := sum(len(stats[r][k]) for r in REPOS)) > 0
            else -1,  # avg time
            sum(times[r][k][1] for r in REPOS),  # total time
        ) for k in LAMBDAS

    }
    total = sum(total.values())
    result.update(overall=text_repo("overall", stats["overall"], total, times, gen_k))
    return result


def results_header_line():
    unsafe_md("<br>")
    unsafe_md("##### **Results**")
    cols = COLUMNS_RESULTS[:-2] + [sum(COLUMNS_RESULTS[-2:])]
    repo, fns, avg_time, total_time, repo_wise = st.columns(cols)
    unsafe_md("repo", repo)
    unsafe_md("functions tested", fns)
    unsafe_md("avg. time", avg_time)
    unsafe_md("total time", total_time)
    return repo_wise.toggle("repo-wise", key="results-repo-wise", value=True)


def repo_result_line(text, stats, bench, model, r, k, on_show):
    repo, fns, avg_time, total_time, btn, show = st.columns(COLUMNS_RESULTS)

    unsafe_md(text[0], repo)
    unsafe_md(text[1], fns)
    unsafe_md(text[2], avg_time)
    unsafe_md(text[3], total_time)

    btn.button(
        "Rerun", key=f"rerun-{r}-{k}",
        on_click=rerun,
        args=(stats, bench, model, r)
    )
    show.button(
        "Show", key=f"show-{r}-{k}",
        on_click=on_show,
        args=(k, r, stats)
    )


def show_results(text, stats, s, model, on_show):
    repo_wise = results_header_line()
    results = REPOS if repo_wise else ["overall"]
    unsafe_md("<hr>")
    for r in results:
        for k in LAMBDAS:
            if k == "all" or text[r][k][1].split("**")[1] != "0":
                repo_result_line(text[r][k], stats[r][k], s.bench_v, model, r, k, on_show)
        unsafe_md("<hr>")


def metrics_header_line():
    unsafe_md("<br>")
    unsafe_md("##### **Metrics**")
    repo, pass_k, es, em, repo_wise = st.columns(COLUMNS_METRICS)
    unsafe_md("repo", repo)
    unsafe_md("pass@k", pass_k)
    unsafe_md("edit similarity", es)
    unsafe_md("exact match", em)
    return repo_wise.toggle("repo-wise", key="metrics-repo-wise", value=True)


def repo_metric_line(metrics, r):
    repo, pass_k, es, em, _ = st.columns(COLUMNS_METRICS)
    unsafe_md(r, repo)
    unsafe_md(metrics["pass_k"], pass_k)
    unsafe_md(metrics['es'], es)
    unsafe_md(f"{metrics['em']:.1f}%", em)


def show_metrics(metrics):
    repo_wise = metrics_header_line()
    cols = REPOS if repo_wise else ["overall"]
    unsafe_md("<hr>")
    for r in cols:
        repo_metric_line(metrics[r], r)
        unsafe_md("<hr>")


def show_test_progress(s, bench, bench_js, df):
    tp_popover = st.popover("Testing progress", use_container_width=True)
    with tp_popover:
        model = st.radio("Model to show results", [s.model, "Original"],
                         horizontal=True, label_visibility="collapsed")
        model = "original" if model == "Original" else model
        gen_k = 10 if model != "original" else 1

        stats, times, total, metrics = get_results(s.bench_v, bench, bench_js, df, model, gen_k)
        text = text_content(stats, total, times, gen_k)

        progress_bar(stats, total, gen_k)

        def on_show(type_, repo, fns):
            with show_container:
                unsafe_md("<br>")
                unsafe_md(f"##### Functions")
                unsafe_md(f"Showing **{type_}** from **{repo}**<br>")
                cols = st.columns([1, 1])
                n = len(fns) // len(cols) + (1 if len(fns) % len(cols) else 0)
                j = 0
                for i, c in enumerate(cols):
                    for x in fns[i * n: (i + 1) * n]:
                        j += 1
                        c.button(
                            f"&#8291;{j}. {x}", key=f"on_show_click-{x}",
                            on_click=on_show_click, args=(x, repo)
                        )

        show_metrics(metrics)
        show_results(text, stats, s, model, on_show)
        show_container = st.container()


def on_show_click(fn, repo):
    gen_i = "Original"
    if "-" in fn:
        fn, gen_i = fn.split("-")
    if "/" in fn:
        repo, fn = fn.split("/")
    st.session_state.repo = repo
    st.session_state.to_be_set = (fn, gen_i)


def on_show_fn(show_container):
    def on_show(type_, repo, fns):
        with show_container:
            unsafe_md("<br>")
            unsafe_md(f"##### Functions")
            unsafe_md(f"Showing **{type_}** from **{repo}**<br>")
            cols = st.columns([1, 1])
            n = len(fns) // len(cols) + (1 if len(fns) % len(cols) else 0)
            j = 0
            for i, c in enumerate(cols):
                for x in fns[i * n: (i + 1) * n]:
                    j += 1
                    c.button(
                        f"&#8291;{j}. {x}", key=f"on_show_click-{x}",
                        on_click=on_show_click, args=(x, repo)
                    )
    return on_show
