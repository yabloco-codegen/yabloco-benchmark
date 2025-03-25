import json
import os
import subprocess
import sys


def run_single_example(row, generated_code, repo, results_path, identifier, prefix):
    # write config file
    path = f"{results_path}/{identifier}.json"
    config = {
        "row": {
            "file": row["file"],
            "pos": int(row["pos"]),
            "code_length": int(row["code_length"]),
        },
        "generated_code": generated_code,
        "repo": repo,
    }

    folder = path.rsplit("/", 1)[0]
    if not os.path.isdir(folder):
        os.makedirs(folder)

    with open(path, "w") as f:
        json.dump(config, f)

    # run docker
    results_path = os.path.abspath(results_path)
    cmd = f"docker run -d --rm -v {results_path}:/results --name {prefix}{identifier.replace('/', '_')} " \
          f"{prefix}{repo} python3 /results/run_single_example.py {identifier}"
    try:
        subprocess.run(cmd, shell=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except Exception as e:
        print(e)
        return False, False, str(e)
    return


def run(build_cmd, test_cmd):
    has_built = True
    has_passed = True
    error = ""

    try:
        child = subprocess.run(build_cmd, shell=True, text=True,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except Exception as e:
        has_built = False
        has_passed = False
        error = str(e)
        print(e)
        return has_built, has_passed, error

    if child.returncode != 0:
        has_built = False
        has_passed = False
        error = child.stderr
        print(child.stdout)
        print(child.stderr)
        return has_built, has_passed, error

    try:
        child = subprocess.run(test_cmd, shell=True, text=True,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except Exception as e:
        has_passed = False
        error = str(e)
        print(e)
        return has_built, has_passed, error

    if child.returncode != 0:
        has_passed = False
        error = child.stderr
        print(child.stdout)
        print(child.stderr)

    return has_built, has_passed, error


def get_new_content(lines, row, generated_code):
    code_start = "".join(lines[:row['pos'] - 1])
    code_end = "".join(lines[row['pos'] + row['code_length']:])
    new_content = code_start + "\n" + generated_code + "\n" + code_end
    return new_content


def replace_code(row, generated_code):
    file_path = row['file']
    with open(f"/{file_path}", encoding="utf-8") as f:
        lines = f.readlines()

    new_content = get_new_content(lines, row, generated_code)
    with open(f"/{file_path}", 'w', encoding="utf-8") as f:
        f.write(new_content)


def process_fn(row, generated_code, build_cmd, test_cmd):
    if generated_code == "-" or generated_code.strip() == "":
        has_built = False
        has_passed = False
        error = "Bad code generated"
    else:
        replace_code(row, generated_code)
        has_built, has_passed, error = run(build_cmd, test_cmd)

    return has_built, has_passed, error


def process_fn_openssl(row, generated_code):
    return process_fn(row, generated_code,
                      f'./Configure --prefix=/openssl --openssldir=/openssl',
                      f'make test')


def process_fn_llvm(row, generated_code):
    return process_fn(row, generated_code,
                      f'cmake -S llvm -DCMAKE_BUILD_TYPE="Release" -DLLVM_ENABLE_ASSERTIONS=On',
                      f'make check-llvm-unit')


def process_fn_bullet3(row, generated_code):
    return process_fn(row, generated_code,
                      f'./build_cmake_pybullet_double.sh',
                      f'./build_cmake/test/InverseDynamics/Test_BulletInverseDynamics && \
                        ./build_cmake/test/InverseDynamics/Test_BulletInverseForwardDynamics && \
                        ./build_cmake/test/InverseDynamics/Test_BulletInverseDynamicsJacobian && \
                        ./build_cmake/test/BulletDynamics/Test_btKinematicCharacterController && \
                        ./build_cmake/test/BulletDynamics/pendulum/Test_BulletDynamics && \
                        ./build_cmake/test/SharedMemory/Test_PhysicsClientServer && \
                        ./build_cmake/test/collision/Test_Collision')


def process_fn_redis(row, generated_code):
    return process_fn(row, generated_code,
                      f'make',
                      f'make test')


def main():
    if len(sys.argv) < 2:
        raise ValueError("Function to test is not identified, pass unique index in the following format: "
                         "\"{bench}/{model}/{repo}/{fn}-{i}\"")
    identifier = sys.argv[1]

    with open(f"/results/{identifier}.json", encoding="utf-8") as f:
        config = json.load(f)

    row = config["row"]
    generated_code = config["generated_code"]
    repo = config["repo"]
    fns = {
        "bullet3": process_fn_bullet3,
        "openssl": process_fn_openssl,
        "redis": process_fn_redis,
        "llvm": process_fn_llvm,
    }
    has_built, has_passed, error = fns[repo](row, generated_code)

    if len(error) > 1000:
        error = f"{error[:400]}\n...skipping {len(error) - 800} symbols...\n{error[:-400]}"

    config.update({
        "built": has_built,
        "passed": has_passed,
        "error": error,
    })
    with open(f"/results/{identifier}-res.json", "w", encoding="utf-8") as f:
        json.dump(config, f)


if __name__ == "__main__":
    main()
