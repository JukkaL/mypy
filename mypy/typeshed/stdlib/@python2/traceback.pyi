from types import FrameType, TracebackType
from typing import IO

_PT = tuple[str, int, str, str | None]

def print_tb(tb: TracebackType | None, limit: int | None = ..., file: IO[str] | None = ...) -> None: ...
def print_exception(
    etype: type[BaseException] | None,
    value: BaseException | None,
    tb: TracebackType | None,
    limit: int | None = ...,
    file: IO[str] | None = ...,
) -> None: ...
def print_exc(limit: int | None = ..., file: IO[str] | None = ...) -> None: ...
def print_last(limit: int | None = ..., file: IO[str] | None = ...) -> None: ...
def print_stack(f: FrameType | None = ..., limit: int | None = ..., file: IO[str] | None = ...) -> None: ...
def extract_tb(tb: TracebackType | None, limit: int | None = ...) -> list[_PT]: ...
def extract_stack(f: FrameType | None = ..., limit: int | None = ...) -> list[_PT]: ...
def format_list(extracted_list: list[_PT]) -> list[str]: ...
def format_exception_only(etype: type[BaseException] | None, value: BaseException | None) -> list[str]: ...
def format_exception(
    etype: type[BaseException] | None, value: BaseException | None, tb: TracebackType | None, limit: int | None = ...
) -> list[str]: ...
def format_exc(limit: int | None = ...) -> str: ...
def format_tb(tb: TracebackType | None, limit: int | None = ...) -> list[str]: ...
def format_stack(f: FrameType | None = ..., limit: int | None = ...) -> list[str]: ...
def tb_lineno(tb: TracebackType) -> int: ...
