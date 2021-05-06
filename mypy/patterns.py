"""Classes for representing match statement patterns."""
from typing import TypeVar, List, Optional, Union

from mypy_extensions import trait

from mypy.nodes import Node, RefExpr, NameExpr, Expression
from mypy.visitor import PatternVisitor

# These are not real AST nodes. CPython represents patterns using the normal expression nodes.

T = TypeVar('T')


@trait
class Pattern(Node):
    """A pattern node."""

    __slots__ = ()

    def accept(self, visitor: PatternVisitor[T]) -> T:
        raise RuntimeError('Not implemented')


@trait
class AlwaysTruePattern(Pattern):
    """A pattern that is always matches"""

    __slots__ = ()


class AsPattern(Pattern):
    pattern = None  # type: Optional[Pattern]
    name = None  # type: Optional[NameExpr]

    def __init__(self, pattern: Optional[Pattern], name: Optional[NameExpr]) -> None:
        super().__init__()
        self.pattern = pattern
        self.name = name

    def accept(self, visitor: PatternVisitor[T]) -> T:
        return visitor.visit_as_pattern(self)


class OrPattern(Pattern):
    patterns = None  # type: List[Pattern]

    def __init__(self, patterns: List[Pattern]) -> None:
        super().__init__()
        self.patterns = patterns

    def accept(self, visitor: PatternVisitor[T]) -> T:
        return visitor.visit_or_pattern(self)


class ValuePattern(Pattern):
    expr = None  # type: Expression

    def __init__(self, expr: Expression):
        super().__init__()
        self.expr = expr

    def accept(self, visitor: PatternVisitor[T]) -> T:
        return visitor.visit_value_pattern(self)


class SingletonPattern(Pattern):
    value = None  # type: Union[bool, None]

    def __init__(self, value: Union[bool, None]):
        super().__init__()
        self.value = value

    def accept(self, visitor: PatternVisitor[T]) -> T:
        return visitor.visit_singleton_pattern(self)


class SequencePattern(Pattern):
    patterns = None  # type: List[Pattern]

    def __init__(self, patterns: List[Pattern]):
        super().__init__()
        self.patterns = patterns

    def accept(self, visitor: PatternVisitor[T]) -> T:
        return visitor.visit_sequence_pattern(self)


# TODO: A StarredPattern is only valid within a SequencePattern. This is not guaranteed by our
# type hierarchy. Should it be?
class StarredPattern(Pattern):
    capture = None  # type: Optional[NameExpr]

    def __init__(self, capture: Optional[NameExpr]):
        super().__init__()
        self.capture = capture

    def accept(self, visitor: PatternVisitor[T]) -> T:
        return visitor.visit_starred_pattern(self)


class MappingPattern(Pattern):
    keys = None  # type: List[Expression]
    values = None  # type: List[Pattern]
    rest = None  # type: Optional[NameExpr]

    def __init__(self, keys: List[Expression], values: List[Pattern],
                 rest: Optional[NameExpr]):
        super().__init__()
        self.keys = keys
        self.values = values
        self.rest = rest

    def accept(self, visitor: PatternVisitor[T]) -> T:
        return visitor.visit_mapping_pattern(self)


class ClassPattern(Pattern):
    class_ref = None  # type: RefExpr
    positionals = None  # type: List[Pattern]
    keyword_keys = None  # type: List[str]
    keyword_values = None  # type: List[Pattern]

    def __init__(self, class_ref: RefExpr, positionals: List[Pattern], keyword_keys: List[str],
                 keyword_values: List[Pattern]):
        super().__init__()
        self.class_ref = class_ref
        self.positionals = positionals
        self.keyword_keys = keyword_keys
        self.keyword_values = keyword_values

    def accept(self, visitor: PatternVisitor[T]) -> T:
        return visitor.visit_class_pattern(self)
