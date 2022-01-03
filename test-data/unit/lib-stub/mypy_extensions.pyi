# NOTE: Requires fixtures/dict.pyi
from typing import (
    Any, Dict, Type, TypeVar, Optional, Any, Generic, Mapping, NoReturn as NoReturn, Iterator
)
import sys

_T = TypeVar('_T')
_VT = TypeVar('_VT')
_U = TypeVar('_U')


def Arg(type: _T = ..., name: Optional[str] = ...) -> _T: ...

def DefaultArg(type: _T = ..., name: Optional[str] = ...) -> _T: ...

def NamedArg(type: _T = ..., name: Optional[str] = ...) -> _T: ...

def DefaultNamedArg(type: _T = ..., name: Optional[str] = ...) -> _T: ...

def VarArg(type: _T = ...) -> _T: ...

def KwArg(type: _T = ...) -> _T: ...


# Fallback type for all typed dicts (does not exist at runtime).
class _TypedDict(Mapping[str, _VT]):
    # Needed to make this class non-abstract. It is explicitly declared abstract in
    # typeshed, but we don't want to import abc here, as it would slow down the tests.
    def __iter__(self) -> Iterator[str]: ...
    def copy(self: _T) -> _T: ...
    # Using NoReturn so that only calls using the plugin hook can go through.
    def setdefault(self, k: NoReturn, default: _VT) -> _VT: ...
    # Mypy expects that 'default' has a type variable type.
    def pop(self, k: NoReturn, default: _T = ...) -> _VT: ...
    def update(self: _T, __m: _T) -> None: ...
    if sys.version_info < (3, 0):
        def has_key(self, k: str) -> bool: ...
    def __delitem__(self, k: NoReturn) -> None: ...

def TypedDict(typename: str, fields: Dict[str, Type[_T]], *, total: Any = ...) -> Type[dict]: ...

# This is intended as a class decorator, but mypy rejects abstract classes
# when a Type[_T] is expected, so we can't give it the type we want.
def trait(cls: Any) -> Any: ...

# The real type is in the comment but it isn't safe to use **kwargs in
# a lib-stub because the fixtures might not have dict. Argh!
# def mypyc_attr(*attrs: str, **kwattrs: object) -> Callable[[_T], _T]: ...
mypyc_attr: Any

class FlexibleAlias(Generic[_T, _U]): ...
