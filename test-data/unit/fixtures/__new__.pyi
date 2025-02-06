# builtins stub with object.__new__

from typing import Any

class object:
    def __init__(self) -> None: pass

    __class__ = object

    def __new__(cls) -> Any: pass

class type:
    def __init__(self, x) -> None: pass

class float: pass
class int: pass
class bool: pass
class str: pass
class function: pass
class dict: pass
