from typing import Callable, Optional

from mypy.plugin import AttributeContext, Plugin
from mypy.types import Type as MypyType


class ClassAttrPlugin(Plugin):
    def get_class_attribute_hook(self, fullname: str
                                 ) -> Optional[Callable[[AttributeContext], MypyType]]:
        if fullname == '__main__.Cls.attr':
            return my_hook
        return None


def my_hook(ctx: AttributeContext) -> MypyType:
    return ctx.api.named_generic_type('builtins.int', [])


def plugin(_version: str):
    return ClassAttrPlugin
