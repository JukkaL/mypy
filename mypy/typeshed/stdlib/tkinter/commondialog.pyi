from typing import Any, ClassVar, Mapping, Optional

class Dialog:
    command: ClassVar[Optional[str]] = ...
    master: Optional[Any] = ...
    options: Mapping[str, Any] = ...
    def __init__(self, master: Optional[Any] = ..., **options) -> None: ...
    def show(self, **options) -> Any: ...
