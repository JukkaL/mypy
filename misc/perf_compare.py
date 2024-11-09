"""Compare performance of mypyc-compiled mypy between one or more commits/branches.

Simple usage:

  python misc/perf_compare.py my-branch main ...

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
import threading
import time


def heading(s: str) -> None:
    print()
    print(f"=== {s} ===")
    print()


def build_mypy(target_dir: str) -> None:
    env = os.environ.copy()
    env["CC"] = "clang"
    env["MYPYC_OPT_LEVEL"] = "2"
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


def run_benchmark(compiled_dir: str, check_dir: str) -> float:
    cache_dir = os.path.join(compiled_dir, ".mypy_cache")
    if os.path.isdir(cache_dir):
        shutil.rmtree(cache_dir)
    env = os.environ.copy()
    env["PYTHONPATH"] = os.path.abspath(compiled_dir)
    abschk = os.path.abspath(check_dir)
    cmd = [
        sys.executable,
        "-m",
        "mypy",
        "--config-file",
        os.path.join(abschk, "mypy_self_check.ini"),
    ]
    cmd += glob.glob(os.path.join(abschk, "mypy/*.py"))
    cmd += glob.glob(os.path.join(abschk, "mypy/*/*.py"))
    t0 = time.time()
    # Ignore errors, since some commits being measured may generate additional errors.
    subprocess.run(cmd, cwd=compiled_dir, env=env)
    return time.time() - t0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("commit", nargs="+")
    args = parser.parse_args()
    commits = args.commit
    num_runs = 16

    if not (os.path.isdir(".git") and os.path.isdir("mypyc")):
        sys.exit("error: Run this the mypy repo root")

    build_threads = []
    target_dirs = []
    for i, commit in enumerate(commits):
        target_dir = f"mypy.{i}.tmpdir"
        target_dirs.append(target_dir)
        clone(target_dir, commit)
        t = threading.Thread(target=lambda: build_mypy(target_dir))
        t.start()
        build_threads.append(t)

    self_check_dir = "mypy.self.tmpdir"
    clone(self_check_dir, commits[0])

    heading("Compiling mypy")
    print("(This will take a while...)")

    for t in build_threads:
        t.join()

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
            tt = run_benchmark(target_dirs[i], self_check_dir)
            # Don't record the first warm-up run
            if n > 0:
                print(f"{commit}: t={tt:.3f}s")
                results.setdefault(commit, []).append(tt)

    print()
    heading("Results")
    first = -1.0
    for commit in commits:
        tt = statistics.mean(results[commit])
        if first < 0:
            delta = "0.0%"
            first = tt
        else:
            d = (tt / first) - 1
            delta = f"{d:+.1%}"
        print(f"{commit:<25} {tt:.3f}s ({delta})")

    shutil.rmtree(self_check_dir)
    for target_dir in target_dirs:
        shutil.rmtree(target_dir)


if __name__ == "__main__":
    main()
