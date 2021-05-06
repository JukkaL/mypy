"""Pattern checker. This file is conceptually part of TypeChecker."""
from collections import defaultdict
from typing import List, Optional, Tuple, Dict, NamedTuple, Set, cast

import mypy.checker
from mypy.expandtype import expand_type_by_instance
from mypy.join import join_types
from mypy.literals import literal_hash
from mypy.messages import MessageBuilder
from mypy.nodes import Expression, ARG_POS, TypeAlias, TypeInfo, Var, NameExpr
from mypy.patterns import (
    Pattern, AsPattern, OrPattern, ValuePattern, SequencePattern, StarredPattern, MappingPattern,
    ClassPattern, SingletonPattern
)
from mypy.plugin import Plugin
from mypy.subtypes import is_subtype, find_member
from mypy.typeops import try_getting_str_literals_from_type, make_simplified_union
from mypy.types import (
    ProperType, AnyType, TypeOfAny, Instance, Type, UninhabitedType, get_proper_type,
    TypedDictType, TupleType, NoneType
)
from mypy.typevars import fill_typevars
from mypy.visitor import PatternVisitor

self_match_type_names = [
    "builtins.bool",
    "builtins.bytearray",
    "builtins.bytes",
    "builtins.dict",
    "builtins.float",
    "builtins.frozenset",
    "builtins.int",
    "builtins.list",
    "builtins.set",
    "builtins.str",
    "builtins.tuple",
]


PatternType = NamedTuple(
    'PatternType',
    [
        ('type', Optional[Type]),
        ('captures', Dict[Expression, Type]),
    ])


