"""Interface for accessing the file system with automatic caching.

The idea is to cache the results of any file system state reads during
a single transaction. This has two main benefits:

* This avoids redundant syscalls, as we won't perform the same OS
  operations multiple times.

* This makes it easier to reason about concurrent FS updates, as different
  operations targeting the same paths can't report different state during
  a transaction.

Note that this only deals with reading state, not writing.

Properties maintained by the API:

* The contents of the file are always from the same or later time compared
  to the reported mtime of the file, even if mtime is queried after reading
  a file.

* Repeating an operation produces the same result as the first one during
  a transaction.

* Call flush() to start a new transaction (flush the caches).

The API is a bit limited. It's easy to add new cached operations, however.
You should perform all file system reads through the API to actually take
advantage of the benefits.
"""

import hashlib
import os
import stat
from typing import Dict, List, Optional, Set, Tuple
from mypy.util import read_with_python_encoding


class FileSystemMetaCache:
    def __init__(self, package_root: Optional[List[str]] = None) -> None:
        if package_root is None:
            package_root = []
        self.package_root = package_root
        self.flush()

    def flush(self) -> None:
        """Start another transaction and empty all caches."""
        self.stat_cache = {}  # type: Dict[str, os.stat_result]
        self.stat_error_cache = {}  # type: Dict[str, OSError]
        self.listdir_cache = {}  # type: Dict[str, List[str]]
        self.listdir_error_cache = {}  # type: Dict[str, OSError]
        self.isfile_case_cache = {}  # type: Dict[str, bool]
        self.fake_package_cache = set()  # type: Set[str]
        self.cwd = os.getcwd()

    def stat(self, path: str) -> os.stat_result:
        if path in self.stat_cache:
            return self.stat_cache[path]
        if path in self.stat_error_cache:
            raise copy_os_error(self.stat_error_cache[path])
        try:
            st = os.stat(path)
        except OSError as err:
            if isinstance(err, OSError) and self.init_under_package_root(path):
                try:
                    return self._fake_init(path)
                except OSError:
                    pass
            # Take a copy to get rid of associated traceback and frame objects.
            # Just assigning to __traceback__ doesn't free them.
            self.stat_error_cache[path] = copy_os_error(err)
            raise err
        self.stat_cache[path] = st
        return st

    def init_under_package_root(self, path: str) -> bool:
        if not self.package_root:
            return False
        dirname, basename = os.path.split(path)
        if basename not in ('__init__.py', '__init__.pyi'):
            return False
        try:
            st = self.stat(dirname)
        except OSError:
            return False
        else:
            if not stat.S_ISDIR(st.st_mode):
                return False
        ok = False
        drive, path = os.path.splitdrive(path)  # Ignore Windows drive name
        for root in self.package_root:
            if path.startswith(root):
                if path == root + basename:
                    # A package root itself is never a package.
                    ok = False
                    break
                else:
                    ok = True
        return ok

    def _fake_init(self, path: str) -> os.stat_result:
        dirname = os.path.dirname(path) or os.curdir
        st = self.stat(dirname)  # May raise OSError
        # Get stat result as a sequence so we can modify it.
        # (Alas, typeshed's os.stat_result is not a sequence yet.)
        tpl = tuple(st)  # type: ignore
        seq = list(tpl)  # type: List[float]
        seq[stat.ST_MODE] = stat.S_IFREG | 0o444
        seq[stat.ST_INO] = 1
        seq[stat.ST_NLINK] = 1
        seq[stat.ST_SIZE] = 0
        tpl = tuple(seq)
        st = os.stat_result(tpl)
        self.stat_cache[path] = st
        self.fake_package_cache.add(dirname)
        return st

    def listdir(self, path: str) -> List[str]:
        if path in self.listdir_cache:
            res = self.listdir_cache[path]
            if os.path.normpath(path) in self.fake_package_cache and '__init__.py' not in res:
                res.append('__init__.py')  # Updates the result as well as the cache
            return res
        if path in self.listdir_error_cache:
            raise copy_os_error(self.listdir_error_cache[path])
        try:
            results = os.listdir(path)
        except OSError as err:
            # Like above, take a copy to reduce memory use.
            self.listdir_error_cache[path] = copy_os_error(err)
            raise err
        self.listdir_cache[path] = results
        if path in self.fake_package_cache and '__init__.py' not in results:
            results.append('__init__.py')
        return results

    def isfile(self, path: str) -> bool:
        try:
            st = self.stat(path)
        except OSError:
            return False
        return stat.S_ISREG(st.st_mode)

    def isfile_case(self, path: str) -> bool:
        """Return whether path exists and is a file.

        On case-insensitive filesystems (like Mac or Windows) this returns
        False if the case of the path's last component does not exactly
        match the case found in the filesystem.
        TODO: We should maybe check the case for some directory components also,
        to avoid permitting wrongly-cased *packages*.
        """
        if path in self.isfile_case_cache:
            return self.isfile_case_cache[path]
        head, tail = os.path.split(path)
        if not tail:
            res = False
        else:
            try:
                names = self.listdir(head)
                res = tail in names and self.isfile(path)
            except OSError:
                res = False
        self.isfile_case_cache[path] = res
        return res

    def isdir(self, path: str) -> bool:
        try:
            st = self.stat(path)
        except OSError:
            return False
        return stat.S_ISDIR(st.st_mode)

    def exists(self, path: str) -> bool:
        try:
            self.stat(path)
        except FileNotFoundError:
            return False
        return True


class FileSystemCache(FileSystemMetaCache):
    def __init__(self, pyversion: Tuple[int, int],
                 package_root: Optional[List[str]] = None) -> None:
        super().__init__(package_root=package_root)
        self.pyversion = pyversion

    def flush(self) -> None:
        """Start another transaction and empty all caches."""
        super().flush()
        self.read_cache = {}  # type: Dict[str, str]
        self.read_error_cache = {}  # type: Dict[str, Exception]
        self.hash_cache = {}  # type: Dict[str, str]

    def read_with_python_encoding(self, path: str) -> str:
        if path in self.read_cache:
            return self.read_cache[path]
        if path in self.read_error_cache:
            raise self.read_error_cache[path]

        # Need to stat first so that the contents of file are from no
        # earlier instant than the mtime reported by self.stat().
        self.stat(path)
        if (os.path.basename(path) == '__init__.py'
                and os.path.dirname(path) in self.fake_package_cache):
            data = ''
            md5hash = hashlib.md5(b'').hexdigest()
        else:
            try:
                data, md5hash = read_with_python_encoding(path, self.pyversion)
            except Exception as err:
                self.read_error_cache[path] = err
                raise
        self.read_cache[path] = data
        self.hash_cache[path] = md5hash
        return data

    def md5(self, path: str) -> str:
        if path not in self.hash_cache:
            self.read_with_python_encoding(path)
        return self.hash_cache[path]


def copy_os_error(e: OSError) -> OSError:
    new = OSError(*e.args)
    new.errno = e.errno
    new.strerror = e.strerror
    new.filename = e.filename
    if e.filename2:
        new.filename2 = e.filename2
    return new
