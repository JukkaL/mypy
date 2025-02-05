from typing import Any, Callable, Generic, TypeVar

_T = TypeVar('_T')

class object:
    def __init__(self) -> None: pass

class type:
    def __init__(self, x: Any) -> None: pass

class function: pass

class property:
    fget: Callable[[Any], Any] | None
    fset: Callable[[Any, Any], None] | None
    fdel: Callable[[Any], None] | None
    __isabstractmethod__: bool

    def __init__(
        self,
        fget: Callable[[Any], Any] | None = ...,
        fset: Callable[[Any, Any], None] | None = ...,
        fdel: Callable[[Any], None] | None = ...,
        doc: str | None = ...,
    ) -> None: ...
    def getter(self, fget: Callable[[Any], Any], /) -> property: ...
    def setter(self, fset: Callable[[Any, Any], None], /) -> property: ...
    def deleter(self, fdel: Callable[[Any], None], /) -> property: ...
    def __get__(self, instance: Any, owner: type | None = None, /) -> Any: ...
    def __set__(self, instance: Any, value: Any, /) -> None: ...
    def __delete__(self, instance: Any, /) -> None: ...
class classmethod: pass

class list: pass
class dict: pass
class int: pass
class float: pass
class str: pass
class bytes: pass
class bool: pass
class ellipsis: pass

class tuple(Generic[_T]): pass
