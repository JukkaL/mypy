Tests
=====


Quick Start
-----------

To add a simple unit test for a new feature you developed, open or create a
`test-data/unit/check-*.test` file with a name that roughly relates to the
feature you added. If you added a new `check-*.test` file, it will be autodiscovered during unittests run.

Add the test in this format anywhere in the file:

    [case testNewSyntaxBasics]
    # flags: --python-version 3.10
    x: int
    x = 5
    y: int = 5

    a: str
    a = 5  # E: Incompatible types in assignment (expression has type "int", variable has type "str")
    b: str = 5  # E: Incompatible types in assignment (expression has type "int", variable has type "str")

    zzz: int
    zzz: str  # E: Name "zzz" already defined

- no code here is executed, just type checked
- optional `# flags: ` indicates which flags to use for this unit test
- `# E: abc...` indicates that this line should result in type check error
with text "abc..."
- note a space after `E:` and `flags:`
- `# E:12` adds column number to the expected error
- use `\` to escape the `#` character and indicate that the rest of the line is part of
the error message
- repeating `# E: ` several times in one line indicates multiple expected errors in one line
- `W: ...` and `N: ...` works exactly like `E: ...`, but report a warning and a note respectively
- lines that don't contain the above should cause no type check errors
- optional `[builtins fixtures/...]` tells the type checker to use
`builtins` stubs from the indicated file (see Fixtures section below)
- optional `[out]` is an alternative to the `# E: ` notation: it indicates that
any text after it contains the expected type checking error messages.
Usually, `# E: ` is preferred because it makes it easier to associate the
errors with the code generating them at a glance, and to change the code of
the test without having to change line numbers in `[out]`
- an empty `[out]` section has no effect
- to add tests for a feature that hasn't been implemented yet, append `-xfail`
  to the end of the test name
- to run just this test, use `pytest -n0 -k testNewSyntaxBasics`


Fixtures
--------

The unit tests use minimal stubs for builtins, so a lot of operations are not
possible. You should generally define any needed classes within the test case
instead of relying on builtins, though clearly this is not always an option
(see below for more about stubs in test cases). This way tests run much
faster and don't break if the stubs change. If your test crashes mysteriously
even though the code works when run manually, you should make sure you have
all the stubs you need for your test case, including built-in classes such as
`list` or `dict`, as these are not included by default.

Where the stubs for builtins come from for a given test:

- The builtins used by default in unit tests live in
  `test-data/unit/lib-stub`.

- Individual test cases can override the `builtins` stubs by using
  `[builtins fixtures/foo.pyi]`; this targets files in `test-data/unit/fixtures`.
  Feel free to modify existing files there or create new ones as you deem fit.

- Test cases can also use `[typing fixtures/typing-full.pyi]` to use a more
  complete stub for `typing` that contains the async types, among other things.

- Feel free to add additional stubs to that `fixtures` directory, but
  generally don't expand files in `lib-stub` without first discussing the
  addition with other mypy developers, as additions could slow down the test
  suite.

- Some tests choose to customize the standard library in a way that's local to the test:
  ```
  [case testFoo]
  ...
  [file builtins.py]
  class int:
    def next_fibonacci() -> int: pass
  ```
  Another possible syntax is:
  ```
  [fixture builtins.py]
  ```
  Whether you use `[file ...]` or `[fixture ...]` depends on whether you want
  the file to be part of the tested corpus (e.g. contribute to `[out]` section)
  or only support the test.

Running tests and linting
-------------------------

First install any additional dependencies needed for testing:

    python3 -m pip install -U -r test-requirements.txt

Configure `pre-commit` to run the linters automatically when you commit:

    pre-commit install

The unit test suites are driven by the `pytest` framework. To run all mypy tests,
run `pytest` in the mypy repository:

    pytest -q mypy

This will run all tests, including integration and regression tests,
and will verify that all stubs are valid. This may take several
minutes to run, so you don't want to use this all the time while doing
development. (The `-q` option activates less verbose output that looks
better when running tests using many CPU cores.)

Test suites for individual components are in the files `mypy/test/test*.py`.

Note that some tests will be disabled for older python versions.

If you work on mypyc, you will want to also run mypyc tests:

    pytest -q mypyc

You can run tests from a specific module directly, a specific suite within a
module, or a test in a suite (even if it's data-driven):

    pytest -q mypy/test/testdiff.py

    pytest -q mypy/test/testsemanal.py::SemAnalTypeInfoSuite

    pytest -n0 mypy/test/testargs.py::ArgSuite::test_coherence

    pytest -n0 mypy/test/testcheck.py::TypeCheckSuite::testCallingVariableWithFunctionType

To control which tests are run and how, you can use the `-k` switch:

    pytest -q -k "MethodCall"

You can also run the type checker for manual testing without
installing it by setting up the Python module search path suitably:

    export PYTHONPATH=$PWD
    python3 -m mypy PROGRAM.py

You will have to manually install the `typing` module if you're running Python
3.4 or earlier.

You can also execute mypy as a module

    python3 -m mypy PROGRAM.py

You can check a module or string instead of a file:

    python3 -m mypy PROGRAM.py
    python3 -m mypy -m MODULE
    python3 -m mypy -c 'import MODULE'

To run mypy on itself:

    python3 -m mypy --config-file mypy_self_check.ini -p mypy

To run the linter (this commands just wraps `pre-commit`, so you can also
invoke it directly like `pre-commit run -a`, and this will also run when you
`git commit` if enabled):

    python3 runtests.py lint

You can also run all of the above tests using `runtests.py` (this includes
type checking mypy and linting):

    python3 runtests.py

By default, this runs everything except some mypyc tests. You can give it
arguments to control what gets run, such as `self` to run mypy on itself:

    python3 runtests.py self

Run `python3 runtests.py mypyc-extra` to run mypyc tests that are not
enabled by default. This is typically only needed if you work on mypyc.

Many test suites store test case descriptions in text files
(`test-data/unit/*.test`). The module `mypy.test.data` parses these
descriptions.

Python evaluation test cases are a little different from unit tests
(`mypy/test/testpythoneval.py`, `test-data/unit/pythoneval.test`). These
type check programs and run them. Unlike the unit tests, these use the
full builtins and library stubs instead of minimal ones. Run them using
`pytest -k testpythoneval`.

`pytest` determines the number of processes to use. The default (set in
`./pytest.ini`) is the number of logical cores; this can be overridden using
`-n` option. To run a single process, use `pytest -n0`.

Note that running more processes than logical cores is likely to
significantly decrease performance.

To run tests with coverage:

    python3 -m pytest --cov mypy --cov-config setup.cfg  --cov-report=term-missing:skip-covered --cov-report=html


Debugging
---------

You can use interactive debuggers like `pdb` to debug failing tests. You
need to pass the `-n0` option to disable parallelization:

    pytest -n0 --pdb -k MethodCall

You can also write `import pdb; pdb.set_trace()` in code to enter the
debugger.

The `--mypy-verbose` flag can be used to enable additional debug output from
most tests (as if `--verbose` had been passed to mypy):

    pytest -n0 --mypy-verbose -k MethodCall

Coverage reports
----------------

There is an experimental feature to generate coverage reports.  To use
this feature, you need to `pip install -U lxml`.  This is an extension
module and requires various library headers to install; on a
Debian-derived system the command
  `apt-get install python3-dev libxml2-dev libxslt1-dev`
may provide the necessary dependencies.

To use the feature, pass e.g. `--txt-report "$(mktemp -d)"`.
