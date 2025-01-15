from typing import Literal, Protocol, overload

class str: pass
class dict: pass
class float: pass
class int:
    def __new__(cls) -> Literal[0]: pass

class _Truthy(Protocol):
    def __bool__(self) -> Literal[True]: pass

class _Falsy(Protocol):
    def __bool__(self) -> Literal[False]: pass

class bool(int):
    @overload
    def __new__(cls, __o: _Truthy) -> Literal[True]: pass
    @overload
    def __new__(cls, __o: _Falsy) -> Literal[False]: pass