class PatternChecker(PatternVisitor[PatternType]):
    """Pattern checker.

    This class checks if a pattern can match a type, what the type can be narrowed to, and what
    type capture patterns should be inferred as.
    """

    # Some services are provided by a TypeChecker instance.
    chk = None  # type: mypy.checker.TypeChecker
    # This is shared with TypeChecker, but stored also here for convenience.
    msg = None  # type: MessageBuilder
    # Currently unused
    plugin = None  # type: Plugin
    # The expression being matched against the pattern
    subject = None  # type: Expression

    subject_type = None  # type: Type
    # Type of the subject to check the (sub)pattern against
    type_context = None  # type: List[Type]

    self_match_types = None  # type: List[Type]

    def __init__(self,
                 chk: 'mypy.checker.TypeChecker',
                 msg: MessageBuilder, plugin: Plugin
                 ) -> None:
        self.chk = chk
        self.msg = msg
        self.plugin = plugin

        self.type_context = []
        self.self_match_types = self.generate_self_match_types()

    def accept(self, o: Pattern, type_context: Type) -> PatternType:
        self.type_context.append(type_context)
        result = o.accept(self)
        self.type_context.pop()

        return result

    def visit_as_pattern(self, o: AsPattern) -> PatternType:
        current_type = self.type_context[-1]
        if o.pattern is not None:
            pattern_type = self.accept(o.pattern, current_type)
            typ, type_map = pattern_type
        else:
            typ, type_map = current_type, {}

        if typ is not None and o.name is not None:
            typ = get_more_specific_type(typ, current_type)
            if typ is not None:
                type_map[o.name] = typ

        return PatternType(typ, type_map)

    def visit_or_pattern(self, o: OrPattern) -> PatternType:

        #
        # Check all the subpatterns
        #
        pattern_types = []
        for pattern in o.patterns:
            pattern_types.append(self.accept(pattern, self.type_context[-1]))

        #
        # Collect the final type
        #
        types = []
        for pattern_type in pattern_types:
            if pattern_type.type is not None:
                types.append(pattern_type.type)

        #
        # Check the capture types
        #
        capture_types = defaultdict(list)  # type: Dict[Var, List[Tuple[Expression, Type]]]
        # Collect captures from the first subpattern
        for expr, typ in pattern_types[0].captures.items():
            node = get_var(expr)
            capture_types[node].append((expr, typ))

        # Check if other subpatterns capture the same names
        for i, pattern_type in enumerate(pattern_types[1:]):
            vars = {get_var(expr) for expr, _ in pattern_type.captures.items()}
            if capture_types.keys() != vars:
                self.msg.fail("Alternative patterns bind different names", o.patterns[i])
            for expr, typ in pattern_type.captures.items():
                node = get_var(expr)
                capture_types[node].append((expr, typ))

        captures = {}  # type: Dict[Expression, Type]
        for var, capture_list in capture_types.items():
            typ = UninhabitedType()
            for _, other in capture_list:
                typ = join_types(typ, other)

            captures[capture_list[0][0]] = typ

        union_type = make_simplified_union(types)
        return PatternType(union_type, captures)

    def visit_value_pattern(self, o: ValuePattern) -> PatternType:
        typ = self.chk.expr_checker.accept(o.expr)
        specific_typ = get_more_specific_type(typ, self.type_context[-1])
        return PatternType(specific_typ, {})

    def visit_singleton_pattern(self, o: SingletonPattern) -> PatternType:
        value = o.value
        if isinstance(value, bool):
            typ = self.chk.expr_checker.infer_literal_expr_type(value, "builtins.bool")
        elif value is None:
            typ = NoneType()
        else:
            assert False

        specific_type = get_more_specific_type(typ, self.type_context[-1])
        return PatternType(specific_type, {})

    def visit_sequence_pattern(self, o: SequencePattern) -> PatternType:
        #
        # check for existence of a starred pattern
        #
        current_type = get_proper_type(self.type_context[-1])
        can_match = True
        star_positions = [i for i, p in enumerate(o.patterns) if isinstance(p, StarredPattern)]
        star_position = None  # type: Optional[int]
        if len(star_positions) == 1:
            star_position = star_positions[0]
        elif len(star_positions) >= 2:
            assert False, "Parser should prevent multiple starred patterns"
        required_patterns = len(o.patterns)
        if star_position is not None:
            required_patterns -= 1

        #
        # get inner types of original type
        #
        if isinstance(current_type, TupleType):
            inner_types = current_type.items
            size_diff = len(inner_types) - required_patterns
            if size_diff < 0:
                return early_non_match()
            elif size_diff > 0 and star_position is None:
                return early_non_match()
        else:
            inner_type = self.get_sequence_type(current_type)
            if inner_type is None:
                if is_subtype(self.chk.named_type("typing.Iterable"), current_type):
                    # Current type is more general, but the actual value could still be iterable
                    inner_type = self.chk.named_type("builtins.object")
                else:
                    return early_non_match()
            inner_types = [inner_type] * len(o.patterns)

        #
        # match inner patterns
        #
        contracted_new_inner_types = []  # type: List[Type]
        captures = {}  # type: Dict[Expression, Type]

        contracted_inner_types = self.contract_starred_pattern_types(inner_types,
                                                                    star_position,
                                                                     required_patterns)
        for p, t in zip(o.patterns, contracted_inner_types):
            pattern_type = self.accept(p, t)
            typ, type_map = pattern_type
            if typ is None:
                can_match = False
            else:
                contracted_new_inner_types.append(typ)
            self.update_type_map(captures, type_map)
        new_inner_types = self.expand_starred_pattern_types(contracted_new_inner_types,
                                                            star_position,
                                                            len(inner_types))

        #
        # Calculate new type
        #
        if not can_match:
            new_type = None  # type: Optional[Type]
        elif isinstance(current_type, TupleType):
            specific_inner_types = []
            for inner_type, new_inner_type in zip(inner_types, new_inner_types):
                specific_inner_types.append(get_more_specific_type(inner_type, new_inner_type))
            if all(typ is not None for typ in specific_inner_types):
                specific_inner_types_cast = cast(List[Type], specific_inner_types)
                new_type = TupleType(specific_inner_types_cast, current_type.partial_fallback)
            else:
                new_type = None
        else:
            new_inner_type = UninhabitedType()
            for typ in new_inner_types:
                new_inner_type = join_types(new_inner_type, typ)
            new_type = self.construct_iterable_child(current_type, new_inner_type)
            if not is_subtype(new_type, current_type):
                new_type = current_type
        return PatternType(new_type, captures)

    def get_sequence_type(self, t: Type) -> Optional[Type]:
        t = get_proper_type(t)
        if isinstance(t, AnyType):
            return AnyType(TypeOfAny.from_another_any, t)

        if self.chk.type_is_iterable(t) and isinstance(t, Instance):
            return self.chk.iterable_item_type(t)
        else:
            return None

    def contract_starred_pattern_types(self,
                                       types: List[Type],
                                       star_pos: Optional[int],
                                       num_patterns: int
                                       ) -> List[Type]:
        if star_pos is None:
            return types
        new_types = types[:star_pos]
        star_length = len(types) - num_patterns
        new_types.append(make_simplified_union(types[star_pos:star_pos+star_length]))
        new_types += types[star_pos+star_length:]

        return new_types

    def expand_starred_pattern_types(self,
                                     types: List[Type],
                                     star_pos: Optional[int],
                                     num_types: int
                                     ) -> List[Type]:
        if star_pos is None:
            return types
        new_types = types[:star_pos]
        star_length = num_types - len(types) + 1
        new_types += [types[star_pos]] * star_length
        new_types += types[star_pos+1:]

        return new_types

    def visit_starred_pattern(self, o: StarredPattern) -> PatternType:
        captures = {}  # type: Dict[Expression, Type]
        if o.capture is not None:
            list_type = self.chk.named_generic_type('builtins.list', [self.type_context[-1]])
            captures[o.capture] = list_type
        return PatternType(self.type_context[-1], captures)

    def visit_mapping_pattern(self, o: MappingPattern) -> PatternType:
        current_type = self.type_context[-1]
        can_match = True
        captures = {}  # type: Dict[Expression, Type]
        for key, value in zip(o.keys, o.values):
            inner_type = self.get_mapping_item_type(o, current_type, key)
            if inner_type is None:
                can_match = False
                inner_type = self.chk.named_type("builtins.object")
            pattern_type = self.accept(value, inner_type)
            if pattern_type is None:
                can_match = False
            else:
                self.update_type_map(captures, pattern_type.captures)

        if o.rest is not None:
            # TODO: Infer dict type args
            captures[o.rest] = self.chk.named_type("builtins.dict")

        if can_match:
            new_type = self.type_context[-1]  # type: Optional[Type]
        else:
            new_type = None
        return PatternType(new_type, captures)

    def get_mapping_item_type(self,
                              pattern: MappingPattern,
                              mapping_type: Type,
                              key: Expression
                              ) -> Optional[Type]:
        local_errors = self.msg.clean_copy()
        local_errors.disable_count = 0
        mapping_type = get_proper_type(mapping_type)
        if isinstance(mapping_type, TypedDictType):
            result = self.chk.expr_checker.visit_typeddict_index_expr(mapping_type,
                                                                      key,
                                                                      local_errors=local_errors
                                                                      )  # type: Optional[Type]
            # If we can't determine the type statically fall back to treating it as a normal
            # mapping
            if local_errors.is_errors():
                local_errors = self.msg.clean_copy()
                local_errors.disable_count = 0
                result = self.get_simple_mapping_item_type(pattern,
                                                           mapping_type,
                                                           key,
                                                           local_errors)

                if local_errors.is_errors():
                    result = None
        else:
            result = self.get_simple_mapping_item_type(pattern,
                                                       mapping_type,
                                                       key,
                                                       local_errors)
        return result

    def get_simple_mapping_item_type(self,
                                     pattern: MappingPattern,
                                     mapping_type: Type,
                                     key: Expression,
                                     local_errors: MessageBuilder
                                     ) -> Type:
        result, _ = self.chk.expr_checker.check_method_call_by_name('__getitem__',
                                                                    mapping_type,
                                                                    [key],
                                                                    [ARG_POS],
                                                                    pattern,
                                                                    local_errors=local_errors)
        return result

    def visit_class_pattern(self, o: ClassPattern) -> PatternType:
        current_type = self.type_context[-1]

        #
        # Check class type
        #
        class_name = o.class_ref.fullname
        assert class_name is not None
        sym = self.chk.lookup_qualified(class_name)
        if isinstance(sym.node, TypeAlias) and not sym.node.no_args:
            self.msg.fail("Class pattern class must not be a type alias with type parameters", o)
            return early_non_match()
        if isinstance(sym.node, (TypeAlias, TypeInfo)):
            typ = self.chk.named_type(class_name)
        else:
            self.msg.fail('Class pattern must be a type. Found "{}"'.format(sym.type), o.class_ref)
            return early_non_match()

        #
        # Convert positional to keyword patterns
        #
        keyword_pairs = []  # type: List[Tuple[Optional[str], Pattern]]
        match_arg_set = set()  # type: Set[str]

        captures = {}  # type: Dict[Expression, Type]

        if len(o.positionals) != 0:
            if self.should_self_match(typ):
                if len(o.positionals) > 1:
                    self.msg.fail("Too many positional patterns for class pattern", o)
                pattern_type = self.accept(o.positionals[0], typ)
                if pattern_type.type is None:
                    return pattern_type
                captures = pattern_type.captures
            else:
                match_args_type = find_member("__match_args__", typ, typ)

                if match_args_type is None:
                    self.msg.fail("Class doesn't define __match_args__", o)
                    return early_non_match()

                proper_match_args_type = get_proper_type(match_args_type)
                if isinstance(proper_match_args_type, TupleType):
                    match_arg_names = get_match_arg_names(proper_match_args_type)

                    if len(o.positionals) > len(match_arg_names):
                        self.msg.fail("Too many positional patterns for class pattern", o)
                        return early_non_match()
                else:
                    match_arg_names = [None] * len(o.positionals)

                for arg_name, pos in zip(match_arg_names, o.positionals):
                    keyword_pairs.append((arg_name, pos))
                    if arg_name is not None:
                        match_arg_set.add(arg_name)

        #
        # Check for duplicate patterns
        #
        keyword_arg_set = set()
        has_duplicates = False
        for key, value in zip(o.keyword_keys, o.keyword_values):
            keyword_pairs.append((key, value))
            if key in match_arg_set:
                self.msg.fail('Keyword "{}" already matches a positional pattern'.format(key),
                              value)
                has_duplicates = True
            elif key in keyword_arg_set:
                self.msg.fail('Duplicate keyword pattern "{}"'.format(key), value)
                has_duplicates = True
            keyword_arg_set.add(key)

        if has_duplicates:
            return early_non_match()

        #
        # Check keyword patterns
        #
        can_match = True
        for keyword, pattern in keyword_pairs:
            key_type = None  # type: Optional[Type]
            if keyword is not None:
                key_type = find_member(keyword, typ, current_type)
            if key_type is None:
                key_type = AnyType(TypeOfAny.implementation_artifact)

            pattern_type = self.accept(pattern, key_type)
            if pattern_type is None:
                can_match = False
            else:
                self.update_type_map(captures, pattern_type.captures)

        if can_match:
            new_type = get_more_specific_type(current_type, typ)
        else:
            new_type = None
        return PatternType(new_type, captures)

    def should_self_match(self, typ: ProperType) -> bool:
        if isinstance(typ, Instance) and typ.type.is_named_tuple:
            return False
        for other in self.self_match_types:
            if is_subtype(typ, other):
                return True
        return False

    def generate_self_match_types(self) -> List[Type]:
        types = []  # type: List[Type]
        for name in self_match_type_names:
            try:
                types.append(self.chk.named_type(name))
            except KeyError:
                # Some built in types are not defined in all test cases
                pass

        return types

    def update_type_map(self,
                        original_type_map: Dict[Expression, Type],
                        extra_type_map: Dict[Expression, Type]
                        ) -> None:
        # Calculating this would not be needed if TypeMap directly used literal hashes instead of
        # expressions, as suggested in the TODO above it's definition
        already_captured = set(literal_hash(expr) for expr in original_type_map)
        for expr, typ in extra_type_map.items():
            if literal_hash(expr) in already_captured:
                node = get_var(expr)
                self.msg.fail('Multiple assignments to name "{}" in pattern'.format(node.name),
                              expr)
            else:
                original_type_map[expr] = typ

    def construct_iterable_child(self, outer_type: Type, inner_type: Type) -> Type:
        iterable = self.chk.named_generic_type("typing.Iterable", [inner_type])
        if self.chk.type_is_iterable(outer_type):
            proper_type = get_proper_type(outer_type)
            assert isinstance(proper_type, Instance)
            empty_type = fill_typevars(proper_type.type)
            partial_type = expand_type_by_instance(empty_type, iterable)
            return expand_type_by_instance(partial_type, proper_type)
        else:
            return iterable


def get_match_arg_names(typ: TupleType) -> List[Optional[str]]:
    args = []  # type: List[Optional[str]]
    for item in typ.items:
        values = try_getting_str_literals_from_type(item)
        if values is None or len(values) != 1:
            args.append(None)
        else:
            args.append(values[0])
    return args


def get_more_specific_type(left: Optional[Type], right: Optional[Type]) -> Optional[Type]:
    if left is None or right is None:
        return None
    elif is_subtype(left, right):
        return left
    elif is_subtype(right, left):
        return right
    else:
        return None


def early_non_match() -> PatternType:
    return PatternType(None, {})


def get_var(expr: Expression) -> Var:
    """
    Warning: this in only true for expressions captured by a match statement.
    Don't call it from anywhere else
    """
    assert isinstance(expr, NameExpr)
    node = expr.node
    assert isinstance(node, Var)
    return node
