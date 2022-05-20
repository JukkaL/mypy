from _typeshed import SupportsGetItem, SupportsItemAccess
from builtins import list as List, type as _type  # aliases to avoid name clashes with `FieldStorage` attributes
from typing import IO, Any, AnyStr, Iterable, Iterator, Mapping, Protocol
from UserDict import UserDict

def parse(
    fp: IO[Any] | None = ...,
    environ: SupportsItemAccess[str, str] = ...,
    keep_blank_values: bool = ...,
    strict_parsing: bool = ...,
) -> dict[str, list[str]]: ...
def parse_qs(qs: str, keep_blank_values: bool = ..., strict_parsing: bool = ...) -> dict[str, list[str]]: ...
def parse_qsl(qs: str, keep_blank_values: bool = ..., strict_parsing: bool = ...) -> list[tuple[str, str]]: ...
def parse_multipart(fp: IO[Any], pdict: SupportsGetItem[str, bytes]) -> dict[str, list[bytes]]: ...

class _Environ(Protocol):
    def __getitem__(self, __k: str) -> str: ...
    def keys(self) -> Iterable[str]: ...

def parse_header(line: str) -> tuple[str, dict[str, str]]: ...
def test(environ: _Environ = ...) -> None: ...
def print_environ(environ: _Environ = ...) -> None: ...
def print_form(form: dict[str, Any]) -> None: ...
def print_directory() -> None: ...
def print_environ_usage() -> None: ...
def escape(s: AnyStr, quote: bool = ...) -> AnyStr: ...

class MiniFieldStorage:
    # The first five "Any" attributes here are always None, but mypy doesn't support that
    filename: Any
    list: Any
    type: Any
    file: IO[bytes] | None
    type_options: dict[Any, Any]
    disposition: Any
    disposition_options: dict[Any, Any]
    headers: dict[Any, Any]
    name: Any
    value: Any
    def __init__(self, name: Any, value: Any) -> None: ...

class FieldStorage(object):
    FieldStorageClass: _type | None
    keep_blank_values: int
    strict_parsing: int
    qs_on_post: str | None
    headers: Mapping[str, str]
    fp: IO[bytes]
    encoding: str
    errors: str
    outerboundary: bytes
    bytes_read: int
    limit: int | None
    disposition: str
    disposition_options: dict[str, str]
    filename: str | None
    file: IO[bytes] | None
    type: str
    type_options: dict[str, str]
    innerboundary: bytes
    length: int
    done: int
    list: List[Any] | None
    value: None | bytes | List[Any]
    def __init__(
        self,
        fp: IO[Any] = ...,
        headers: Mapping[str, str] = ...,
        outerboundary: bytes = ...,
        environ: SupportsGetItem[str, str] = ...,
        keep_blank_values: int = ...,
        strict_parsing: int = ...,
    ) -> None: ...
    def __iter__(self) -> Iterator[str]: ...
    def __getitem__(self, key: str) -> Any: ...
    def getvalue(self, key: str, default: Any = ...) -> Any: ...
    def getfirst(self, key: str, default: Any = ...) -> Any: ...
    def getlist(self, key: str) -> List[Any]: ...
    def keys(self) -> List[str]: ...
    def has_key(self, key: str) -> bool: ...
    def __contains__(self, key: str) -> bool: ...
    def __len__(self) -> int: ...
    def __nonzero__(self) -> bool: ...
    # In Python 2 it always returns bytes and ignores the "binary" flag
    def make_file(self, binary: Any = ...) -> IO[bytes]: ...

class FormContentDict(UserDict[str, list[str]]):
    query_string: str
    def __init__(self, environ: Mapping[str, str] = ..., keep_blank_values: int = ..., strict_parsing: int = ...) -> None: ...

class SvFormContentDict(FormContentDict):
    def getlist(self, key: Any) -> Any: ...

class InterpFormContentDict(SvFormContentDict): ...

class FormContent(FormContentDict):
    # TODO this should have
    # def values(self, key: Any) -> Any: ...
    # but this is incompatible with the supertype, and adding '# type: ignore' triggers
    # a parse error in pytype (https://github.com/google/pytype/issues/53)
    def indexed_value(self, key: Any, location: int) -> Any: ...
    def value(self, key: Any) -> Any: ...
    def length(self, key: Any) -> int: ...
    def stripped(self, key: Any) -> Any: ...
    def pars(self) -> dict[Any, Any]: ...
