"""Facilities for generating error messages during type checking.

Don't add any non-trivial message construction logic to the type
checker, as it can compromise clarity and make messages less
consistent. Add such logic to this module instead. Literal messages, including those
with format args, should be defined as constants in mypy.message_registry.

Historically we tried to avoid all message string literals in the type
checker but we are moving away from this convention.
"""

from __future__ import annotations

import difflib
import itertools
import re
from collections.abc import Collection, Iterable, Iterator, Sequence
from contextlib import contextmanager
from textwrap import dedent
from typing import Any, Callable, Final, cast

import mypy.typeops
from mypy import errorcodes as codes, message_registry
from mypy.erasetype import erase_type
from mypy.errorcodes import ErrorCode
from mypy.errors import ErrorInfo, Errors, ErrorWatcher
from mypy.nodes import (
    ARG_NAMED,
    ARG_NAMED_OPT,
    ARG_OPT,
    ARG_POS,
    ARG_STAR,
    ARG_STAR2,
    CONTRAVARIANT,
    COVARIANT,
    SYMBOL_FUNCBASE_TYPES,
    ArgKind,
    CallExpr,
    ClassDef,
    Context,
    Expression,
    FuncDef,
    IndexExpr,
    MypyFile,
    NameExpr,
    ReturnStmt,
    StrExpr,
    SymbolNode,
    SymbolTable,
    TypeInfo,
    Var,
    reverse_builtin_aliases,
)
from mypy.operators import op_methods, op_methods_to_symbols
from mypy.options import Options
from mypy.subtypes import (
    IS_CLASS_OR_STATIC,
    IS_CLASSVAR,
    IS_SETTABLE,
    IS_VAR,
    find_member,
    get_member_flags,
    is_same_type,
    is_subtype,
)
from mypy.typeops import separate_union_literals
from mypy.types import (
    AnyType,
    CallableType,
    DeletedType,
    FunctionLike,
    Instance,
    LiteralType,
    NoneType,
    Overloaded,
    Parameters,
    ParamSpecType,
    PartialType,
    ProperType,
    TupleType,
    Type,
    TypeAliasType,
    TypedDictType,
    TypeOfAny,
    TypeStrVisitor,
    TypeType,
    TypeVarLikeType,
    TypeVarTupleType,
    TypeVarType,
    UnboundType,
    UninhabitedType,
    UnionType,
    UnpackType,
    flatten_nested_unions,
    get_proper_type,
    get_proper_types,
)
from mypy.typetraverser import TypeTraverserVisitor
from mypy.util import plural_s, unmangle

TYPES_FOR_UNIMPORTED_HINTS: Final = {
    "typing.Any",
    "typing.Callable",
    "typing.Dict",
    "typing.Iterable",
    "typing.Iterator",
    "typing.List",
    "typing.Optional",
    "typing.Set",
    "typing.Tuple",
    "typing.TypeVar",
    "typing.Union",
    "typing.cast",
}


ARG_CONSTRUCTOR_NAMES: Final = {
    ARG_POS: "Arg",
    ARG_OPT: "DefaultArg",
    ARG_NAMED: "NamedArg",
    ARG_NAMED_OPT: "DefaultNamedArg",
    ARG_STAR: "VarArg",
    ARG_STAR2: "KwArg",
}


# Map from the full name of a missing definition to the test fixture (under
# test-data/unit/fixtures/) that provides the definition. This is used for
# generating better error messages when running mypy tests only.
SUGGESTED_TEST_FIXTURES: Final = {
    "builtins.set": "set.pyi",
    "builtins.tuple": "tuple.pyi",
    "builtins.bool": "bool.pyi",
    "builtins.Exception": "exception.pyi",
    "builtins.BaseException": "exception.pyi",
    "builtins.isinstance": "isinstancelist.pyi",
    "builtins.property": "property.pyi",
    "builtins.classmethod": "classmethod.pyi",
    "typing._SpecialForm": "typing-medium.pyi",
}

UNSUPPORTED_NUMBERS_TYPES: Final = {
    "numbers.Number",
    "numbers.Complex",
    "numbers.Real",
    "numbers.Rational",
    "numbers.Integral",
}

MAX_TUPLE_ITEMS = 10
MAX_UNION_ITEMS = 10


