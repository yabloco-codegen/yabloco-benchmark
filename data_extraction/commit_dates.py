import json
import os
import sys
from datetime import datetime
from glob import glob

import git
from tqdm import tqdm


def parse_subset(project_path, partition_n, partition):
    # json: for each cpp file, for each line: date

    repo = git.Repo(project_path)
    result = {}

    paths = [
        p for p in
        glob(project_path + "/**/*.cpp", recursive=True) +
        glob(project_path + "/**/*.c", recursive=True) +
        glob(project_path + "/**/*.h", recursive=True)
    ]

    n = len(paths) // partition_n + 1
    paths = paths[partition * n:(partition + 1) * n]
    paths = [p for p in paths if os.path.isfile(p)]

    for file in tqdm(paths, total=len(paths)):
        try:
            lines = {}
            blame = repo.blame_incremental("HEAD", file.replace(project_path, "", 1)[1:])

            for b in blame:
                d = datetime.fromtimestamp(b.commit.committed_date).strftime('%d.%m.%Y')
                for i in b.linenos:
                    lines[i] = d

            lines = {k: v for k, v in sorted(lines.items())}
            result[file] = lines
        except Exception:
            print(file)

    return result


def main():
    project_path = sys.argv[1]
    output_path = sys.argv[2]

    if len(sys.argv) == 3:
        result = parse_subset(project_path, 1, 0)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f)

    elif len(sys.argv) == 4:
        partition_n = int(sys.argv[3])
        result = {}
        for partition in range(partition_n):
            with open(f"{partition}_{output_path}", "r", encoding="utf-8") as f:
                result.update(json.load(f))

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f)

    elif len(sys.argv) == 5:
        partition_n = int(sys.argv[3])
        partition = int(sys.argv[4])
        result = parse_subset(project_path, partition_n, partition)

        with open(f"{partition}_{output_path}", "w", encoding="utf-8") as f:
            json.dump(result, f)


if __name__ == "__main__":
    main()
