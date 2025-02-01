# Contributing to Mypy

Welcome!  Mypy is a community project that aims to work for a wide
range of Python users and Python codebases.  If you're trying mypy on
your Python code, your experience and what you can contribute are
important to the project's success.

## Code of Conduct

Everyone participating in the Mypy community, and in particular in our
issue tracker, pull requests, and chat, is expected to treat
other people with respect and more generally to follow the guidelines
articulated in the [Python Community Code of Conduct](https://www.python.org/psf/codeofconduct/).

## Getting started with development

### Setup

#### (1) Fork the mypy repository

Within GitHub, navigate to <https://github.com/python/mypy> and fork the repository.

#### (2) Clone the mypy repository and enter into it

```bash
git clone https://github.com/<your_username>/mypy.git
cd mypy
```

If you use the following command to clone instead:
```bash
git clone git@github.com:<your_username>/mypy.git
```
then make sure to connect to GitHub first: [Connecting to github with ssh](https://docs.github.com/en/authentication/connecting-to-github-with-ssh)

#### (3) Create then activate a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

```bash
# For Windows use
python -m venv venv
. venv/Scripts/activate

# For more details, see https://docs.python.org/3/library/venv.html#creating-virtual-environments
```

#### (4) Install the test requirements and the project

```bash
python -m pip install -r test-requirements.txt
python -m pip install -e .
hash -r  # This resets shell PATH cache, not necessary on Windows
```

> **Note**
> You'll need Python 3.9 or higher to install all requirements listed in
> test-requirements.txt

### Running tests

Running the full test suite can take a while, and usually isn't necessary when
preparing a PR. Once you file a PR, the full test suite will run on GitHub.
You'll then be able to see any test failures, and make any necessary changes to
your PR.

However, if you wish to do so, you can run the full test suite
like this:

```bash
python runtests.py
```

Some useful commands for running specific tests include:

```bash
# Use mypy to check mypy's own code
python runtests.py self
# or equivalently:
python -m mypy --config-file mypy_self_check.ini -p mypy

# Run a single test from the test suite
pytest -n0 -k 'test_name'

# Run all test cases in the "test-data/unit/check-dataclasses.test" file
pytest mypy/test/testcheck.py::TypeCheckSuite::check-dataclasses.test

# Run the formatters and linters
python runtests.py lint
```

For an in-depth guide on running and writing tests,
see [the README in the test-data directory](test-data/unit/README.md).

#### Using `tox`

You can also use [`tox`](https://tox.wiki/en/latest/) to run tests and other commands.
`tox` handles setting up test environments for you.

```bash
# Run tests
tox run -e py

# Run tests using some specific Python version
tox run -e py311

# Run a specific command
tox run -e lint

# Run a single test from the test suite
tox run -e py -- -n0 -k 'test_name'

# Run all test cases in the "test-data/unit/check-dataclasses.test" file using
# Python 3.11 specifically
tox run -e py311 -- mypy/test/testcheck.py::TypeCheckSuite::check-dataclasses.test

# Set up a development environment with all the project libraries and run a command
tox -e dev -- mypy --verbose test_case.py
tox -e dev --override testenv:dev.allowlist_externals+=env -- env  # inspect the environment
```

If you don't already have `tox` installed, you can use a virtual environment as
described above to install `tox` via `pip` (e.g., ``python -m pip install tox``).

## First time contributors

If you're looking for things to help with, browse our [issue tracker](https://github.com/python/mypy/issues)!

In particular, look for:

- [good first issues](https://github.com/python/mypy/labels/good-first-issue)
- [good second issues](https://github.com/python/mypy/labels/good-second-issue)
- [documentation issues](https://github.com/python/mypy/labels/documentation)

You do not need to ask for permission to work on any of these issues.
Just fix the issue yourself, [try to add a unit test](#running-tests) and
[open a pull request](#submitting-changes).

To get help fixing a specific issue, it's often best to comment on the issue
itself. You're much more likely to get help if you provide details about what
you've tried and where you've looked (maintainers tend to help those who help
themselves). [gitter](https://gitter.im/python/typing) can also be a good place
to ask for help.

Interactive debuggers like `pdb` and `ipdb` are really useful for getting
started with the mypy codebase. This is a
[useful tutorial](https://realpython.com/python-debugging-pdb/).

It's also extremely easy to get started contributing to our sister project
[typeshed](https://github.com/python/typeshed/issues) that provides type stubs
for libraries. This is a great way to become familiar with type syntax.

## Submitting changes

Even more excellent than a good bug report is a fix for a bug, or the
implementation of a much-needed new feature. We'd love to have
your contributions.

We use the usual GitHub pull-request flow, which may be familiar to
you if you've contributed to other projects on GitHub.  For the mechanics,
see [our git and GitHub workflow help page](https://github.com/python/mypy/wiki/Using-Git-And-GitHub),
or [GitHub's own documentation](https://help.github.com/articles/using-pull-requests/).

Anyone interested in Mypy may review your code.  One of the Mypy core
developers will merge your pull request when they think it's ready.

If your change will be a significant amount of work
to write, we highly recommend starting by opening an issue laying out
what you want to do.  That lets a conversation happen early in case
other contributors disagree with what you'd like to do or have ideas
that will help you do it.

The best pull requests are focused, clearly describe what they're for
and why they're correct, and contain tests for whatever changes they
make to the code's behavior.  As a bonus these are easiest for someone
to review, which helps your pull request get merged quickly!  Standard
advice about good pull requests for open-source projects applies; we
have [our own writeup](https://github.com/python/mypy/wiki/Good-Pull-Request)
of this advice.

Also, do not squash your commits after you have submitted a pull request, as this
erases context during review. We will squash commits when the pull request is merged.

You may also find other pages in the
[Mypy developer guide](https://github.com/python/mypy/wiki/Developer-Guides)
helpful in developing your change.

## Core developer guidelines

Core developers should follow these rules when processing pull requests:

- Always wait for tests to pass before merging PRs.
- Use "[Squash and merge](https://github.com/blog/2141-squash-your-commits)"
  to merge PRs.
- Delete branches for merged PRs (by core devs pushing to the main repo).
- Edit the final commit message before merging to conform to the following
  style (we wish to have a clean `git log` output):
  - When merging a multi-commit PR make sure that the commit message doesn't
    contain the local history from the committer and the review history from
    the PR. Edit the message to only describe the end state of the PR.
  - Make sure there is a *single* newline at the end of the commit message.
    This way there is a single empty line between commits in `git log`
    output.
  - Split lines as needed so that the maximum line length of the commit
    message is under 80 characters, including the subject line.
  - Capitalize the subject and each paragraph.
  - Make sure that the subject of the commit message has no trailing dot.
  - Use the imperative mood in the subject line (e.g. "Fix typo in README").
  - If the PR fixes an issue, make sure something like "Fixes #xxx." occurs
    in the body of the message (not in the subject).
  - Use Markdown for formatting.