class MessageBuilder:
    """Helper class for reporting type checker error messages with parameters.

    The methods of this class need to be provided with the context within a
    file; the errors member manages the wider context.

    IDEA: Support a 'verbose mode' that includes full information about types
          in error messages and that may otherwise produce more detailed error
          messages.
    """

    # Report errors using this instance. It knows about the current file and
    # import context.
    errors: Errors

    modules: dict[str, MypyFile]

    # Hack to deduplicate error messages from union types
    _disable_type_names: list[bool]

    def __init__(self, errors: Errors, modules: dict[str, MypyFile]) -> None:
        self.errors = errors
        self.options = errors.options
        self.modules = modules
        self._disable_type_names = []

    #
    # Helpers
    #

    def filter_errors(
        self,
        *,
        filter_errors: bool | Callable[[str, ErrorInfo], bool] = True,
        save_filtered_errors: bool = False,
    ) -> ErrorWatcher:
        return ErrorWatcher(
            self.errors, filter_errors=filter_errors, save_filtered_errors=save_filtered_errors
        )

    def add_errors(self, errors: list[ErrorInfo]) -> None:
        """Add errors in messages to this builder."""
        for info in errors:
            self.errors.add_error_info(info)

    @contextmanager
    def disable_type_names(self) -> Iterator[None]:
        self._disable_type_names.append(True)
        try:
            yield
        finally:
            self._disable_type_names.pop()

    def are_type_names_disabled(self) -> bool:
        return len(self._disable_type_names) > 0 and self._disable_type_names[-1]

    def prefer_simple_messages(self) -> bool:
        """Should we generate simple/fast error messages?

        If errors aren't shown to the user, we don't want to waste cyles producing
        complex error messages.
        """
        return self.errors.prefer_simple_messages()

    def report(
        self,
        msg: str,
        context: Context | None,
        severity: str,
        *,
        code: ErrorCode | None = None,
        file: str | None = None,
        origin: Context | None = None,
        offset: int = 0,
        allow_dups: bool = False,
        secondary_context: Context | None = None,
    ) -> None:
        """Report an error or note (unless disabled).

        Note that context controls where error is reported, while origin controls
        where # type: ignore comments have effect.
        """

        def span_from_context(ctx: Context) -> Iterable[int]:
            """This determines where a type: ignore for a given context has effect.

            Current logic is a bit tricky, to keep as much backwards compatibility as
            possible. We may reconsider this to always be a single line (or otherwise
            simplify it) when we drop Python 3.7.

            TODO: address this in follow up PR
            """
            if isinstance(ctx, (ClassDef, FuncDef)):
                return range(ctx.line, ctx.line + 1)
            elif not isinstance(ctx, Expression):
                return [ctx.line]
            else:
                return range(ctx.line, (ctx.end_line or ctx.line) + 1)

        origin_span: Iterable[int] | None
        if origin is not None:
            origin_span = span_from_context(origin)
        elif context is not None:
            origin_span = span_from_context(context)
        else:
            origin_span = None

        if secondary_context is not None:
            assert origin_span is not None
            origin_span = itertools.chain(origin_span, span_from_context(secondary_context))

        self.errors.report(
            context.line if context else -1,
            context.column if context else -1,
            msg,
            severity=severity,
            file=file,
            offset=offset,
            origin_span=origin_span,
            end_line=context.end_line if context else -1,
            end_column=context.end_column if context else -1,
            code=code,
            allow_dups=allow_dups,
        )

    def fail(
        self,
        msg: str,
        context: Context | None,
        *,
        code: ErrorCode | None = None,
        file: str | None = None,
        allow_dups: bool = False,
        secondary_context: Context | None = None,
    ) -> None:
        """Report an error message (unless disabled)."""
        self.report(
            msg,
            context,
            "error",
            code=code,
            file=file,
            allow_dups=allow_dups,
            secondary_context=secondary_context,
        )

    def note(
        self,
        msg: str,
        context: Context,
        file: str | None = None,
        origin: Context | None = None,
        offset: int = 0,
        allow_dups: bool = False,
        *,
        code: ErrorCode | None = None,
        secondary_context: Context | None = None,
    ) -> None:
        """Report a note (unless disabled)."""
        self.report(
            msg,
            context,
            "note",
            file=file,
            origin=origin,
            offset=offset,
            allow_dups=allow_dups,
            code=code,
            secondary_context=secondary_context,
        )

    def note_multiline(
        self,
        messages: str,
        context: Context,
        file: str | None = None,
        offset: int = 0,
        allow_dups: bool = False,
        code: ErrorCode | None = None,
        *,
        secondary_context: Context | None = None,
    ) -> None:
        """Report as many notes as lines in the message (unless disabled)."""
        for msg in messages.splitlines():
            self.report(
                msg,
                context,
                "note",
                file=file,
                offset=offset,
                allow_dups=allow_dups,
                code=code,
                secondary_context=secondary_context,
            )

    #
    # Specific operations
    #

    # The following operations are for generating specific error messages. They
    # get some information as arguments, and they build an error message based
    # on them.

    def has_no_attr(
        self,
        original_type: Type,
        typ: Type,
        member: str,
        context: Context,
        module_symbol_table: SymbolTable | None = None,
    ) -> ErrorCode | None:
        """Report a missing or non-accessible member.

        original_type is the top-level type on which the error occurred.
        typ is the actual type that is missing the member. These can be
        different, e.g., in a union, original_type will be the union and typ
        will be the specific item in the union that does not have the member
        attribute.

        'module_symbol_table' is passed to this function if the type for which we
        are trying to get a member was originally a module. The SymbolTable allows
        us to look up and suggests attributes of the module since they are not
        directly available on original_type

        If member corresponds to an operator, use the corresponding operator
        name in the messages. Return the error code that was produced, if any.
        """
        original_type = get_proper_type(original_type)
        typ = get_proper_type(typ)

        if isinstance(original_type, Instance) and original_type.type.has_readable_member(member):
            self.fail(f'Member "{member}" is not assignable', context)
            return None
        elif member == "__contains__":
            self.fail(
                f"Unsupported right operand type for in ({format_type(original_type, self.options)})",
                context,
                code=codes.OPERATOR,
            )
            return codes.OPERATOR
        elif member in op_methods.values():
            # Access to a binary operator member (e.g. _add). This case does
            # not handle indexing operations.
            for op, method in op_methods.items():
                if method == member:
                    self.unsupported_left_operand(op, original_type, context)
                    return codes.OPERATOR
        elif member == "__neg__":
            self.fail(
                f"Unsupported operand type for unary - ({format_type(original_type, self.options)})",
                context,
                code=codes.OPERATOR,
            )
            return codes.OPERATOR
        elif member == "__pos__":
            self.fail(
                f"Unsupported operand type for unary + ({format_type(original_type, self.options)})",
                context,
                code=codes.OPERATOR,
            )
            return codes.OPERATOR
        elif member == "__invert__":
            self.fail(
                f"Unsupported operand type for ~ ({format_type(original_type, self.options)})",
                context,
                code=codes.OPERATOR,
            )
            return codes.OPERATOR
        elif member == "__getitem__":
            # Indexed get.
            # TODO: Fix this consistently in format_type
            if isinstance(original_type, FunctionLike) and original_type.is_type_obj():
                self.fail(
                    "The type {} is not generic and not indexable".format(
                        format_type(original_type, self.options)
                    ),
                    context,
                )
                return None
            else:
                self.fail(
                    f"Value of type {format_type(original_type, self.options)} is not indexable",
                    context,
                    code=codes.INDEX,
                )
                return codes.INDEX
        elif member == "__setitem__":
            # Indexed set.
            self.fail(
                "Unsupported target for indexed assignment ({})".format(
                    format_type(original_type, self.options)
                ),
                context,
                code=codes.INDEX,
            )
            return codes.INDEX
        elif member == "__call__":
            if isinstance(original_type, Instance) and (
                original_type.type.fullname == "builtins.function"
            ):
                # "'function' not callable" is a confusing error message.
                # Explain that the problem is that the type of the function is not known.
                self.fail("Cannot call function of unknown type", context, code=codes.OPERATOR)
                return codes.OPERATOR
            else:
                self.fail(
                    message_registry.NOT_CALLABLE.format(format_type(original_type, self.options)),
                    context,
                    code=codes.OPERATOR,
                )
                return codes.OPERATOR
        else:
            # The non-special case: a missing ordinary attribute.
            extra = ""
            if member == "__iter__":
                extra = " (not iterable)"
            elif member == "__aiter__":
                extra = " (not async iterable)"
            if not self.are_type_names_disabled():
                failed = False
                if isinstance(original_type, Instance) and original_type.type.names:
                    if (
                        module_symbol_table is not None
                        and member in module_symbol_table
                        and not module_symbol_table[member].module_public
                    ):
                        self.fail(
                            f"{format_type(original_type, self.options, module_names=True)} does not "
                            f'explicitly export attribute "{member}"',
                            context,
                            code=codes.ATTR_DEFINED,
                        )
                        failed = True
                    else:
                        alternatives = set(original_type.type.names.keys())
                        if module_symbol_table is not None:
                            alternatives |= {
                                k for k, v in module_symbol_table.items() if v.module_public
                            }
                        # Rare but possible, see e.g. testNewAnalyzerCyclicDefinitionCrossModule
                        alternatives.discard(member)

                        matches = [m for m in COMMON_MISTAKES.get(member, []) if m in alternatives]
                        matches.extend(best_matches(member, alternatives, n=3))
                        if member == "__aiter__" and matches == ["__iter__"]:
                            matches = []  # Avoid misleading suggestion
                        if matches:
                            self.fail(
                                '{} has no attribute "{}"; maybe {}?{}'.format(
                                    format_type(original_type, self.options),
                                    member,
                                    pretty_seq(matches, "or"),
                                    extra,
                                ),
                                context,
                                code=codes.ATTR_DEFINED,
                            )
                            failed = True
                if not failed:
                    self.fail(
                        '{} has no attribute "{}"{}'.format(
                            format_type(original_type, self.options), member, extra
                        ),
                        context,
                        code=codes.ATTR_DEFINED,
                    )
                return codes.ATTR_DEFINED
            elif isinstance(original_type, UnionType):
                # The checker passes "object" in lieu of "None" for attribute
                # checks, so we manually convert it back.
                typ_format, orig_type_format = format_type_distinctly(
                    typ, original_type, options=self.options
                )
                if typ_format == '"object"' and any(
                    type(item) == NoneType for item in original_type.items
                ):
                    typ_format = '"None"'
                self.fail(
                    'Item {} of {} has no attribute "{}"{}'.format(
                        typ_format, orig_type_format, member, extra
                    ),
                    context,
                    code=codes.UNION_ATTR,
                )
                return codes.UNION_ATTR
            elif isinstance(original_type, TypeVarType):
                bound = get_proper_type(original_type.upper_bound)
                if isinstance(bound, UnionType):
                    typ_fmt, bound_fmt = format_type_distinctly(typ, bound, options=self.options)
                    original_type_fmt = format_type(original_type, self.options)
                    self.fail(
                        "Item {} of the upper bound {} of type variable {} has no "
                        'attribute "{}"{}'.format(
                            typ_fmt, bound_fmt, original_type_fmt, member, extra
                        ),
                        context,
                        code=codes.UNION_ATTR,
                    )
                    return codes.UNION_ATTR
            else:
                self.fail(
                    '{} has no attribute "{}"{}'.format(
                        format_type(original_type, self.options), member, extra
                    ),
                    context,
                    code=codes.ATTR_DEFINED,
                )
                return codes.ATTR_DEFINED
        return None

    def unsupported_operand_types(
        self,
        op: str,
        left_type: Any,
        right_type: Any,
        context: Context,
        *,
        code: ErrorCode = codes.OPERATOR,
    ) -> None:
        """Report unsupported operand types for a binary operation.

        Types can be Type objects or strings.
        """
        left_str = ""
        if isinstance(left_type, str):
            left_str = left_type
        else:
            left_str = format_type(left_type, self.options)

        right_str = ""
        if isinstance(right_type, str):
            right_str = right_type
        else:
            right_str = format_type(right_type, self.options)

        if self.are_type_names_disabled():
            msg = f"Unsupported operand types for {op} (likely involving Union)"
        else:
            msg = f"Unsupported operand types for {op} ({left_str} and {right_str})"
        self.fail(msg, context, code=code)

    def unsupported_left_operand(self, op: str, typ: Type, context: Context) -> None:
        if self.are_type_names_disabled():
            msg = f"Unsupported left operand type for {op} (some union)"
        else:
            msg = f"Unsupported left operand type for {op} ({format_type(typ, self.options)})"
        self.fail(msg, context, code=codes.OPERATOR)

    def not_callable(self, typ: Type, context: Context) -> Type:
        self.fail(message_registry.NOT_CALLABLE.format(format_type(typ, self.options)), context)
        return AnyType(TypeOfAny.from_error)

    def untyped_function_call(self, callee: CallableType, context: Context) -> Type:
        name = callable_name(callee) or "(unknown)"
        self.fail(
            f"Call to untyped function {name} in typed context",
            context,
            code=codes.NO_UNTYPED_CALL,
        )
        return AnyType(TypeOfAny.from_error)

    def incompatible_argument(
        self,
        n: int,
        m: int,
        callee: CallableType,
        arg_type: Type,
        arg_kind: ArgKind,
        object_type: Type | None,
        context: Context,
        outer_context: Context,
    ) -> ErrorCode | None:
        """Report an error about an incompatible argument type.

        The argument type is arg_type, argument number is n and the
        callee type is 'callee'. If the callee represents a method
        that corresponds to an operator, use the corresponding
        operator name in the messages.

        Return the error code that used for the argument (multiple error
        codes are possible).
        """
        arg_type = get_proper_type(arg_type)

        target = ""
        callee_name = callable_name(callee)
        if callee_name is not None:
            name = callee_name
            if callee.bound_args and callee.bound_args[0] is not None:
                base = format_type(callee.bound_args[0], self.options)
            else:
                base = extract_type(name)

            for method, op in op_methods_to_symbols.items():
                for variant in method, "__r" + method[2:]:
                    # FIX: do not rely on textual formatting
                    if name.startswith(f'"{variant}" of'):
                        if op == "in" or variant != method:
                            # Reversed order of base/argument.
                            self.unsupported_operand_types(
                                op, arg_type, base, context, code=codes.OPERATOR
                            )
                        else:
                            self.unsupported_operand_types(
                                op, base, arg_type, context, code=codes.OPERATOR
                            )
                        return codes.OPERATOR

            if name.startswith('"__getitem__" of'):
                self.invalid_index_type(
                    arg_type, callee.arg_types[n - 1], base, context, code=codes.INDEX
                )
                return codes.INDEX

            if name.startswith('"__setitem__" of'):
                if n == 1:
                    self.invalid_index_type(
                        arg_type, callee.arg_types[n - 1], base, context, code=codes.INDEX
                    )
                    return codes.INDEX
                else:
                    arg_type_str, callee_type_str = format_type_distinctly(
                        arg_type, callee.arg_types[n - 1], options=self.options
                    )
                    info = (
                        f" (expression has type {arg_type_str}, target has type {callee_type_str})"
                    )
                    error_msg = (
                        message_registry.INCOMPATIBLE_TYPES_IN_ASSIGNMENT.with_additional_msg(info)
                    )
                    self.fail(error_msg.value, context, code=error_msg.code)
                    return error_msg.code

            target = f"to {name} "

        msg = ""
        code = codes.MISC
        notes: list[str] = []
        if callee_name == "<list>":
            name = callee_name[1:-1]
            n -= 1
            actual_type_str, expected_type_str = format_type_distinctly(
                arg_type, callee.arg_types[0], options=self.options
            )
            msg = "{} item {} has incompatible type {}; expected {}".format(
                name.title(), n, actual_type_str, expected_type_str
            )
            code = codes.LIST_ITEM
        elif callee_name == "<dict>" and isinstance(
            get_proper_type(callee.arg_types[n - 1]), TupleType
        ):
            name = callee_name[1:-1]
            n -= 1
            key_type, value_type = cast(TupleType, arg_type).items
            expected_key_type, expected_value_type = cast(TupleType, callee.arg_types[n]).items

            # don't increase verbosity unless there is need to do so
            if is_subtype(key_type, expected_key_type):
                key_type_str = format_type(key_type, self.options)
                expected_key_type_str = format_type(expected_key_type, self.options)
            else:
                key_type_str, expected_key_type_str = format_type_distinctly(
                    key_type, expected_key_type, options=self.options
                )
            if is_subtype(value_type, expected_value_type):
                value_type_str = format_type(value_type, self.options)
                expected_value_type_str = format_type(expected_value_type, self.options)
            else:
                value_type_str, expected_value_type_str = format_type_distinctly(
                    value_type, expected_value_type, options=self.options
                )

            msg = "{} entry {} has incompatible type {}: {}; expected {}: {}".format(
                name.title(),
                n,
                key_type_str,
                value_type_str,
                expected_key_type_str,
                expected_value_type_str,
            )
            code = codes.DICT_ITEM
        elif callee_name == "<dict>":
            value_type_str, expected_value_type_str = format_type_distinctly(
                arg_type, callee.arg_types[n - 1], options=self.options
            )
            msg = "Unpacked dict entry {} has incompatible type {}; expected {}".format(
                n - 1, value_type_str, expected_value_type_str
            )
            code = codes.DICT_ITEM
        elif callee_name == "<list-comprehension>":
            actual_type_str, expected_type_str = map(
                strip_quotes,
                format_type_distinctly(arg_type, callee.arg_types[0], options=self.options),
            )
            msg = "List comprehension has incompatible type List[{}]; expected List[{}]".format(
                actual_type_str, expected_type_str
            )
        elif callee_name == "<set-comprehension>":
            actual_type_str, expected_type_str = map(
                strip_quotes,
                format_type_distinctly(arg_type, callee.arg_types[0], options=self.options),
            )
            msg = "Set comprehension has incompatible type Set[{}]; expected Set[{}]".format(
                actual_type_str, expected_type_str
            )
        elif callee_name == "<dictionary-comprehension>":
            actual_type_str, expected_type_str = format_type_distinctly(
                arg_type, callee.arg_types[n - 1], options=self.options
            )
            msg = (
                "{} expression in dictionary comprehension has incompatible type {}; "
                "expected type {}"
            ).format("Key" if n == 1 else "Value", actual_type_str, expected_type_str)
        elif callee_name == "<generator>":
            actual_type_str, expected_type_str = format_type_distinctly(
                arg_type, callee.arg_types[0], options=self.options
            )
            msg = "Generator has incompatible item type {}; expected {}".format(
                actual_type_str, expected_type_str
            )
        else:
            if self.prefer_simple_messages():
                msg = "Argument has incompatible type"
            else:
                try:
                    expected_type = callee.arg_types[m - 1]
                except IndexError:  # Varargs callees
                    expected_type = callee.arg_types[-1]
                arg_type_str, expected_type_str = format_type_distinctly(
                    arg_type, expected_type, bare=True, options=self.options
                )
                if arg_kind == ARG_STAR:
                    arg_type_str = "*" + arg_type_str
                elif arg_kind == ARG_STAR2:
                    arg_type_str = "**" + arg_type_str

                # For function calls with keyword arguments, display the argument name rather
                # than the number.
                arg_label = str(n)
                if isinstance(outer_context, CallExpr) and len(outer_context.arg_names) >= n:
                    arg_name = outer_context.arg_names[n - 1]
                    if arg_name is not None:
                        arg_label = f'"{arg_name}"'
                if (
                    arg_kind == ARG_STAR2
                    and isinstance(arg_type, TypedDictType)
                    and m <= len(callee.arg_names)
                    and callee.arg_names[m - 1] is not None
                    and callee.arg_kinds[m - 1] != ARG_STAR2
                ):
                    arg_name = callee.arg_names[m - 1]
                    assert arg_name is not None
                    arg_type_str, expected_type_str = format_type_distinctly(
                        arg_type.items[arg_name], expected_type, bare=True, options=self.options
                    )
                    arg_label = f'"{arg_name}"'
                if isinstance(outer_context, IndexExpr) and isinstance(
                    outer_context.index, StrExpr
                ):
                    msg = 'Value of "{}" has incompatible type {}; expected {}'.format(
                        outer_context.index.value,
                        quote_type_string(arg_type_str),
                        quote_type_string(expected_type_str),
                    )
                else:
                    msg = "Argument {} {}has incompatible type {}; expected {}".format(
                        arg_label,
                        target,
                        quote_type_string(arg_type_str),
                        quote_type_string(expected_type_str),
                    )
                expected_type = get_proper_type(expected_type)
                if isinstance(expected_type, UnionType):
                    expected_types = list(expected_type.items)
                else:
                    expected_types = [expected_type]
                for type in get_proper_types(expected_types):
                    if isinstance(arg_type, Instance) and isinstance(type, Instance):
                        notes = append_invariance_notes(notes, arg_type, type)
                        notes = append_numbers_notes(notes, arg_type, type)
            object_type = get_proper_type(object_type)
            if isinstance(object_type, TypedDictType):
                code = codes.TYPEDDICT_ITEM
            else:
                code = codes.ARG_TYPE
        self.fail(msg, context, code=code)
        if notes:
            for note_msg in notes:
                self.note(note_msg, context, code=code)
        return code

    def incompatible_argument_note(
        self,
        original_caller_type: ProperType,
        callee_type: ProperType,
        context: Context,
        code: ErrorCode | None,
    ) -> None:
        if self.prefer_simple_messages():
            return
        if isinstance(
            original_caller_type, (Instance, TupleType, TypedDictType, TypeType, CallableType)
        ):
            if isinstance(callee_type, Instance) and callee_type.type.is_protocol:
                self.report_protocol_problems(
                    original_caller_type, callee_type, context, code=code
                )
            if (
                isinstance(callee_type, TypeType)
                and isinstance(callee_type.item, Instance)
                and isinstance(original_caller_type, CallableType)
                and callee_type.item.type.is_protocol
            ):
                proper_ret_type = get_proper_type(original_caller_type.ret_type)
                if isinstance(proper_ret_type, Instance):
                    self.report_protocol_problems(
                        proper_ret_type, callee_type.item, context, code=code
                    )
            if isinstance(callee_type, UnionType):
                for item in callee_type.items:
                    item = get_proper_type(item)
                    if isinstance(item, Instance) and item.type.is_protocol:
                        self.report_protocol_problems(
                            original_caller_type, item, context, code=code
                        )
        if isinstance(callee_type, CallableType) and isinstance(original_caller_type, Instance):
            call = find_member(
                "__call__", original_caller_type, original_caller_type, is_operator=True
            )
            if call:
                self.note_call(original_caller_type, call, context, code=code)
        if isinstance(callee_type, Instance) and callee_type.type.is_protocol:
            call = find_member("__call__", callee_type, callee_type, is_operator=True)
            if call:
                self.note_call(callee_type, call, context, code=code)
        self.maybe_note_concatenate_pos_args(original_caller_type, callee_type, context, code)

    def maybe_note_concatenate_pos_args(
        self,
        original_caller_type: ProperType,
        callee_type: ProperType,
        context: Context,
        code: ErrorCode | None = None,
    ) -> None:
        # pos-only vs positional can be confusing, with Concatenate
        if (
            isinstance(callee_type, CallableType)
            and isinstance(original_caller_type, CallableType)
            and (original_caller_type.from_concatenate or callee_type.from_concatenate)
        ):
            names: list[str] = []
            for c, o in zip(
                callee_type.formal_arguments(), original_caller_type.formal_arguments()
            ):
                if None in (c.pos, o.pos):
                    # non-positional
                    continue
                if c.name != o.name and c.name is None and o.name is not None:
                    names.append(o.name)

            if names:
                missing_arguments = '"' + '", "'.join(names) + '"'
                self.note(
                    f'This is likely because "{original_caller_type.name}" has named arguments: '
                    f"{missing_arguments}. Consider marking them positional-only",
                    context,
                    code=code,
                )

    def invalid_index_type(
        self,
        index_type: Type,
        expected_type: Type,
        base_str: str,
        context: Context,
        *,
        code: ErrorCode,
    ) -> None:
        index_str, expected_str = format_type_distinctly(
            index_type, expected_type, options=self.options
        )
        self.fail(
            "Invalid index type {} for {}; expected type {}".format(
                index_str, base_str, expected_str
            ),
            context,
            code=code,
        )

    def readonly_keys_mutated(self, keys: set[str], context: Context) -> None:
        if len(keys) == 1:
            suffix = "is"
        else:
            suffix = "are"
        self.fail(
            "ReadOnly {} TypedDict {} mutated".format(format_key_list(sorted(keys)), suffix),
            code=codes.TYPEDDICT_READONLY_MUTATED,
            context=context,
        )

    def too_few_arguments(
        self, callee: CallableType, context: Context, argument_names: Sequence[str | None] | None
    ) -> None:
        if self.prefer_simple_messages():
            msg = "Too few arguments"
        elif argument_names is not None:
            num_positional_args = sum(k is None for k in argument_names)
            arguments_left = callee.arg_names[num_positional_args : callee.min_args]
            diff = [k for k in arguments_left if k not in argument_names]
            if len(diff) == 1:
                msg = "Missing positional argument"
            else:
                msg = "Missing positional arguments"
            callee_name = callable_name(callee)
            if callee_name is not None and diff and all(d is not None for d in diff):
                args = '", "'.join(cast(list[str], diff))
                msg += f' "{args}" in call to {callee_name}'
            else:
                msg = "Too few arguments" + for_function(callee)

        else:
            msg = "Too few arguments" + for_function(callee)
        self.fail(msg, context, code=codes.CALL_ARG)

    def missing_named_argument(self, callee: CallableType, context: Context, name: str) -> None:
        msg = f'Missing named argument "{name}"' + for_function(callee)
        self.fail(msg, context, code=codes.CALL_ARG)

    def too_many_arguments(self, callee: CallableType, context: Context) -> None:
        if self.prefer_simple_messages():
            msg = "Too many arguments"
        else:
            msg = "Too many arguments" + for_function(callee)
        self.fail(msg, context, code=codes.CALL_ARG)
        self.maybe_note_about_special_args(callee, context)

    def too_many_arguments_from_typed_dict(
        self, callee: CallableType, arg_type: TypedDictType, context: Context
    ) -> None:
        # Try to determine the name of the extra argument.
        for key in arg_type.items:
            if key not in callee.arg_names:
                msg = f'Extra argument "{key}" from **args' + for_function(callee)
                break
        else:
            self.too_many_arguments(callee, context)
            return
        self.fail(msg, context)

    def too_many_positional_arguments(self, callee: CallableType, context: Context) -> None:
        if self.prefer_simple_messages():
            msg = "Too many positional arguments"
        else:
            msg = "Too many positional arguments" + for_function(callee)
        self.fail(msg, context)
        self.maybe_note_about_special_args(callee, context)

    def maybe_note_about_special_args(self, callee: CallableType, context: Context) -> None:
        if self.prefer_simple_messages():
            return
        # https://github.com/python/mypy/issues/11309
        first_arg = callee.def_extras.get("first_arg")
        if first_arg and first_arg not in {"self", "cls", "mcs"}:
            self.note(
                "Looks like the first special argument in a method "
                'is not named "self", "cls", or "mcs", '
                "maybe it is missing?",
                context,
            )

    def unexpected_keyword_argument_for_function(
        self, for_func: str, name: str, context: Context, *, matches: list[str] | None = None
    ) -> None:
        msg = f'Unexpected keyword argument "{name}"' + for_func
        if matches:
            msg += f"; did you mean {pretty_seq(matches, 'or')}?"
        self.fail(msg, context, code=codes.CALL_ARG)

    def unexpected_keyword_argument(
        self, callee: CallableType, name: str, arg_type: Type, context: Context
    ) -> None:
        # Suggest intended keyword, look for type match else fallback on any match.
        matching_type_args = []
        not_matching_type_args = []
        for i, kwarg_type in enumerate(callee.arg_types):
            callee_arg_name = callee.arg_names[i]
            if callee_arg_name is not None and callee.arg_kinds[i] != ARG_STAR:
                if is_subtype(arg_type, kwarg_type):
                    matching_type_args.append(callee_arg_name)
                else:
                    not_matching_type_args.append(callee_arg_name)
        matches = best_matches(name, matching_type_args, n=3)
        if not matches:
            matches = best_matches(name, not_matching_type_args, n=3)
        self.unexpected_keyword_argument_for_function(
            for_function(callee), name, context, matches=matches
        )
        module = find_defining_module(self.modules, callee)
        if module:
            assert callee.definition is not None
            fname = callable_name(callee)
            if not fname:  # an alias to function with a different name
                fname = "Called function"
            self.note(
                f"{fname} defined here",
                callee.definition,
                file=module.path,
                origin=context,
                code=codes.CALL_ARG,
            )

    def duplicate_argument_value(self, callee: CallableType, index: int, context: Context) -> None:
        self.fail(
            '{} gets multiple values for keyword argument "{}"'.format(
                callable_name(callee) or "Function", callee.arg_names[index]
            ),
            context,
        )

    def does_not_return_value(self, callee_type: Type | None, context: Context) -> None:
        """Report an error about use of an unusable type."""
        callee_type = get_proper_type(callee_type)
        callee_name = callable_name(callee_type) if isinstance(callee_type, FunctionLike) else None
        name = callee_name or "Function"
        message = f"{name} does not return a value (it only ever returns None)"
        self.fail(message, context, code=codes.FUNC_RETURNS_VALUE)

    def deleted_as_rvalue(self, typ: DeletedType, context: Context) -> None:
        """Report an error about using an deleted type as an rvalue."""
        if typ.source is None:
            s = ""
        else:
            s = f' "{typ.source}"'
        self.fail(f"Trying to read deleted variable{s}", context)

    def deleted_as_lvalue(self, typ: DeletedType, context: Context) -> None:
        """Report an error about using an deleted type as an lvalue.

        Currently, this only occurs when trying to assign to an
        exception variable outside the local except: blocks.
        """
        if typ.source is None:
            s = ""
        else:
            s = f' "{typ.source}"'
        self.fail(f"Assignment to variable{s} outside except: block", context)

    def no_variant_matches_arguments(
        self,
        overload: Overloaded,
        arg_types: list[Type],
        context: Context,
        *,
        code: ErrorCode | None = None,
    ) -> None:
        code = code or codes.CALL_OVERLOAD
        name = callable_name(overload)
        if name:
            name_str = f" of {name}"
        else:
            name_str = ""
        arg_types_str = ", ".join(format_type(arg, self.options) for arg in arg_types)
        num_args = len(arg_types)
        if num_args == 0:
            self.fail(
                f"All overload variants{name_str} require at least one argument",
                context,
                code=code,
            )
        elif num_args == 1:
            self.fail(
                f"No overload variant{name_str} matches argument type {arg_types_str}",
                context,
                code=code,
            )
        else:
            self.fail(
                f"No overload variant{name_str} matches argument types {arg_types_str}",
                context,
                code=code,
            )

        self.note(f"Possible overload variant{plural_s(len(overload.items))}:", context, code=code)
        for item in overload.items:
            self.note(pretty_callable(item, self.options), context, offset=4, code=code)

    def wrong_number_values_to_unpack(
        self, provided: int, expected: int, context: Context
    ) -> None:
        if provided < expected:
            if provided == 1:
                self.fail(f"Need more than 1 value to unpack ({expected} expected)", context)
            else:
                self.fail(
                    f"Need more than {provided} values to unpack ({expected} expected)", context
                )
        elif provided > expected:
            self.fail(
                f"Too many values to unpack ({expected} expected, {provided} provided)", context
            )

    def unpacking_strings_disallowed(self, context: Context) -> None:
        self.fail("Unpacking a string is disallowed", context)

    def type_not_iterable(self, type: Type, context: Context) -> None:
        self.fail(f"{format_type(type, self.options)} object is not iterable", context)

    def possible_missing_await(self, context: Context, code: ErrorCode | None) -> None:
        self.note('Maybe you forgot to use "await"?', context, code=code)

    def incompatible_operator_assignment(self, op: str, context: Context) -> None:
        self.fail(f"Result type of {op} incompatible in assignment", context)

    def overload_signature_incompatible_with_supertype(
        self, name: str, name_in_super: str, supertype: str, context: Context
    ) -> None:
        target = self.override_target(name, name_in_super, supertype)
        self.fail(
            f'Signature of "{name}" incompatible with {target}', context, code=codes.OVERRIDE
        )

        note_template = 'Overload variants must be defined in the same order as they are in "{}"'
        self.note(note_template.format(supertype), context, code=codes.OVERRIDE)

    def signature_incompatible_with_supertype(
        self,
        name: str,
        name_in_super: str,
        supertype: str,
        context: Context,
        *,
        original: ProperType,
        override: ProperType,
    ) -> None:
        code = codes.OVERRIDE
        target = self.override_target(name, name_in_super, supertype)
        self.fail(f'Signature of "{name}" incompatible with {target}', context, code=code)

        original_str, override_str = format_type_distinctly(
            original, override, options=self.options, bare=True
        )

        INCLUDE_DECORATOR = True  # Include @classmethod and @staticmethod decorators, if any
        ALLOW_DUPS = True  # Allow duplicate notes, needed when signatures are duplicates
        ALIGN_OFFSET = 1  # One space, to account for the difference between error and note
        OFFSET = 4  # Four spaces, so that notes will look like this:
        # error: Signature of "f" incompatible with supertype "A"
        # note:      Superclass:
        # note:          def f(self) -> str
        # note:      Subclass:
        # note:          def f(self, x: str) -> None
        self.note(
            "Superclass:", context, offset=ALIGN_OFFSET + OFFSET, allow_dups=ALLOW_DUPS, code=code
        )
        if isinstance(original, (CallableType, Overloaded)):
            self.pretty_callable_or_overload(
                original,
                context,
                offset=ALIGN_OFFSET + 2 * OFFSET,
                add_class_or_static_decorator=INCLUDE_DECORATOR,
                allow_dups=ALLOW_DUPS,
                code=code,
            )
        else:
            self.note(
                original_str,
                context,
                offset=ALIGN_OFFSET + 2 * OFFSET,
                allow_dups=ALLOW_DUPS,
                code=code,
            )

        self.note(
            "Subclass:", context, offset=ALIGN_OFFSET + OFFSET, allow_dups=ALLOW_DUPS, code=code
        )
        if isinstance(override, (CallableType, Overloaded)):
            self.pretty_callable_or_overload(
                override,
                context,
                offset=ALIGN_OFFSET + 2 * OFFSET,
                add_class_or_static_decorator=INCLUDE_DECORATOR,
                allow_dups=ALLOW_DUPS,
                code=code,
            )
        else:
            self.note(
                override_str,
                context,
                offset=ALIGN_OFFSET + 2 * OFFSET,
                allow_dups=ALLOW_DUPS,
                code=code,
            )

    def pretty_callable_or_overload(
        self,
        tp: CallableType | Overloaded,
        context: Context,
        *,
        offset: int = 0,
        add_class_or_static_decorator: bool = False,
        allow_dups: bool = False,
        code: ErrorCode | None = None,
    ) -> None:
        if isinstance(tp, CallableType):
            if add_class_or_static_decorator:
                decorator = pretty_class_or_static_decorator(tp)
                if decorator is not None:
                    self.note(decorator, context, offset=offset, allow_dups=allow_dups, code=code)
            self.note(
                pretty_callable(tp, self.options),
                context,
                offset=offset,
                allow_dups=allow_dups,
                code=code,
            )
        elif isinstance(tp, Overloaded):
            self.pretty_overload(
                tp,
                context,
                offset,
                add_class_or_static_decorator=add_class_or_static_decorator,
                allow_dups=allow_dups,
                code=code,
            )

    def argument_incompatible_with_supertype(
        self,
        arg_num: int,
        name: str,
        type_name: str | None,
        name_in_supertype: str,
        arg_type_in_supertype: Type,
        supertype: str,
        context: Context,
        secondary_context: Context,
    ) -> None:
        target = self.override_target(name, name_in_supertype, supertype)
        arg_type_in_supertype_f = format_type_bare(arg_type_in_supertype, self.options)
        self.fail(
            'Argument {} of "{}" is incompatible with {}; '
            'supertype defines the argument type as "{}"'.format(
                arg_num, name, target, arg_type_in_supertype_f
            ),
            context,
            code=codes.OVERRIDE,
            secondary_context=secondary_context,
        )
        if name != "__post_init__":
            # `__post_init__` is special, it can be incompatible by design.
            # So, this note is misleading.
            self.note(
                "This violates the Liskov substitution principle",
                context,
                code=codes.OVERRIDE,
                secondary_context=secondary_context,
            )
            self.note(
                "See https://mypy.readthedocs.io/en/stable/common_issues.html#incompatible-overrides",
                context,
                code=codes.OVERRIDE,
                secondary_context=secondary_context,
            )

        if name == "__eq__" and type_name:
            multiline_msg = self.comparison_method_example_msg(class_name=type_name)
            self.note_multiline(
                multiline_msg, context, code=codes.OVERRIDE, secondary_context=secondary_context
            )

    def comparison_method_example_msg(self, class_name: str) -> str:
        return dedent(
            """\
        It is recommended for "__eq__" to work with arbitrary objects, for example:
            def __eq__(self, other: object) -> bool:
                if not isinstance(other, {class_name}):
                    return NotImplemented
                return <logic to compare two {class_name} instances>
        """.format(
                class_name=class_name
            )
        )

    def return_type_incompatible_with_supertype(
        self,
        name: str,
        name_in_supertype: str,
        supertype: str,
        original: Type,
        override: Type,
        context: Context,
    ) -> None:
        target = self.override_target(name, name_in_supertype, supertype)
        override_str, original_str = format_type_distinctly(
            override, original, options=self.options
        )
        self.fail(
            'Return type {} of "{}" incompatible with return type {} in {}'.format(
                override_str, name, original_str, target
            ),
            context,
            code=codes.OVERRIDE,
        )

        original = get_proper_type(original)
        override = get_proper_type(override)
        if (
            isinstance(original, Instance)
            and isinstance(override, Instance)
            and override.type.fullname == "typing.AsyncIterator"
            and original.type.fullname == "typing.Coroutine"
            and len(original.args) == 3
            and original.args[2] == override
        ):
            self.note(f'Consider declaring "{name}" in {target} without "async"', context)
            self.note(
                "See https://mypy.readthedocs.io/en/stable/more_types.html#asynchronous-iterators",
                context,
            )

    def override_target(self, name: str, name_in_super: str, supertype: str) -> str:
        target = f'supertype "{supertype}"'
        if name_in_super != name:
            target = f'"{name_in_super}" of {target}'
        return target

    def incompatible_type_application(
        self, min_arg_count: int, max_arg_count: int, actual_arg_count: int, context: Context
    ) -> None:
        if max_arg_count == 0:
            self.fail("Type application targets a non-generic function or class", context)
            return

        if min_arg_count == max_arg_count:
            s = f"{max_arg_count} expected"
        else:
            s = f"expected between {min_arg_count} and {max_arg_count}"

        if actual_arg_count > max_arg_count:
            self.fail(f"Type application has too many types ({s})", context)
        else:
            self.fail(f"Type application has too few types ({s})", context)

    def could_not_infer_type_arguments(
        self, callee_type: CallableType, n: int, context: Context
    ) -> None:
        callee_name = callable_name(callee_type)
        if callee_name is not None and n > 0:
            self.fail(f"Cannot infer type argument {n} of {callee_name}", context)
            if callee_name == "<dict>":
                # Invariance in key type causes more of these errors than we would want.
                self.note(
                    "Try assigning the literal to a variable annotated as dict[<key>, <val>]",
                    context,
                )
        else:
            self.fail("Cannot infer function type argument", context)

    def invalid_var_arg(self, typ: Type, context: Context) -> None:
        self.fail("Expected iterable as variadic argument", context)

    def invalid_keyword_var_arg(self, typ: Type, is_mapping: bool, context: Context) -> None:
        typ = get_proper_type(typ)
        if isinstance(typ, Instance) and is_mapping:
            self.fail("Keywords must be strings", context)
        else:
            self.fail(
                f"Argument after ** must be a mapping, not {format_type(typ, self.options)}",
                context,
                code=codes.ARG_TYPE,
            )

    def undefined_in_superclass(self, member: str, context: Context) -> None:
        self.fail(f'"{member}" undefined in superclass', context)

    def variable_may_be_undefined(self, name: str, context: Context) -> None:
        self.fail(f'Name "{name}" may be undefined', context, code=codes.POSSIBLY_UNDEFINED)

    def var_used_before_def(self, name: str, context: Context) -> None:
        self.fail(f'Name "{name}" is used before definition', context, code=codes.USED_BEFORE_DEF)

    def first_argument_for_super_must_be_type(self, actual: Type, context: Context) -> None:
        actual = get_proper_type(actual)
        if isinstance(actual, Instance):
            # Don't include type of instance, because it can look confusingly like a type
            # object.
            type_str = "a non-type instance"
        else:
            type_str = format_type(actual, self.options)
        self.fail(
            f'Argument 1 for "super" must be a type object; got {type_str}',
            context,
            code=codes.ARG_TYPE,
        )

    def unsafe_super(self, method: str, cls: str, ctx: Context) -> None:
        self.fail(
            f'Call to abstract method "{method}" of "{cls}" with trivial body via super() is unsafe',
            ctx,
            code=codes.SAFE_SUPER,
        )

    def too_few_string_formatting_arguments(self, context: Context) -> None:
        self.fail("Not enough arguments for format string", context, code=codes.STRING_FORMATTING)

    def too_many_string_formatting_arguments(self, context: Context) -> None:
        self.fail(
            "Not all arguments converted during string formatting",
            context,
            code=codes.STRING_FORMATTING,
        )

    def unsupported_placeholder(self, placeholder: str, context: Context) -> None:
        self.fail(
            f'Unsupported format character "{placeholder}"', context, code=codes.STRING_FORMATTING
        )

    def string_interpolation_with_star_and_key(self, context: Context) -> None:
        self.fail(
            "String interpolation contains both stars and mapping keys",
            context,
            code=codes.STRING_FORMATTING,
        )

    def requires_int_or_single_byte(self, context: Context, format_call: bool = False) -> None:
        self.fail(
            '"{}c" requires an integer in range(256) or a single byte'.format(
                ":" if format_call else "%"
            ),
            context,
            code=codes.STRING_FORMATTING,
        )

    def requires_int_or_char(self, context: Context, format_call: bool = False) -> None:
        self.fail(
            '"{}c" requires int or char'.format(":" if format_call else "%"),
            context,
            code=codes.STRING_FORMATTING,
        )

    def key_not_in_mapping(self, key: str, context: Context) -> None:
        self.fail(f'Key "{key}" not found in mapping', context, code=codes.STRING_FORMATTING)

    def string_interpolation_mixing_key_and_non_keys(self, context: Context) -> None:
        self.fail(
            "String interpolation mixes specifier with and without mapping keys",
            context,
            code=codes.STRING_FORMATTING,
        )

    def cannot_determine_type(self, name: str, context: Context) -> None:
        self.fail(f'Cannot determine type of "{name}"', context, code=codes.HAS_TYPE)

    def cannot_determine_type_in_base(self, name: str, base: str, context: Context) -> None:
        self.fail(f'Cannot determine type of "{name}" in base class "{base}"', context)

    def no_formal_self(self, name: str, item: CallableType, context: Context) -> None:
        type = format_type(item, self.options)
        self.fail(
            f'Attribute function "{name}" with type {type} does not accept self argument', context
        )

    def incompatible_self_argument(
        self, name: str, arg: Type, sig: CallableType, is_classmethod: bool, context: Context
    ) -> None:
        kind = "class attribute function" if is_classmethod else "attribute function"
        arg_type = format_type(arg, self.options)
        sig_type = format_type(sig, self.options)
        self.fail(
            f'Invalid self argument {arg_type} to {kind} "{name}" with type {sig_type}', context
        )

    def incompatible_conditional_function_def(
        self, defn: FuncDef, old_type: FunctionLike, new_type: FunctionLike
    ) -> None:
        self.fail("All conditional function variants must have identical signatures", defn)
        if isinstance(old_type, (CallableType, Overloaded)) and isinstance(
            new_type, (CallableType, Overloaded)
        ):
            self.note("Original:", defn)
            self.pretty_callable_or_overload(old_type, defn, offset=4)
            self.note("Redefinition:", defn)
            self.pretty_callable_or_overload(new_type, defn, offset=4)

    def cannot_instantiate_abstract_class(
        self, class_name: str, abstract_attributes: dict[str, bool], context: Context
    ) -> None:
        attrs = format_string_list([f'"{a}"' for a in abstract_attributes])
        self.fail(
            f'Cannot instantiate abstract class "{class_name}" with abstract '
            f"attribute{plural_s(abstract_attributes)} {attrs}",
            context,
            code=codes.ABSTRACT,
        )
        attrs_with_none = [
            f'"{a}"'
            for a, implicit_and_can_return_none in abstract_attributes.items()
            if implicit_and_can_return_none
        ]
        if not attrs_with_none:
            return
        if len(attrs_with_none) == 1:
            note = (
                f"{attrs_with_none[0]} is implicitly abstract because it has an empty function "
                "body. If it is not meant to be abstract, explicitly `return` or `return None`."
            )
        else:
            note = (
                "The following methods were marked implicitly abstract because they have empty "
                f"function bodies: {format_string_list(attrs_with_none)}. "
                "If they are not meant to be abstract, explicitly `return` or `return None`."
            )
        self.note(note, context, code=codes.ABSTRACT)

    def base_class_definitions_incompatible(
        self, name: str, base1: TypeInfo, base2: TypeInfo, context: Context
    ) -> None:
        self.fail(
            'Definition of "{}" in base class "{}" is incompatible '
            'with definition in base class "{}"'.format(name, base1.name, base2.name),
            context,
        )

    def cant_assign_to_method(self, context: Context) -> None:
        self.fail(message_registry.CANNOT_ASSIGN_TO_METHOD, context, code=codes.METHOD_ASSIGN)

    def cant_assign_to_classvar(self, name: str, context: Context) -> None:
        self.fail(f'Cannot assign to class variable "{name}" via instance', context)

    def no_overridable_method(self, name: str, context: Context) -> None:
        self.fail(
            f'Method "{name}" is marked as an override, '
            "but no base method was found with this name",
            context,
        )

    def explicit_override_decorator_missing(
        self, name: str, base_name: str, context: Context
    ) -> None:
        self.fail(
            f'Method "{name}" is not using @override '
            f'but is overriding a method in class "{base_name}"',
            context,
            code=codes.EXPLICIT_OVERRIDE_REQUIRED,
        )

    def final_cant_override_writable(self, name: str, ctx: Context) -> None:
        self.fail(f'Cannot override writable attribute "{name}" with a final one', ctx)

    def cant_override_final(self, name: str, base_name: str, ctx: Context) -> None:
        self.fail(
            (
                f'Cannot override final attribute "{name}" '
                f'(previously declared in base class "{base_name}")'
            ),
            ctx,
        )

    def cant_assign_to_final(self, name: str, attr_assign: bool, ctx: Context) -> None:
        """Warn about a prohibited assignment to a final attribute.

        Pass `attr_assign=True` if the assignment assigns to an attribute.
        """
        kind = "attribute" if attr_assign else "name"
        self.fail(f'Cannot assign to final {kind} "{unmangle(name)}"', ctx)

    def protocol_members_cant_be_final(self, ctx: Context) -> None:
        self.fail("Protocol member cannot be final", ctx)

    def final_without_value(self, ctx: Context) -> None:
        self.fail("Final name must be initialized with a value", ctx)

    def read_only_property(self, name: str, type: TypeInfo, context: Context) -> None:
        self.fail(f'Property "{name}" defined in "{type.name}" is read-only', context)

    def incompatible_typevar_value(
        self, callee: CallableType, typ: Type, typevar_name: str, context: Context
    ) -> None:
        self.fail(
            message_registry.INCOMPATIBLE_TYPEVAR_VALUE.format(
                typevar_name, callable_name(callee) or "function", format_type(typ, self.options)
            ),
            context,
            code=codes.TYPE_VAR,
        )

    def dangerous_comparison(self, left: Type, right: Type, kind: str, ctx: Context) -> None:
        left_str = "element" if kind == "container" else "left operand"
        right_str = "container item" if kind == "container" else "right operand"
        message = "Non-overlapping {} check ({} type: {}, {} type: {})"
        left_typ, right_typ = format_type_distinctly(left, right, options=self.options)
        self.fail(
            message.format(kind, left_str, left_typ, right_str, right_typ),
            ctx,
            code=codes.COMPARISON_OVERLAP,
        )

    def overload_inconsistently_applies_decorator(self, decorator: str, context: Context) -> None:
        self.fail(
            f'Overload does not consistently use the "@{decorator}" '
            + "decorator on all function signatures.",
            context,
        )

    def overloaded_signatures_overlap(
        self, index1: int, index2: int, flip_note: bool, context: Context
    ) -> None:
        self.fail(
            "Overloaded function signatures {} and {} overlap with "
            "incompatible return types".format(index1, index2),
            context,
            code=codes.OVERLOAD_OVERLAP,
        )
        if flip_note:
            self.note(
                "Flipping the order of overloads will fix this error",
                context,
                code=codes.OVERLOAD_OVERLAP,
            )

    def overloaded_signature_will_never_match(
        self, index1: int, index2: int, context: Context
    ) -> None:
        self.fail(
            "Overloaded function signature {index2} will never be matched: "
            "signature {index1}'s parameter type(s) are the same or broader".format(
                index1=index1, index2=index2
            ),
            context,
            code=codes.OVERLOAD_CANNOT_MATCH,
        )

    def overloaded_signatures_typevar_specific(self, index: int, context: Context) -> None:
        self.fail(
            f"Overloaded function implementation cannot satisfy signature {index} "
            + "due to inconsistencies in how they use type variables",
            context,
        )

    def overloaded_signatures_arg_specific(self, index: int, context: Context) -> None:
        self.fail(
            (
                f"Overloaded function implementation does not accept all possible arguments "
                f"of signature {index}"
            ),
            context,
        )

    def overloaded_signatures_ret_specific(self, index: int, context: Context) -> None:
        self.fail(
            f"Overloaded function implementation cannot produce return type of signature {index}",
            context,
        )

    def warn_both_operands_are_from_unions(self, context: Context) -> None:
        self.note("Both left and right operands are unions", context, code=codes.OPERATOR)

    def warn_operand_was_from_union(self, side: str, original: Type, context: Context) -> None:
        self.note(
            f"{side} operand is of type {format_type(original, self.options)}",
            context,
            code=codes.OPERATOR,
        )

    def operator_method_signatures_overlap(
        self,
        reverse_class: TypeInfo,
        reverse_method: str,
        forward_class: Type,
        forward_method: str,
        context: Context,
    ) -> None:
        self.fail(
            'Signatures of "{}" of "{}" and "{}" of {} are unsafely overlapping'.format(
                reverse_method,
                reverse_class.name,
                forward_method,
                format_type(forward_class, self.options),
            ),
            context,
        )

    def forward_operator_not_callable(self, forward_method: str, context: Context) -> None:
        self.fail(f'Forward operator "{forward_method}" is not callable', context)

    def signatures_incompatible(self, method: str, other_method: str, context: Context) -> None:
        self.fail(f'Signatures of "{method}" and "{other_method}" are incompatible', context)

    def yield_from_invalid_operand_type(self, expr: Type, context: Context) -> Type:
        text = (
            format_type(expr, self.options)
            if format_type(expr, self.options) != "object"
            else expr
        )
        self.fail(f'"yield from" can\'t be applied to {text}', context)
        return AnyType(TypeOfAny.from_error)

    def invalid_signature(self, func_type: Type, context: Context) -> None:
        self.fail(f"Invalid signature {format_type(func_type, self.options)}", context)

    def invalid_signature_for_special_method(
        self, func_type: Type, context: Context, method_name: str
    ) -> None:
        self.fail(
            f'Invalid signature {format_type(func_type, self.options)} for "{method_name}"',
            context,
        )

    def reveal_type(self, typ: Type, context: Context) -> None:
        visitor = TypeStrVisitor(options=self.options)
        self.note(f'Revealed type is "{typ.accept(visitor)}"', context)

    def reveal_locals(self, type_map: dict[str, Type | None], context: Context) -> None:
        # To ensure that the output is predictable on Python < 3.6,
        # use an ordered dictionary sorted by variable name
        sorted_locals = dict(sorted(type_map.items(), key=lambda t: t[0]))
        if sorted_locals:
            self.note("Revealed local types are:", context)
            for k, v in sorted_locals.items():
                visitor = TypeStrVisitor(options=self.options)
                self.note(f"    {k}: {v.accept(visitor) if v is not None else None}", context)
        else:
            self.note("There are no locals to reveal", context)

    def unsupported_type_type(self, item: Type, context: Context) -> None:
        self.fail(
            f'Cannot instantiate type "Type[{format_type_bare(item, self.options)}]"', context
        )

    def redundant_cast(self, typ: Type, context: Context) -> None:
        self.fail(
            f"Redundant cast to {format_type(typ, self.options)}",
            context,
            code=codes.REDUNDANT_CAST,
        )

    def assert_type_fail(self, source_type: Type, target_type: Type, context: Context) -> None:
        (source, target) = format_type_distinctly(source_type, target_type, options=self.options)
        self.fail(f"Expression is of type {source}, not {target}", context, code=codes.ASSERT_TYPE)

    def unimported_type_becomes_any(self, prefix: str, typ: Type, ctx: Context) -> None:
        self.fail(
            f"{prefix} becomes {format_type(typ, self.options)} due to an unfollowed import",
            ctx,
            code=codes.NO_ANY_UNIMPORTED,
        )

    def need_annotation_for_var(
        self, node: SymbolNode, context: Context, python_version: tuple[int, int] | None = None
    ) -> None:
        hint = ""
        pep604_supported = not python_version or python_version >= (3, 10)
        # type to recommend the user adds
        recommended_type = None
        # Only gives hint if it's a variable declaration and the partial type is a builtin type
        if python_version and isinstance(node, Var) and isinstance(node.type, PartialType):
            type_dec = "<type>"
            if not node.type.type:
                # partial None
                if pep604_supported:
                    recommended_type = f"{type_dec} | None"
                else:
                    recommended_type = f"Optional[{type_dec}]"
            elif node.type.type.fullname in reverse_builtin_aliases:
                # partial types other than partial None
                alias = reverse_builtin_aliases[node.type.type.fullname]
                alias = alias.split(".")[-1]
                if alias == "Dict":
                    type_dec = f"{type_dec}, {type_dec}"
                if self.options.use_lowercase_names():
                    alias = alias.lower()
                recommended_type = f"{alias}[{type_dec}]"
        if recommended_type is not None:
            hint = f' (hint: "{node.name}: {recommended_type} = ...")'

        self.fail(
            f'Need type annotation for "{unmangle(node.name)}"{hint}',
            context,
            code=codes.VAR_ANNOTATED,
        )

    def explicit_any(self, ctx: Context) -> None:
        self.fail('Explicit "Any" is not allowed', ctx, code=codes.EXPLICIT_ANY)

    def unsupported_target_for_star_typeddict(self, typ: Type, ctx: Context) -> None:
        self.fail(
            "Unsupported type {} for ** expansion in TypedDict".format(
                format_type(typ, self.options)
            ),
            ctx,
            code=codes.TYPEDDICT_ITEM,
        )

    def non_required_keys_absent_with_star(self, keys: list[str], ctx: Context) -> None:
        self.fail(
            "Non-required {} not explicitly found in any ** item".format(
                format_key_list(keys, short=True)
            ),
            ctx,
            code=codes.TYPEDDICT_ITEM,
        )

    def unexpected_typeddict_keys(
        self,
        typ: TypedDictType,
        expected_keys: list[str],
        actual_keys: list[str],
        context: Context,
    ) -> None:
        actual_set = set(actual_keys)
        expected_set = set(expected_keys)
        if not typ.is_anonymous():
            # Generate simpler messages for some common special cases.
            # Use list comprehension instead of set operations to preserve order.
            missing = [key for key in expected_keys if key not in actual_set]
            if missing:
                self.fail(
                    "Missing {} for TypedDict {}".format(
                        format_key_list(missing, short=True), format_type(typ, self.options)
                    ),
                    context,
                    code=codes.TYPEDDICT_ITEM,
                )
            extra = [key for key in actual_keys if key not in expected_set]
            if extra:
                self.fail(
                    "Extra {} for TypedDict {}".format(
                        format_key_list(extra, short=True), format_type(typ, self.options)
                    ),
                    context,
                    code=codes.TYPEDDICT_UNKNOWN_KEY,
                )
            if missing or extra:
                # No need to check for further errors
                return
        found = format_key_list(actual_keys, short=True)
        if not expected_keys:
            self.fail(f"Unexpected TypedDict {found}", context)
            return
        expected = format_key_list(expected_keys)
        if actual_keys and actual_set < expected_set:
            found = f"only {found}"
        self.fail(f"Expected {expected} but found {found}", context, code=codes.TYPEDDICT_ITEM)

    def typeddict_key_must_be_string_literal(self, typ: TypedDictType, context: Context) -> None:
        self.fail(
            "TypedDict key must be a string literal; expected one of {}".format(
                format_item_name_list(typ.items.keys())
            ),
            context,
            code=codes.LITERAL_REQ,
        )

    def typeddict_key_not_found(
        self, typ: TypedDictType, item_name: str, context: Context, setitem: bool = False
    ) -> None:
        """Handle error messages for TypedDicts that have unknown keys.

        Note, that we differentiate in between reading a value and setting a
        value.
        Setting a value on a TypedDict is an 'unknown-key' error, whereas
        reading it is the more serious/general 'item' error.
        """
        if typ.is_anonymous():
            self.fail(
                '"{}" is not a valid TypedDict key; expected one of {}'.format(
                    item_name, format_item_name_list(typ.items.keys())
                ),
                context,
            )
        else:
            err_code = codes.TYPEDDICT_UNKNOWN_KEY if setitem else codes.TYPEDDICT_ITEM
            self.fail(
                f'TypedDict {format_type(typ, self.options)} has no key "{item_name}"',
                context,
                code=err_code,
            )
            matches = best_matches(item_name, typ.items.keys(), n=3)
            if matches:
                self.note(
                    "Did you mean {}?".format(pretty_seq(matches, "or")), context, code=err_code
                )

    def typeddict_context_ambiguous(self, types: list[TypedDictType], context: Context) -> None:
        formatted_types = ", ".join(list(format_type_distinctly(*types, options=self.options)))
        self.fail(
            f"Type of TypedDict is ambiguous, none of ({formatted_types}) matches cleanly", context
        )

    def typeddict_key_cannot_be_deleted(
        self, typ: TypedDictType, item_name: str, context: Context
    ) -> None:
        if typ.is_anonymous():
            self.fail(f'TypedDict key "{item_name}" cannot be deleted', context)
        else:
            self.fail(
                f'Key "{item_name}" of TypedDict {format_type(typ, self.options)} cannot be deleted',
                context,
            )

    def typeddict_setdefault_arguments_inconsistent(
        self, default: Type, expected: Type, context: Context
    ) -> None:
        msg = 'Argument 2 to "setdefault" of "TypedDict" has incompatible type {}; expected {}'
        self.fail(
            msg.format(format_type(default, self.options), format_type(expected, self.options)),
            context,
            code=codes.TYPEDDICT_ITEM,
        )

    def type_arguments_not_allowed(self, context: Context) -> None:
        self.fail("Parameterized generics cannot be used with class or instance checks", context)

    def disallowed_any_type(self, typ: Type, context: Context) -> None:
        typ = get_proper_type(typ)
        if isinstance(typ, AnyType):
            message = 'Expression has type "Any"'
        else:
            message = f'Expression type contains "Any" (has type {format_type(typ, self.options)})'
        self.fail(message, context)

    def incorrectly_returning_any(self, typ: Type, context: Context) -> None:
        message = (
            f"Returning Any from function declared to return {format_type(typ, self.options)}"
        )
        self.fail(message, context, code=codes.NO_ANY_RETURN)

    def incorrect__exit__return(self, context: Context) -> None:
        self.fail(
            '"bool" is invalid as return type for "__exit__" that always returns False',
            context,
            code=codes.EXIT_RETURN,
        )
        self.note(
            'Use "typing_extensions.Literal[False]" as the return type or change it to "None"',
            context,
            code=codes.EXIT_RETURN,
        )
        self.note(
            'If return type of "__exit__" implies that it may return True, '
            "the context manager may swallow exceptions",
            context,
            code=codes.EXIT_RETURN,
        )

    def untyped_decorated_function(self, typ: Type, context: Context) -> None:
        typ = get_proper_type(typ)
        if isinstance(typ, AnyType):
            self.fail("Function is untyped after decorator transformation", context)
        else:
            self.fail(
                f'Type of decorated function contains type "Any" ({format_type(typ, self.options)})',
                context,
            )

    def typed_function_untyped_decorator(self, func_name: str, context: Context) -> None:
        self.fail(f'Untyped decorator makes function "{func_name}" untyped', context)

    def bad_proto_variance(
        self, actual: int, tvar_name: str, expected: int, context: Context
    ) -> None:
        msg = capitalize(
            '{} type variable "{}" used in protocol where {} one is expected'.format(
                variance_string(actual), tvar_name, variance_string(expected)
            )
        )
        self.fail(msg, context)

    def concrete_only_assign(self, typ: Type, context: Context) -> None:
        self.fail(
            f"Can only assign concrete classes to a variable of type {format_type(typ, self.options)}",
            context,
            code=codes.TYPE_ABSTRACT,
        )

    def concrete_only_call(self, typ: Type, context: Context) -> None:
        self.fail(
            f"Only concrete class can be given where {format_type(typ, self.options)} is expected",
            context,
            code=codes.TYPE_ABSTRACT,
        )

    def cannot_use_function_with_type(
        self, method_name: str, type_name: str, context: Context
    ) -> None:
        self.fail(f"Cannot use {method_name}() with {type_name} type", context)

    def report_non_method_protocol(
        self, tp: TypeInfo, members: list[str], context: Context
    ) -> None:
        self.fail(
            "Only protocols that don't have non-method members can be used with issubclass()",
            context,
        )
        if len(members) < 3:
            attrs = ", ".join(members)
            self.note(f'Protocol "{tp.name}" has non-method member(s): {attrs}', context)

    def note_call(
        self, subtype: Type, call: Type, context: Context, *, code: ErrorCode | None
    ) -> None:
        self.note(
            '"{}.__call__" has type {}'.format(
                format_type_bare(subtype, self.options),
                format_type(call, self.options, verbosity=1),
            ),
            context,
            code=code,
        )

    def unreachable_statement(self, context: Context) -> None:
        self.fail("Statement is unreachable", context, code=codes.UNREACHABLE)

    def redundant_left_operand(self, op_name: str, context: Context) -> None:
        """Indicates that the left operand of a boolean expression is redundant:
        it does not change the truth value of the entire condition as a whole.
        'op_name' should either be the string "and" or the string "or".
        """
        self.redundant_expr(f'Left operand of "{op_name}"', op_name == "and", context)

    def unreachable_right_operand(self, op_name: str, context: Context) -> None:
        """Indicates that the right operand of a boolean expression is redundant:
        it does not change the truth value of the entire condition as a whole.
        'op_name' should either be the string "and" or the string "or".
        """
        self.fail(
            f'Right operand of "{op_name}" is never evaluated', context, code=codes.UNREACHABLE
        )

    def redundant_condition_in_comprehension(self, truthiness: bool, context: Context) -> None:
        self.redundant_expr("If condition in comprehension", truthiness, context)

    def redundant_condition_in_if(self, truthiness: bool, context: Context) -> None:
        self.redundant_expr("If condition", truthiness, context)

    def redundant_expr(self, description: str, truthiness: bool, context: Context) -> None:
        self.fail(
            f"{description} is always {str(truthiness).lower()}",
            context,
            code=codes.REDUNDANT_EXPR,
        )

    def impossible_intersection(
        self, formatted_base_class_list: str, reason: str, context: Context
    ) -> None:
        template = "Subclass of {} cannot exist: {}"
        self.fail(
            template.format(formatted_base_class_list, reason), context, code=codes.UNREACHABLE
        )

    def tvar_without_default_type(
        self, tvar_name: str, last_tvar_name_with_default: str, context: Context
    ) -> None:
        self.fail(
            f'"{tvar_name}" cannot appear after "{last_tvar_name_with_default}" '
            "in type parameter list because it has no default type",
            context,
        )

    def report_protocol_problems(
        self,
        subtype: Instance | TupleType | TypedDictType | TypeType | CallableType,
        supertype: Instance,
        context: Context,
        *,
        code: ErrorCode | None,
    ) -> None:
        """Report possible protocol conflicts between 'subtype' and 'supertype'.

        This includes missing members, incompatible types, and incompatible
        attribute flags, such as settable vs read-only or class variable vs
        instance variable.
        """
        OFFSET = 4  # Four spaces, so that notes will look like this:
        # note: 'Cls' is missing following 'Proto' members:
        # note:     method, attr
        MAX_ITEMS = 2  # Maximum number of conflicts, missing members, and overloads shown
        # List of special situations where we don't want to report additional problems
        exclusions: dict[type, list[str]] = {
            TypedDictType: ["typing.Mapping"],
            TupleType: ["typing.Iterable", "typing.Sequence"],
        }
        if supertype.type.fullname in exclusions.get(type(subtype), []):
            return
        if any(isinstance(tp, UninhabitedType) for tp in get_proper_types(supertype.args)):
            # We don't want to add notes for failed inference (e.g. Iterable[Never]).
            # This will be only confusing a user even more.
            return

        class_obj = False
        is_module = False
        skip = []
        if isinstance(subtype, TupleType):
            if not isinstance(subtype.partial_fallback, Instance):
                return
            subtype = subtype.partial_fallback
        elif isinstance(subtype, TypedDictType):
            if not isinstance(subtype.fallback, Instance):
                return
            subtype = subtype.fallback
        elif isinstance(subtype, TypeType):
            if not isinstance(subtype.item, Instance):
                return
            class_obj = True
            subtype = subtype.item
        elif isinstance(subtype, CallableType):
            if subtype.is_type_obj():
                ret_type = get_proper_type(subtype.ret_type)
                if isinstance(ret_type, TupleType):
                    ret_type = ret_type.partial_fallback
                if not isinstance(ret_type, Instance):
                    return
                class_obj = True
                subtype = ret_type
            else:
                subtype = subtype.fallback
                skip = ["__call__"]
        if subtype.extra_attrs and subtype.extra_attrs.mod_name:
            is_module = True

        # Report missing members
        missing = get_missing_protocol_members(subtype, supertype, skip=skip)
        if (
            missing
            and (len(missing) < len(supertype.type.protocol_members) or missing == ["__call__"])
            and len(missing) <= MAX_ITEMS
        ):
            if missing == ["__call__"] and class_obj:
                self.note(
                    '"{}" has constructor incompatible with "__call__" of "{}"'.format(
                        subtype.type.name, supertype.type.name
                    ),
                    context,
                    code=code,
                )
            else:
                self.note(
                    '"{}" is missing following "{}" protocol member{}:'.format(
                        subtype.type.name, supertype.type.name, plural_s(missing)
                    ),
                    context,
                    code=code,
                )
                self.note(", ".join(missing), context, offset=OFFSET, code=code)
        elif len(missing) > MAX_ITEMS or len(missing) == len(supertype.type.protocol_members):
            # This is an obviously wrong type: too many missing members
            return

        # Report member type conflicts
        conflict_types = get_conflict_protocol_types(
            subtype, supertype, class_obj=class_obj, options=self.options
        )
        if conflict_types and (
            not is_subtype(subtype, erase_type(supertype), options=self.options)
            or not subtype.type.defn.type_vars
            or not supertype.type.defn.type_vars
            # Always show detailed message for ParamSpec
            or subtype.type.has_param_spec_type
            or supertype.type.has_param_spec_type
        ):
            type_name = format_type(subtype, self.options, module_names=True)
            self.note(f"Following member(s) of {type_name} have conflicts:", context, code=code)
            for name, got, exp in conflict_types[:MAX_ITEMS]:
                exp = get_proper_type(exp)
                got = get_proper_type(got)
                if not isinstance(exp, (CallableType, Overloaded)) or not isinstance(
                    got, (CallableType, Overloaded)
                ):
                    self.note(
                        "{}: expected {}, got {}".format(
                            name, *format_type_distinctly(exp, got, options=self.options)
                        ),
                        context,
                        offset=OFFSET,
                        code=code,
                    )
                else:
                    self.note("Expected:", context, offset=OFFSET, code=code)
                    if isinstance(exp, CallableType):
                        self.note(
                            pretty_callable(exp, self.options, skip_self=class_obj or is_module),
                            context,
                            offset=2 * OFFSET,
                            code=code,
                        )
                    else:
                        assert isinstance(exp, Overloaded)
                        self.pretty_overload(
                            exp, context, 2 * OFFSET, code=code, skip_self=class_obj or is_module
                        )
                    self.note("Got:", context, offset=OFFSET, code=code)
                    if isinstance(got, CallableType):
                        self.note(
                            pretty_callable(got, self.options, skip_self=class_obj or is_module),
                            context,
                            offset=2 * OFFSET,
                            code=code,
                        )
                    else:
                        assert isinstance(got, Overloaded)
                        self.pretty_overload(
                            got, context, 2 * OFFSET, code=code, skip_self=class_obj or is_module
                        )
            self.print_more(conflict_types, context, OFFSET, MAX_ITEMS, code=code)

        # Report flag conflicts (i.e. settable vs read-only etc.)
        conflict_flags = get_bad_protocol_flags(subtype, supertype, class_obj=class_obj)
        for name, subflags, superflags in conflict_flags[:MAX_ITEMS]:
            if not class_obj and IS_CLASSVAR in subflags and IS_CLASSVAR not in superflags:
                self.note(
                    "Protocol member {}.{} expected instance variable, got class variable".format(
                        supertype.type.name, name
                    ),
                    context,
                    code=code,
                )
            if not class_obj and IS_CLASSVAR in superflags and IS_CLASSVAR not in subflags:
                self.note(
                    "Protocol member {}.{} expected class variable, got instance variable".format(
                        supertype.type.name, name
                    ),
                    context,
                    code=code,
                )
            if IS_SETTABLE in superflags and IS_SETTABLE not in subflags:
                self.note(
                    "Protocol member {}.{} expected settable variable,"
                    " got read-only attribute".format(supertype.type.name, name),
                    context,
                    code=code,
                )
            if IS_CLASS_OR_STATIC in superflags and IS_CLASS_OR_STATIC not in subflags:
                self.note(
                    "Protocol member {}.{} expected class or static method".format(
                        supertype.type.name, name
                    ),
                    context,
                    code=code,
                )
            if (
                class_obj
                and IS_VAR in superflags
                and (IS_VAR in subflags and IS_CLASSVAR not in subflags)
            ):
                self.note(
                    "Only class variables allowed for class object access on protocols,"
                    ' {} is an instance variable of "{}"'.format(name, subtype.type.name),
                    context,
                    code=code,
                )
            if class_obj and IS_CLASSVAR in superflags:
                self.note(
                    "ClassVar protocol member {}.{} can never be matched by a class object".format(
                        supertype.type.name, name
                    ),
                    context,
                    code=code,
                )
        self.print_more(conflict_flags, context, OFFSET, MAX_ITEMS, code=code)

    def pretty_overload(
        self,
        tp: Overloaded,
        context: Context,
        offset: int,
        *,
        add_class_or_static_decorator: bool = False,
        allow_dups: bool = False,
        code: ErrorCode | None = None,
        skip_self: bool = False,
    ) -> None:
        for item in tp.items:
            self.note("@overload", context, offset=offset, allow_dups=allow_dups, code=code)

            if add_class_or_static_decorator:
                decorator = pretty_class_or_static_decorator(item)
                if decorator is not None:
                    self.note(decorator, context, offset=offset, allow_dups=allow_dups, code=code)

            self.note(
                pretty_callable(item, self.options, skip_self=skip_self),
                context,
                offset=offset,
                allow_dups=allow_dups,
                code=code,
            )

    def print_more(
        self,
        conflicts: Sequence[Any],
        context: Context,
        offset: int,
        max_items: int,
        *,
        code: ErrorCode | None = None,
    ) -> None:
        if len(conflicts) > max_items:
            self.note(
                f"<{len(conflicts) - max_items} more conflict(s) not shown>",
                context,
                offset=offset,
                code=code,
            )

    def try_report_long_tuple_assignment_error(
        self,
        subtype: ProperType,
        supertype: ProperType,
        context: Context,
        msg: message_registry.ErrorMessage,
        subtype_label: str | None = None,
        supertype_label: str | None = None,
    ) -> bool:
        """Try to generate meaningful error message for very long tuple assignment

        Returns a bool: True when generating long tuple assignment error,
        False when no such error reported
        """
        if isinstance(subtype, TupleType):
            if (
                len(subtype.items) > MAX_TUPLE_ITEMS
                and isinstance(supertype, Instance)
                and supertype.type.fullname == "builtins.tuple"
            ):
                lhs_type = supertype.args[0]
                lhs_types = [lhs_type] * len(subtype.items)
                self.generate_incompatible_tuple_error(lhs_types, subtype.items, context, msg)
                return True
            elif isinstance(supertype, TupleType) and (
                len(subtype.items) > MAX_TUPLE_ITEMS or len(supertype.items) > MAX_TUPLE_ITEMS
            ):
                if len(subtype.items) != len(supertype.items):
                    if supertype_label is not None and subtype_label is not None:
                        msg = msg.with_additional_msg(
                            " ({} {}, {} {})".format(
                                subtype_label,
                                self.format_long_tuple_type(subtype),
                                supertype_label,
                                self.format_long_tuple_type(supertype),
                            )
                        )
                        self.fail(msg.value, context, code=msg.code)
                        return True
                self.generate_incompatible_tuple_error(
                    supertype.items, subtype.items, context, msg
                )
                return True
        return False

    def format_long_tuple_type(self, typ: TupleType) -> str:
        """Format very long tuple type using an ellipsis notation"""
        item_cnt = len(typ.items)
        if item_cnt > MAX_TUPLE_ITEMS:
            return "{}[{}, {}, ... <{} more items>]".format(
                "tuple" if self.options.use_lowercase_names() else "Tuple",
                format_type_bare(typ.items[0], self.options),
                format_type_bare(typ.items[1], self.options),
                str(item_cnt - 2),
            )
        else:
            return format_type_bare(typ, self.options)

    def generate_incompatible_tuple_error(
        self,
        lhs_types: list[Type],
        rhs_types: list[Type],
        context: Context,
        msg: message_registry.ErrorMessage,
    ) -> None:
        """Generate error message for individual incompatible tuple pairs"""
        error_cnt = 0
        notes: list[str] = []
        for i, (lhs_t, rhs_t) in enumerate(zip(lhs_types, rhs_types)):
            if not is_subtype(lhs_t, rhs_t):
                if error_cnt < 3:
                    notes.append(
                        "Expression tuple item {} has type {}; {} expected; ".format(
                            str(i),
                            format_type(rhs_t, self.options),
                            format_type(lhs_t, self.options),
                        )
                    )
                error_cnt += 1

        info = f" ({str(error_cnt)} tuple items are incompatible"
        if error_cnt - 3 > 0:
            info += f"; {str(error_cnt - 3)} items are omitted)"
        else:
            info += ")"
        msg = msg.with_additional_msg(info)
        self.fail(msg.value, context, code=msg.code)
        for note in notes:
            self.note(note, context, code=msg.code)

    def add_fixture_note(self, fullname: str, ctx: Context) -> None:
        self.note(f'Maybe your test fixture does not define "{fullname}"?', ctx)
        if fullname in SUGGESTED_TEST_FIXTURES:
            self.note(
                "Consider adding [builtins fixtures/{}] to your test description".format(
                    SUGGESTED_TEST_FIXTURES[fullname]
                ),
                ctx,
            )

    def annotation_in_unchecked_function(self, context: Context) -> None:
        self.note(
            "By default the bodies of untyped functions are not checked,"
            " consider using --check-untyped-defs",
            context,
            code=codes.ANNOTATION_UNCHECKED,
        )

    def type_parameters_should_be_declared(self, undeclared: list[str], context: Context) -> None:
        names = ", ".join('"' + n + '"' for n in undeclared)
        self.fail(
            message_registry.TYPE_PARAMETERS_SHOULD_BE_DECLARED.format(names),
            context,
            code=codes.VALID_TYPE,
        )


