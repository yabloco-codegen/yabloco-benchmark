import time

from fuzzywuzzy import fuzz


def get_ind(bench, model, repo, fn, gen_i=None):
    """ {bench}/{model}/{repo}/{fn_id}-{i} """

    if gen_i == "Original":
        gen_i = None

    ind = f"{bench}/{model}/{repo}/{fn}"
    if gen_i is not None:
        ind += f"-{gen_i}"
    return ind


def edit_similarity_score(generated_code, ground_truth):
    edit_sim = fuzz.ratio(ground_truth, generated_code)
    return round(edit_sim, 5)


def parse_generation(raw_text, fn=None):
    # Выделение кода - скорее всего он выделен специальными символами
    if not isinstance(raw_text, str):
        return ""
    sections = raw_text.split('```')
    generated_code = "-"
    if len(sections) >= 3:
        generated_code = sections[1]
    if len(sections) == 1:
        generated_code = sections[0]

    remove_prefix = ["cpp", "c++", "c", "++"]
    for pref in remove_prefix:
        generated_code = generated_code.removeprefix(pref)
    generated_lines = generated_code.split('\n')

    # Убираем мусор из начала функции
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


def format_time(seconds, short=False):
    if seconds == -1:
        return "NaN"

    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    result = (f"{h}h " if h else "") + (f"{m}min " if m else "") + f"{s:.1f}sec"
    if short:
        result = " ".join(result.split()[:2])
        if "." in result and len(result.split(".")[0]) > 1:
            result = result.split(".")[0] + "s"
        return result.replace("min", "m").replace("sec", "s")

    return result


def get_ttl_hash(seconds=300):
    """Return the same value withing `seconds` time period"""
    return round(time.time() / seconds)
