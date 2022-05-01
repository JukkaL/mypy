from typing import Any, Iterable, Iterator, Protocol, Sequence, Text, Union

QUOTE_ALL: int
QUOTE_MINIMAL: int
QUOTE_NONE: int
QUOTE_NONNUMERIC: int

class Error(Exception): ...

class Dialect:
    delimiter: str
    quotechar: str | None
    escapechar: str | None
    doublequote: bool
    skipinitialspace: bool
    lineterminator: str
    quoting: int
    strict: int
    def __init__(self) -> None: ...

_DialectLike = Union[str, Dialect, type[Dialect]]

class _reader(Iterator[list[str]]):
    dialect: Dialect
    line_num: int
    def next(self) -> list[str]: ...

class _writer:
    dialect: Dialect
    def writerow(self, row: Sequence[Any]) -> Any: ...
    def writerows(self, rows: Iterable[Sequence[Any]]) -> None: ...

class _Writer(Protocol):
    def write(self, s: str) -> Any: ...

def writer(csvfile: _Writer, dialect: _DialectLike = ..., **fmtparams: Any) -> _writer: ...
def reader(csvfile: Iterable[Text], dialect: _DialectLike = ..., **fmtparams: Any) -> _reader: ...
def register_dialect(name: str, dialect: Any = ..., **fmtparams: Any) -> None: ...
def unregister_dialect(name: str) -> None: ...
def get_dialect(name: str) -> Dialect: ...
def list_dialects() -> list[str]: ...
def field_size_limit(new_limit: int = ...) -> int: ...
