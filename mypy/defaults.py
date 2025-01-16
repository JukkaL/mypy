from __future__ import annotations

import os
from typing import Final

# Earliest fully supported Python 3.x version. Used as the default Python
# version in tests. Mypy wheels should be built starting with this version,
# and CI tests should be run on this version (and later versions).
PYTHON3_VERSION: Final = (3, 9)

# Earliest Python 3.x version supported via --python-version 3.x. To run
# mypy, at least version PYTHON3_VERSION is needed.
PYTHON3_VERSION_MIN: Final = (3, 8)  # Keep in sync with typeshed's python support


def find_pyproject() -> str:
    """Search for file pyproject.toml in the parent directories recursively.

    It resolves symlinks, so if there is any symlink up in the tree, it does not respect them

    If the file is not found until the root of FS or repository, PYPROJECT_FILE is used
    """

    def is_root(current_dir: str) -> bool:
        parent = os.path.join(current_dir, os.path.pardir)
        return os.path.samefile(current_dir, parent) or any(
            os.path.isdir(os.path.join(current_dir, cvs_root)) for cvs_root in (".git", ".hg")
        )

    # Preserve the original behavior, returning PYPROJECT_FILE if exists
    if os.path.isfile(PYPROJECT_FILE) or is_root(os.path.curdir):
        return PYPROJECT_FILE

    # And iterate over the tree
    current_dir = os.path.pardir
    while not is_root(current_dir):
        config_file = os.path.join(current_dir, PYPROJECT_FILE)
        if os.path.isfile(config_file):
            return config_file
        parent = os.path.join(current_dir, os.path.pardir)
        current_dir = parent

    return PYPROJECT_FILE


CACHE_DIR: Final = ".mypy_cache"
CONFIG_FILE: Final = ["mypy.ini", ".mypy.ini"]
PYPROJECT_FILE: Final = "pyproject.toml"
PYPROJECT_CONFIG_FILES: Final = [find_pyproject()]
SHARED_CONFIG_FILES: Final = ["setup.cfg"]
USER_CONFIG_FILES: Final = ["~/.config/mypy/config", "~/.mypy.ini"]
if os.environ.get("XDG_CONFIG_HOME"):
    USER_CONFIG_FILES.insert(0, os.path.join(os.environ["XDG_CONFIG_HOME"], "mypy/config"))

CONFIG_FILES: Final = (
    CONFIG_FILE + PYPROJECT_CONFIG_FILES + SHARED_CONFIG_FILES + USER_CONFIG_FILES
)

# This must include all reporters defined in mypy.report. This is defined here
# to make reporter names available without importing mypy.report -- this speeds
# up startup.
REPORTER_NAMES: Final = [
    "linecount",
    "any-exprs",
    "linecoverage",
    "memory-xml",
    "cobertura-xml",
    "xml",
    "xslt-html",
    "xslt-txt",
    "html",
    "txt",
    "lineprecision",
]

# Threshold after which we sometimes filter out most errors to avoid very
# verbose output. The default is to show all errors.
MANY_ERRORS_THRESHOLD: Final = -1
