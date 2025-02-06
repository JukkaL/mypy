#!/usr/bin/env python3

from __future__ import annotations

import subprocess
from subprocess import Popen
from sys import argv, executable, exit

# Slow test suites
CMDLINE = "PythonCmdline"
PEP561 = "PEP561Suite"
EVALUATION = "PythonEvaluation"
DAEMON = "testdaemon"
STUBGEN_CMD = "StubgenCmdLine"
STUBGEN_PY = "StubgenPythonSuite"
MYPYC_RUN = "TestRun"
MYPYC_RUN_MULTI = "TestRunMultiFile"
MYPYC_EXTERNAL = "TestExternal"
MYPYC_COMMAND_LINE = "TestCommandLine"
MYPYC_SEPARATE = "TestRunSeparate"
MYPYC_MULTIMODULE = "multimodule"  # Subset of mypyc run tests that are slow
ERROR_STREAM = "ErrorStreamSuite"


ALL_NON_FAST = [
    CMDLINE,
    PEP561,
    EVALUATION,
    DAEMON,
    STUBGEN_CMD,
    STUBGEN_PY,
    MYPYC_RUN,
    MYPYC_RUN_MULTI,
    MYPYC_EXTERNAL,
    MYPYC_COMMAND_LINE,
    MYPYC_SEPARATE,
    ERROR_STREAM,
]


# This must be enabled by explicitly including 'pytest-extra' on the command line
PYTEST_OPT_IN = [PEP561]


# These must be enabled by explicitly including 'mypyc-extra' on the command line.
MYPYC_OPT_IN = [MYPYC_RUN, MYPYC_RUN_MULTI, MYPYC_SEPARATE]

# These mypyc test filters cover most slow test cases
MYPYC_SLOW = [MYPYC_RUN_MULTI, MYPYC_COMMAND_LINE, MYPYC_SEPARATE, MYPYC_MULTIMODULE]


# We split the pytest run into three parts to improve test
# parallelization. Each run should have tests that each take a roughly similar
# time to run.
cmds = {
    # Self type check
    "self": [
        executable,
        "-m",
        "mypy",
        "--config-file",
        "mypy_self_check.ini",
        "-p",
        "mypy",
        "-p",
        "mypyc",
    ],
    # Type check setup.py as well
    "self-packaging": [
        executable,
        "-m",
        "mypy",
        "--config-file",
        "mypy_self_check.ini",
        "setup.py",
    ],
    # Lint
    "lint": ["pre-commit", "run", "--all-files"],
    # Fast test cases only (this is the bulk of the test suite)
    "pytest-fast": ["pytest", "-q", "-k", f"not ({' or '.join(ALL_NON_FAST)})"],
    # Test cases that invoke mypy (with small inputs)
    "pytest-cmdline": [
        "pytest",
        "-q",
        "-k",
        " or ".join([CMDLINE, EVALUATION, STUBGEN_CMD, STUBGEN_PY]),
    ],
    # Test cases that may take seconds to run each
    "pytest-slow": [
        "pytest",
        "-q",
        "-k",
        " or ".join([DAEMON, MYPYC_EXTERNAL, MYPYC_COMMAND_LINE, ERROR_STREAM]),
    ],
    "mypyc-fast": ["pytest", "-q", "mypyc", "-k", f"not ({' or '.join(MYPYC_SLOW)})"],
    # Test cases that might take minutes to run
    "pytest-extra": ["pytest", "-q", "-k", " or ".join(PYTEST_OPT_IN)],
    # Mypyc tests that aren't run by default, since they are slow and rarely
    # fail for commits that don't touch mypyc
    "mypyc-extra": ["pytest", "-q", "-k", " or ".join(MYPYC_OPT_IN)],
}

# Stop run immediately if these commands fail
FAST_FAIL = ["self", "lint"]

EXTRA_COMMANDS = ("pytest-extra", "mypyc-fast", "mypyc-extra")
DEFAULT_COMMANDS = [cmd for cmd in cmds if cmd not in EXTRA_COMMANDS]

assert all(cmd in cmds for cmd in FAST_FAIL)


def run_cmd(name: str) -> int:
    status = 0
    cmd = cmds[name]
    print(f"run {name}: {cmd}")
    proc = subprocess.run(cmd, stderr=subprocess.STDOUT)
    if proc.returncode:
        print("\nFAILED: %s" % name)
        status = proc.returncode
        if name in FAST_FAIL:
            exit(status)
    return status


def start_background_cmd(name: str) -> Popen:
    cmd = cmds[name]
    proc = subprocess.Popen(cmd, stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
    return proc


def wait_background_cmd(name: str, proc: Popen) -> int:
    output = proc.communicate()[0]
    status = proc.returncode
    print(f"run {name}: {cmds[name]}")
    if status:
        print(output.decode().rstrip())
        print("\nFAILED:", name)
        if name in FAST_FAIL:
            exit(status)
    return status


def main() -> None:
    prog, *args = argv

    if not set(args).issubset(cmds):
        print("usage:", prog, " ".join(f"[{k}]" for k in cmds))
        print()
        print(
            "Run the given tests. If given no arguments, run everything except"
            + " pytest-extra and mypyc-extra."
        )
        exit(1)

    if not args:
        args = DEFAULT_COMMANDS.copy()

    status = 0

    if "self" in args and "lint" in args:
        # Perform lint and self check in parallel as it's faster.
        proc = start_background_cmd("lint")
        cmd_status = run_cmd("self")
        if cmd_status:
            status = cmd_status
        cmd_status = wait_background_cmd("lint", proc)
        if cmd_status:
            status = cmd_status
        args = [arg for arg in args if arg not in ("self", "lint")]

    for arg in args:
        cmd_status = run_cmd(arg)
        if cmd_status:
            status = cmd_status

    exit(status)


if __name__ == "__main__":
    main()