def quote_type_string(type_string: str) -> str:
    """Quotes a type representation for use in messages."""
    no_quote_regex = r"^<(tuple|union): \d+ items>$"
    if (
        type_string in ["Module", "overloaded function", "<deleted>"]
        or type_string.startswith("Module ")
        or re.match(no_quote_regex, type_string) is not None
        or type_string.endswith("?")
    ):
        # Messages are easier to read if these aren't quoted.  We use a
        # regex to match strings with variable contents.
        return type_string
    return f'"{type_string}"'


def format_callable_args(
    arg_types: list[Type],
    arg_kinds: list[ArgKind],
    arg_names: list[str | None],
    format: Callable[[Type], str],
    verbosity: int,
) -> str:
    """Format a bunch of Callable arguments into a string"""
    arg_strings = []
    for arg_name, arg_type, arg_kind in zip(arg_names, arg_types, arg_kinds):
        if arg_kind == ARG_POS and arg_name is None or verbosity == 0 and arg_kind.is_positional():
            arg_strings.append(format(arg_type))
        else:
            constructor = ARG_CONSTRUCTOR_NAMES[arg_kind]
            if arg_kind.is_star() or arg_name is None:
                arg_strings.append(f"{constructor}({format(arg_type)})")
            else:
                arg_strings.append(f"{constructor}({format(arg_type)}, {repr(arg_name)})")

    return ", ".join(arg_strings)


