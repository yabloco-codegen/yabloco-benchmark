import json
import os.path
import subprocess
import sys

from config import RESULTS_PATH


def main():
    if len(sys.argv) < 2:
        raise ValueError("Container to kill is not identified, pass unique index in the following format: "
                         "\"{bench}/{model}/{repo}/{fn}-{i}\"")
    ind = sys.argv[1]

    if os.path.isfile(f"{RESULTS_PATH}/{ind}-res.json"):
        return

    cmd = f"docker stop {ind.replace('/', '_')}"
    subprocess.run(cmd, shell=True, text=True)

    with open(f"{RESULTS_PATH}/{ind}.json", encoding="utf-8") as f:
        config = json.load(f)

    config.update({
        "built": False,
        "passed": False,
        "error": "Timeout",
    })
    with open(f"{RESULTS_PATH}/{ind}-res.json", "w", encoding="utf-8") as f:
        json.dump(config, f)


if __name__ == "__main__":
    main()
