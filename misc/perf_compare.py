"""Compare performance of mypyc-compiled mypy between one or more commits/branches.

Simple usage:

  python misc/perf_compare.py master my-branch ...

What this does:

 * Create a temp clone of the mypy repo for each target commit to measure
 * Checkout a target commit in each of the clones
 * Compile mypyc in each of the clones *in parallel*
 * Create another temp clone of the mypy repo as the code to check
 * Self check with each of the compiled mypys N times
 * Report the average runtimes and relative performance
 * Remove the temp clones
"""

from __future__ import annotations

import argparse
import glob
import os
import random
import shutil
import statistics
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed


def heading(s: str) -> None:
    print()
    print(f"=== {s} ===")
    print()


def build_mypy(target_dir: str) -> None:
    env = os.environ.copy()
    env["CC"] = "clang"
    env["MYPYC_OPT_LEVEL"] = "2"
    env["PYTHONHASHSEED"] = "1"
    cmd = [sys.executable, "setup.py", "--use-mypyc", "build_ext", "--inplace"]
    subprocess.run(cmd, env=env, check=True, cwd=target_dir)


def clone(target_dir: str, commit: str | None) -> None:
    heading(f"Cloning mypy to {target_dir}")
    repo_dir = os.getcwd()
    if os.path.isdir(target_dir):
        print(f"{target_dir} exists: deleting")
        shutil.rmtree(target_dir)
    subprocess.run(["git", "clone", repo_dir, target_dir], check=True)
    if commit:
        subprocess.run(["git", "checkout", commit], check=True, cwd=target_dir)


def edit_python_file(fnam: str) -> None:
    with open(fnam) as f:
        data = f.read()
    data += "\n#"
    with open(fnam, "w") as f:
        f.write(data)


def run_benchmark(
    compiled_dir: str, check_dir: str, *, incremental: bool, code: str | None
) -> float:
    cache_dir = os.path.join(compiled_dir, ".mypy_cache")
    if os.path.isdir(cache_dir) and not incremental:
        shutil.rmtree(cache_dir)
    env = os.environ.copy()
    env["PYTHONPATH"] = os.path.abspath(compiled_dir)
    env["PYTHONHASHSEED"] = "1"
    abschk = os.path.abspath(check_dir)
    cmd = [sys.executable, "-m", "mypy"]
    if code:
        cmd += ["-c", code]
    else:
        cmd += ["--config-file", os.path.join(abschk, "mypy_self_check.ini")]
        cmd += glob.glob(os.path.join(abschk, "mypy/*.py"))
        cmd += glob.glob(os.path.join(abschk, "mypy/*/*.py"))
        if incremental:
            # Update a few files to force non-trivial incremental run
            edit_python_file(os.path.join(abschk, "mypy/__main__.py"))
            edit_python_file(os.path.join(abschk, "mypy/test/testcheck.py"))
    t0 = time.time()
    # Ignore errors, since some commits being measured may generate additional errors.
    subprocess.run(cmd, cwd=compiled_dir, env=env)
    return time.time() - t0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--incremental",
        default=False,
        action="store_true",
        help="measure incremental run (fully cached)",
    )
    parser.add_argument(
        "--num-runs",
        metavar="N",
        default=15,
        type=int,
        help="set number of measurements to perform (default=15)",
    )
    parser.add_argument(
        "-j",
        metavar="N",
        default=8,
        type=int,
        help="set maximum number of parallel builds (default=8)",
    )
    parser.add_argument(
        "-c",
        metavar="CODE",
        default=None,
        type=str,
        help="measure time to type check Python code fragment instead of mypy self-check",
    )
    parser.add_argument("commit", nargs="+", help="git revision to measure (e.g. branch name)")
    args = parser.parse_args()
    incremental: bool = args.incremental
    commits = args.commit
    num_runs: int = args.num_runs + 1
    max_workers: int = args.j
    code: str | None = args.c

    if not (os.path.isdir(".git") and os.path.isdir("mypyc")):
        sys.exit("error: Run this the mypy repo root")

    target_dirs = []
    for i, commit in enumerate(commits):
        target_dir = f"mypy.{i}.tmpdir"
        target_dirs.append(target_dir)
        clone(target_dir, commit)

    self_check_dir = "mypy.self.tmpdir"
    clone(self_check_dir, commits[0])

    heading("Compiling mypy")
    print("(This will take a while...)")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(build_mypy, target_dir) for target_dir in target_dirs]
        for future in as_completed(futures):
            future.result()

    print(f"Finished compiling mypy ({len(commits)} builds)")

    heading("Performing measurements")

    results: dict[str, list[float]] = {}
    for n in range(num_runs):
        if n == 0:
            print("Warmup...")
        else:
            print(f"Run {n}/{num_runs - 1}...")
        items = list(enumerate(commits))
        random.shuffle(items)
        for i, commit in items:
            tt = run_benchmark(target_dirs[i], self_check_dir, incremental=incremental, code=code)
            # Don't record the first warm-up run
            if n > 0:
                print(f"{commit}: t={tt:.3f}s")
                results.setdefault(commit, []).append(tt)

    print()
    heading("Results")
    first = -1.0
    for commit in commits:
        tt = statistics.mean(results[commit])
        s = statistics.stdev(results[commit])
        if first < 0:
            delta = "0.0%"
            first = tt
        else:
            d = (tt / first) - 1
            delta = f"{d:+.1%}"
        print(f"{commit:<25} {tt:.3f}s ({delta}) | stdev {s}")

    shutil.rmtree(self_check_dir)
    for target_dir in target_dirs:
        shutil.rmtree(target_dir)


if __name__ == "__main__":
    main()