def format_type_inner(
    typ: Type,
    verbosity: int,
    options: Options,
    fullnames: set[str] | None,
    module_names: bool = False,
) -> str:
    """
    Convert a type to a relatively short string suitable for error messages.

    Args:
      verbosity: a coarse grained control on the verbosity of the type
      fullnames: a set of names that should be printed in full
    """

    def format(typ: Type) -> str:
        return format_type_inner(typ, verbosity, options, fullnames)

    def format_list(types: Sequence[Type]) -> str:
        return ", ".join(format(typ) for typ in types)

    def format_union_items(types: Sequence[Type]) -> list[str]:
        formatted = [format(typ) for typ in types if format(typ) != "None"]
        if len(formatted) > MAX_UNION_ITEMS and verbosity == 0:
            more = len(formatted) - MAX_UNION_ITEMS // 2
            formatted = formatted[: MAX_UNION_ITEMS // 2]
        else:
            more = 0
        if more:
            formatted.append(f"<{more} more items>")
        if any(format(typ) == "None" for typ in types):
            formatted.append("None")
        return formatted

    def format_union(types: Sequence[Type]) -> str:
        return " | ".join(format_union_items(types))

    def format_literal_value(typ: LiteralType) -> str:
        if typ.is_enum_literal():
            underlying_type = format(typ.fallback)
            return f"{underlying_type}.{typ.value}"
        else:
            return typ.value_repr()

    if isinstance(typ, TypeAliasType) and typ.is_recursive:
        if typ.alias is None:
            type_str = "<alias (unfixed)>"
        else:
            if verbosity >= 2 or (fullnames and typ.alias.fullname in fullnames):
                type_str = typ.alias.fullname
            else:
                type_str = typ.alias.name
            if typ.args:
                type_str += f"[{format_list(typ.args)}]"
        return type_str

    # TODO: always mention type alias names in errors.
    typ = get_proper_type(typ)

    if isinstance(typ, Instance):
        itype = typ
        # Get the short name of the type.
        if itype.type.fullname == "types.ModuleType":
            # Make some common error messages simpler and tidier.
            base_str = "Module"
            if itype.extra_attrs and itype.extra_attrs.mod_name and module_names:
                return f'{base_str} "{itype.extra_attrs.mod_name}"'
            return base_str
        if itype.type.fullname == "typing._SpecialForm":
            # This is not a real type but used for some typing-related constructs.
            return "<typing special form>"
        if itype.type.fullname in reverse_builtin_aliases and not options.use_lowercase_names():
            alias = reverse_builtin_aliases[itype.type.fullname]
            base_str = alias.split(".")[-1]
        elif verbosity >= 2 or (fullnames and itype.type.fullname in fullnames):
            base_str = itype.type.fullname
        else:
            base_str = itype.type.name
        if not itype.args:
            if itype.type.has_type_var_tuple_type and len(itype.type.type_vars) == 1:
                return base_str + "[()]"
            # No type arguments, just return the type name
            return base_str
        elif itype.type.fullname == "builtins.tuple":
            item_type_str = format(itype.args[0])
            return f"{'tuple' if options.use_lowercase_names() else 'Tuple'}[{item_type_str}, ...]"
        else:
            # There are type arguments. Convert the arguments to strings.
            return f"{base_str}[{format_list(itype.args)}]"
    elif isinstance(typ, UnpackType):
        if options.use_star_unpack():
            return f"*{format(typ.type)}"
        return f"Unpack[{format(typ.type)}]"
    elif isinstance(typ, TypeVarType):
        # This is similar to non-generic instance types.
        fullname = scoped_type_var_name(typ)
        if verbosity >= 2 or (fullnames and fullname in fullnames):
            return fullname
        return typ.name
    elif isinstance(typ, TypeVarTupleType):
        # This is similar to non-generic instance types.
        fullname = scoped_type_var_name(typ)
        if verbosity >= 2 or (fullnames and fullname in fullnames):
            return fullname
        return typ.name
    elif isinstance(typ, ParamSpecType):
        # Concatenate[..., P]
        if typ.prefix.arg_types:
            args = format_callable_args(
                typ.prefix.arg_types, typ.prefix.arg_kinds, typ.prefix.arg_names, format, verbosity
            )

            return f"[{args}, **{typ.name_with_suffix()}]"
        else:
            # TODO: better disambiguate ParamSpec name clashes.
            return typ.name_with_suffix()
    elif isinstance(typ, TupleType):
        # Prefer the name of the fallback class (if not tuple), as it's more informative.
        if typ.partial_fallback.type.fullname != "builtins.tuple":
            return format(typ.partial_fallback)
        type_items = format_list(typ.items) or "()"
        if options.use_lowercase_names():
            s = f"tuple[{type_items}]"
        else:
            s = f"Tuple[{type_items}]"
        return s
    elif isinstance(typ, TypedDictType):
        # If the TypedDictType is named, return the name
        if not typ.is_anonymous():
            return format(typ.fallback)
        items = []
        for item_name, item_type in typ.items.items():
            modifier = ""
            if item_name not in typ.required_keys:
                modifier += "?"
            if item_name in typ.readonly_keys:
                modifier += "="
            items.append(f"{item_name!r}{modifier}: {format(item_type)}")
        return f"TypedDict({{{', '.join(items)}}})"
    elif isinstance(typ, LiteralType):
        return f"Literal[{format_literal_value(typ)}]"
    elif isinstance(typ, UnionType):
        typ = get_proper_type(ignore_last_known_values(typ))
        if not isinstance(typ, UnionType):
            return format(typ)
        literal_items, union_items = separate_union_literals(typ)

        # Coalesce multiple Literal[] members. This also changes output order.
        # If there's just one Literal item, retain the original ordering.
        if len(literal_items) > 1:
            literal_str = "Literal[{}]".format(
                ", ".join(format_literal_value(t) for t in literal_items)
            )

            if len(union_items) == 1 and isinstance(get_proper_type(union_items[0]), NoneType):
                return (
                    f"{literal_str} | None"
                    if options.use_or_syntax()
                    else f"Optional[{literal_str}]"
                )
            elif union_items:
                return (
                    f"{literal_str} | {format_union(union_items)}"
                    if options.use_or_syntax()
                    else f"Union[{', '.join(format_union_items(union_items))}, {literal_str}]"
                )
            else:
                return literal_str
        else:
            # Only print Union as Optional if the Optional wouldn't have to contain another Union
            print_as_optional = (
                len(typ.items) - sum(isinstance(get_proper_type(t), NoneType) for t in typ.items)
                == 1
            )
            if print_as_optional:
                rest = [t for t in typ.items if not isinstance(get_proper_type(t), NoneType)]
                return (
                    f"{format(rest[0])} | None"
                    if options.use_or_syntax()
                    else f"Optional[{format(rest[0])}]"
                )
            else:
                s = (
                    format_union(typ.items)
                    if options.use_or_syntax()
                    else f"Union[{', '.join(format_union_items(typ.items))}]"
                )
            return s
    elif isinstance(typ, NoneType):
        return "None"
    elif isinstance(typ, AnyType):
        return "Any"
    elif isinstance(typ, DeletedType):
        return "<deleted>"
    elif isinstance(typ, UninhabitedType):
        return "Never"
    elif isinstance(typ, TypeType):
        type_name = "type" if options.use_lowercase_names() else "Type"
        return f"{type_name}[{format(typ.item)}]"
    elif isinstance(typ, FunctionLike):
        func = typ
        if func.is_type_obj():
            # The type of a type object type can be derived from the
            # return type (this always works).
            return format(TypeType.make_normalized(func.items[0].ret_type))
        elif isinstance(func, CallableType):
            if func.type_guard is not None:
                return_type = f"TypeGuard[{format(func.type_guard)}]"
            elif func.type_is is not None:
                return_type = f"TypeIs[{format(func.type_is)}]"
            else:
                return_type = format(func.ret_type)
            if func.is_ellipsis_args:
                return f"Callable[..., {return_type}]"
            param_spec = func.param_spec()
            if param_spec is not None:
                return f"Callable[{format(param_spec)}, {return_type}]"
            args = format_callable_args(
                func.arg_types, func.arg_kinds, func.arg_names, format, verbosity
            )
            return f"Callable[[{args}], {return_type}]"
        else:
            # Use a simple representation for function types; proper
            # function types may result in long and difficult-to-read
            # error messages.
            return "overloaded function"
    elif isinstance(typ, UnboundType):
        return typ.accept(TypeStrVisitor(options=options))
    elif isinstance(typ, Parameters):
        args = format_callable_args(typ.arg_types, typ.arg_kinds, typ.arg_names, format, verbosity)
        return f"[{args}]"
    elif typ is None:
        raise RuntimeError("Type is None")
    else:
        # Default case; we simply have to return something meaningful here.
        return "object"


def collect_all_named_types(t: Type) -> list[Type]:
    """Return all instances/aliases/type variables that `t` contains (including `t`).

    This is similar to collect_all_inner_types from typeanal but only
    returns instances and will recurse into fallbacks.
    """
    visitor = CollectAllNamedTypesQuery()
    t.accept(visitor)
    return visitor.types


class CollectAllNamedTypesQuery(TypeTraverserVisitor):
    def __init__(self) -> None:
        self.types: list[Type] = []

    def visit_instance(self, t: Instance) -> None:
        self.types.append(t)
        super().visit_instance(t)

    def visit_type_alias_type(self, t: TypeAliasType) -> None:
        if t.alias and not t.is_recursive:
            get_proper_type(t).accept(self)
        else:
            self.types.append(t)
            super().visit_type_alias_type(t)

    def visit_type_var(self, t: TypeVarType) -> None:
        self.types.append(t)
        super().visit_type_var(t)

    def visit_type_var_tuple(self, t: TypeVarTupleType) -> None:
        self.types.append(t)
        super().visit_type_var_tuple(t)

    def visit_param_spec(self, t: ParamSpecType) -> None:
        self.types.append(t)
        super().visit_param_spec(t)


def scoped_type_var_name(t: TypeVarLikeType) -> str:
    if not t.id.namespace:
        return t.name
    # TODO: support rare cases when both TypeVar name and namespace suffix coincide.
    *_, suffix = t.id.namespace.split(".")
    return f"{t.name}@{suffix}"


def find_type_overlaps(*types: Type) -> set[str]:
    """Return a set of fullnames that share a short name and appear in either type.

    This is used to ensure that distinct types with the same short name are printed
    with their fullname.
    """
    d: dict[str, set[str]] = {}
    for type in types:
        for t in collect_all_named_types(type):
            if isinstance(t, ProperType) and isinstance(t, Instance):
                d.setdefault(t.type.name, set()).add(t.type.fullname)
            elif isinstance(t, TypeAliasType) and t.alias:
                d.setdefault(t.alias.name, set()).add(t.alias.fullname)
            else:
                assert isinstance(t, TypeVarLikeType)
                d.setdefault(t.name, set()).add(scoped_type_var_name(t))
    for shortname in d.keys():
        if f"typing.{shortname}" in TYPES_FOR_UNIMPORTED_HINTS:
            d[shortname].add(f"typing.{shortname}")

    overlaps: set[str] = set()
    for fullnames in d.values():
        if len(fullnames) > 1:
            overlaps.update(fullnames)
    return overlaps


def format_type(
    typ: Type, options: Options, verbosity: int = 0, module_names: bool = False
) -> str:
    """
    Convert a type to a relatively short string suitable for error messages.

    `verbosity` is a coarse-grained control on the verbosity of the type

    This function returns a string appropriate for unmodified use in error
    messages; this means that it will be quoted in most cases.  If
    modification of the formatted string is required, callers should use
    format_type_bare.
    """
    return quote_type_string(format_type_bare(typ, options, verbosity, module_names))


def format_type_bare(
    typ: Type, options: Options, verbosity: int = 0, module_names: bool = False
) -> str:
    """
    Convert a type to a relatively short string suitable for error messages.

    `verbosity` is a coarse-grained control on the verbosity of the type
    `fullnames` specifies a set of names that should be printed in full

    This function will return an unquoted string.  If a caller doesn't need to
    perform post-processing on the string output, format_type should be used
    instead.  (The caller may want to use quote_type_string after
    processing has happened, to maintain consistent quoting in messages.)
    """
    return format_type_inner(typ, verbosity, options, find_type_overlaps(typ), module_names)


def format_type_distinctly(*types: Type, options: Options, bare: bool = False) -> tuple[str, ...]:
    """Jointly format types to distinct strings.

    Increase the verbosity of the type strings until they become distinct
    while also requiring that distinct types with the same short name are
    formatted distinctly.

    By default, the returned strings are created using format_type() and will be
    quoted accordingly. If ``bare`` is True, the returned strings will not
    be quoted; callers who need to do post-processing of the strings before
    quoting them (such as prepending * or **) should use this.
    """
    overlapping = find_type_overlaps(*types)
    for verbosity in range(2):
        strs = [
            format_type_inner(type, verbosity=verbosity, options=options, fullnames=overlapping)
            for type in types
        ]
        if len(set(strs)) == len(strs):
            break
    if bare:
        return tuple(strs)
    else:
        return tuple(quote_type_string(s) for s in strs)


def pretty_class_or_static_decorator(tp: CallableType) -> str | None:
    """Return @classmethod or @staticmethod, if any, for the given callable type."""
    if tp.definition is not None and isinstance(tp.definition, SYMBOL_FUNCBASE_TYPES):
        if tp.definition.is_class:
            return "@classmethod"
        if tp.definition.is_static:
            return "@staticmethod"
    return None


def pretty_callable(tp: CallableType, options: Options, skip_self: bool = False) -> str:
    """Return a nice easily-readable representation of a callable type.
    For example:
        def [T <: int] f(self, x: int, y: T) -> None

    If skip_self is True, print an actual callable type, as it would appear
    when bound on an instance/class, rather than how it would appear in the
    defining statement.
    """
    s = ""
    asterisk = False
    slash = False
    for i in range(len(tp.arg_types)):
        if s:
            s += ", "
        if tp.arg_kinds[i].is_named() and not asterisk:
            s += "*, "
            asterisk = True
        if tp.arg_kinds[i] == ARG_STAR:
            s += "*"
            asterisk = True
        if tp.arg_kinds[i] == ARG_STAR2:
            s += "**"
        name = tp.arg_names[i]
        if name:
            s += name + ": "
        type_str = format_type_bare(tp.arg_types[i], options)
        if tp.arg_kinds[i] == ARG_STAR2 and tp.unpack_kwargs:
            type_str = f"Unpack[{type_str}]"
        s += type_str
        if tp.arg_kinds[i].is_optional():
            s += " = ..."
        if (
            not slash
            and tp.arg_kinds[i].is_positional()
            and name is None
            and (
                i == len(tp.arg_types) - 1
                or (tp.arg_names[i + 1] is not None or not tp.arg_kinds[i + 1].is_positional())
            )
        ):
            s += ", /"
            slash = True

    # If we got a "special arg" (i.e: self, cls, etc...), prepend it to the arg list
    if (
        isinstance(tp.definition, FuncDef)
        and hasattr(tp.definition, "arguments")
        and not tp.from_concatenate
    ):
        definition_arg_names = [arg.variable.name for arg in tp.definition.arguments]
        if (
            len(definition_arg_names) > len(tp.arg_names)
            and definition_arg_names[0]
            and not skip_self
        ):
            if s:
                s = ", " + s
            s = definition_arg_names[0] + s
        s = f"{tp.definition.name}({s})"
    elif tp.name:
        first_arg = tp.def_extras.get("first_arg")
        if first_arg:
            if s:
                s = ", " + s
            s = first_arg + s
        s = f"{tp.name.split()[0]}({s})"  # skip "of Class" part
    else:
        s = f"({s})"

    s += " -> "
    if tp.type_guard is not None:
        s += f"TypeGuard[{format_type_bare(tp.type_guard, options)}]"
    elif tp.type_is is not None:
        s += f"TypeIs[{format_type_bare(tp.type_is, options)}]"
    else:
        s += format_type_bare(tp.ret_type, options)

    if tp.variables:
        tvars = []
        for tvar in tp.variables:
            if isinstance(tvar, TypeVarType):
                upper_bound = get_proper_type(tvar.upper_bound)
                if not (
                    isinstance(upper_bound, Instance)
                    and upper_bound.type.fullname == "builtins.object"
                ):
                    tvars.append(f"{tvar.name}: {format_type_bare(upper_bound, options)}")
                elif tvar.values:
                    tvars.append(
                        "{}: ({})".format(
                            tvar.name,
                            ", ".join([format_type_bare(tp, options) for tp in tvar.values]),
                        )
                    )
                else:
                    tvars.append(tvar.name)
            else:
                # For other TypeVarLikeTypes, just use the repr
                tvars.append(repr(tvar))
        s = f"[{', '.join(tvars)}] {s}"
    return f"def {s}"


def variance_string(variance: int) -> str:
    if variance == COVARIANT:
        return "covariant"
    elif variance == CONTRAVARIANT:
        return "contravariant"
    else:
        return "invariant"


def get_missing_protocol_members(left: Instance, right: Instance, skip: list[str]) -> list[str]:
    """Find all protocol members of 'right' that are not implemented
    (i.e. completely missing) in 'left'.
    """
    assert right.type.is_protocol
    missing: list[str] = []
    for member in right.type.protocol_members:
        if member in skip:
            continue
        if not find_member(member, left, left):
            missing.append(member)
    return missing


def get_conflict_protocol_types(
    left: Instance, right: Instance, class_obj: bool = False, options: Options | None = None
) -> list[tuple[str, Type, Type]]:
    """Find members that are defined in 'left' but have incompatible types.
    Return them as a list of ('member', 'got', 'expected').
    """
    assert right.type.is_protocol
    conflicts: list[tuple[str, Type, Type]] = []
    for member in right.type.protocol_members:
        if member in ("__init__", "__new__"):
            continue
        supertype = find_member(member, right, left)
        assert supertype is not None
        subtype = mypy.typeops.get_protocol_member(left, member, class_obj)
        if not subtype:
            continue
        is_compat = is_subtype(subtype, supertype, ignore_pos_arg_names=True, options=options)
        if IS_SETTABLE in get_member_flags(member, right):
            is_compat = is_compat and is_subtype(supertype, subtype, options=options)
        if not is_compat:
            conflicts.append((member, subtype, supertype))
    return conflicts


def get_bad_protocol_flags(
    left: Instance, right: Instance, class_obj: bool = False
) -> list[tuple[str, set[int], set[int]]]:
    """Return all incompatible attribute flags for members that are present in both
    'left' and 'right'.
    """
    assert right.type.is_protocol
    all_flags: list[tuple[str, set[int], set[int]]] = []
    for member in right.type.protocol_members:
        if find_member(member, left, left):
            item = (member, get_member_flags(member, left), get_member_flags(member, right))
            all_flags.append(item)
    bad_flags = []
    for name, subflags, superflags in all_flags:
        if (
            IS_CLASSVAR in subflags
            and IS_CLASSVAR not in superflags
            and IS_SETTABLE in superflags
            or IS_CLASSVAR in superflags
            and IS_CLASSVAR not in subflags
            or IS_SETTABLE in superflags
            and IS_SETTABLE not in subflags
            or IS_CLASS_OR_STATIC in superflags
            and IS_CLASS_OR_STATIC not in subflags
            or class_obj
            and IS_VAR in superflags
            and IS_CLASSVAR not in subflags
            or class_obj
            and IS_CLASSVAR in superflags
        ):
            bad_flags.append((name, subflags, superflags))
    return bad_flags


def capitalize(s: str) -> str:
    """Capitalize the first character of a string."""
    if s == "":
        return ""
    else:
        return s[0].upper() + s[1:]


def extract_type(name: str) -> str:
    """If the argument is the name of a method (of form C.m), return
    the type portion in quotes (e.g. "y"). Otherwise, return the string
    unmodified.
    """
    name = re.sub('^"[a-zA-Z0-9_]+" of ', "", name)
    return name


def strip_quotes(s: str) -> str:
    """Strip a double quote at the beginning and end of the string, if any."""
    s = re.sub('^"', "", s)
    s = re.sub('"$', "", s)
    return s


def format_string_list(lst: list[str]) -> str:
    assert lst
    if len(lst) == 1:
        return lst[0]
    elif len(lst) <= 5:
        return f"{', '.join(lst[:-1])} and {lst[-1]}"
    else:
        return "%s, ... and %s (%i methods suppressed)" % (
            ", ".join(lst[:2]),
            lst[-1],
            len(lst) - 3,
        )


def format_item_name_list(s: Iterable[str]) -> str:
    lst = list(s)
    if len(lst) <= 5:
        return "(" + ", ".join([f'"{name}"' for name in lst]) + ")"
    else:
        return "(" + ", ".join([f'"{name}"' for name in lst[:5]]) + ", ...)"


def callable_name(type: FunctionLike) -> str | None:
    name = type.get_name()
    if name is not None and name[0] != "<":
        return f'"{name}"'.replace(" of ", '" of "')
    return name


def for_function(callee: CallableType) -> str:
    name = callable_name(callee)
    if name is not None:
        return f" for {name}"
    return ""


def wrong_type_arg_count(low: int, high: int, act: str, name: str) -> str:
    if low == high:
        s = f"{low} type arguments"
        if low == 0:
            s = "no type arguments"
        elif low == 1:
            s = "1 type argument"
    else:
        s = f"between {low} and {high} type arguments"
    if act == "0":
        act = "none"
    return f'"{name}" expects {s}, but {act} given'


def find_defining_module(modules: dict[str, MypyFile], typ: CallableType) -> MypyFile | None:
    if not typ.definition:
        return None
    fullname = typ.definition.fullname
    if "." in fullname:
        for i in range(fullname.count(".")):
            module_name = fullname.rsplit(".", i + 1)[0]
            try:
                return modules[module_name]
            except KeyError:
                pass
        assert False, "Couldn't determine module from CallableType"
    return None


# For hard-coding suggested missing member alternatives.
COMMON_MISTAKES: Final[dict[str, Sequence[str]]] = {"add": ("append", "extend")}


def _real_quick_ratio(a: str, b: str) -> float:
    # this is an upper bound on difflib.SequenceMatcher.ratio
    # similar to difflib.SequenceMatcher.real_quick_ratio, but faster since we don't instantiate
    al = len(a)
    bl = len(b)
    return 2.0 * min(al, bl) / (al + bl)


def best_matches(current: str, options: Collection[str], n: int) -> list[str]:
    if not current:
        return []
    # narrow down options cheaply
    options = [o for o in options if _real_quick_ratio(current, o) > 0.75]
    if len(options) >= 50:
        options = [o for o in options if abs(len(o) - len(current)) <= 1]

    ratios = {option: difflib.SequenceMatcher(a=current, b=option).ratio() for option in options}
    options = [option for option, ratio in ratios.items() if ratio > 0.75]
    return sorted(options, key=lambda v: (-ratios[v], v))[:n]


def pretty_seq(args: Sequence[str], conjunction: str) -> str:
    quoted = ['"' + a + '"' for a in args]
    if len(quoted) == 1:
        return quoted[0]
    if len(quoted) == 2:
        return f"{quoted[0]} {conjunction} {quoted[1]}"
    last_sep = ", " + conjunction + " "
    return ", ".join(quoted[:-1]) + last_sep + quoted[-1]


def append_invariance_notes(
    notes: list[str], arg_type: Instance, expected_type: Instance
) -> list[str]:
    """Explain that the type is invariant and give notes for how to solve the issue."""
    invariant_type = ""
    covariant_suggestion = ""
    if (
        arg_type.type.fullname == "builtins.list"
        and expected_type.type.fullname == "builtins.list"
        and is_subtype(arg_type.args[0], expected_type.args[0])
    ):
        invariant_type = "List"
        covariant_suggestion = 'Consider using "Sequence" instead, which is covariant'
    elif (
        arg_type.type.fullname == "builtins.dict"
        and expected_type.type.fullname == "builtins.dict"
        and is_same_type(arg_type.args[0], expected_type.args[0])
        and is_subtype(arg_type.args[1], expected_type.args[1])
    ):
        invariant_type = "Dict"
        covariant_suggestion = (
            'Consider using "Mapping" instead, which is covariant in the value type'
        )
    if invariant_type and covariant_suggestion:
        notes.append(
            f'"{invariant_type}" is invariant -- see '
            + "https://mypy.readthedocs.io/en/stable/common_issues.html#variance"
        )
        notes.append(covariant_suggestion)
    return notes


def append_union_note(
    notes: list[str], arg_type: UnionType, expected_type: UnionType, options: Options
) -> list[str]:
    """Point to specific union item(s) that may cause failure in subtype check."""
    non_matching = []
    items = flatten_nested_unions(arg_type.items)
    if len(items) < MAX_UNION_ITEMS:
        return notes
    for item in items:
        if not is_subtype(item, expected_type):
            non_matching.append(item)
    if non_matching:
        types = ", ".join([format_type(typ, options) for typ in non_matching])
        notes.append(f"Item{plural_s(non_matching)} in the first union not in the second: {types}")
    return notes


def append_numbers_notes(
    notes: list[str], arg_type: Instance, expected_type: Instance
) -> list[str]:
    """Explain if an unsupported type from "numbers" is used in a subtype check."""
    if expected_type.type.fullname in UNSUPPORTED_NUMBERS_TYPES:
        notes.append('Types from "numbers" aren\'t supported for static type checking')
        notes.append("See https://peps.python.org/pep-0484/#the-numeric-tower")
        notes.append("Consider using a protocol instead, such as typing.SupportsFloat")
    return notes


def make_inferred_type_note(
    context: Context, subtype: Type, supertype: Type, supertype_str: str
) -> str:
    """Explain that the user may have forgotten to type a variable.

    The user does not expect an error if the inferred container type is the same as the return
    type of a function and the argument type(s) are a subtype of the argument type(s) of the
    return type. This note suggests that they add a type annotation with the return type instead
    of relying on the inferred type.
    """
    subtype = get_proper_type(subtype)
    supertype = get_proper_type(supertype)
    if (
        isinstance(subtype, Instance)
        and isinstance(supertype, Instance)
        and subtype.type.fullname == supertype.type.fullname
        and subtype.args
        and supertype.args
        and isinstance(context, ReturnStmt)
        and isinstance(context.expr, NameExpr)
        and isinstance(context.expr.node, Var)
        and context.expr.node.is_inferred
    ):
        for subtype_arg, supertype_arg in zip(subtype.args, supertype.args):
            if not is_subtype(subtype_arg, supertype_arg):
                return ""
        var_name = context.expr.name
        return 'Perhaps you need a type annotation for "{}"? Suggestion: {}'.format(
            var_name, supertype_str
        )
    return ""


def format_key_list(keys: list[str], *, short: bool = False) -> str:
    formatted_keys = [f'"{key}"' for key in keys]
    td = "" if short else "TypedDict "
    if len(keys) == 0:
        return f"no {td}keys"
    elif len(keys) == 1:
        return f"{td}key {formatted_keys[0]}"
    else:
        return f"{td}keys ({', '.join(formatted_keys)})"


def ignore_last_known_values(t: UnionType) -> Type:
    """This will avoid types like str | str in error messages.

    last_known_values are kept during union simplification, but may cause
    weird formatting for e.g. tuples of literals.
    """
    union_items: list[Type] = []
    seen_instances = set()
    for item in t.items:
        if isinstance(item, ProperType) and isinstance(item, Instance):
            erased = item.copy_modified(last_known_value=None)
            if erased in seen_instances:
                continue
            seen_instances.add(erased)
            union_items.append(erased)
        else:
            union_items.append(item)
    return UnionType.make_union(union_items, t.line, t.column)
