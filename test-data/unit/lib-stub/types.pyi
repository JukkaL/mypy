from typing import TypeVar

_T = TypeVar('_T')

def coroutine(func: _T) -> _T: pass

class ModuleType:
    __file__ = ... # type: str
