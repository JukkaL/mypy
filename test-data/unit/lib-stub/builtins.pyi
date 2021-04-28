# DO NOT ADD TO THIS FILE AS IT WILL SLOW DOWN TESTS!
#
# Use [builtins fixtures/...pyi] if you need more features.

class object:
    def __init__(self) -> None: pass

class type:
    def __init__(self, x: object) -> None: pass

# These are provided here for convenience.
class int:
    def __add__(self, other: int) -> int: pass
class float: pass

class str: pass
class bytes: pass

class function: pass
class ellipsis: pass

from typing import Generic, Sequence, TypeVar
_T = TypeVar('_T')
class list(Generic[_T], Sequence[_T]): pass

# Definition of None is implicit
