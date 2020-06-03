"""Utilities for defining primitive ops.

Most of the ops can be automatically generated by matching against AST
nodes and types. For example, a func_op is automatically generated when
a specific function is called with the specific positional argument
count and argument types.

Example op definition:

list_len_op = func_op(name='builtins.len',
                      arg_types=[list_rprimitive],
                      result_type=short_int_rprimitive,
                      error_kind=ERR_NEVER,
                      emit=emit_len)

This op is automatically generated for calls to len() with a single
list argument. The result type is short_int_rprimitive, and this
never raises an exception (ERR_NEVER). The function emit_len is used
to generate C for this op.  The op can also be manually generated using
"list_len_op". Ops that are only generated automatically don't need to
be assigned to a module attribute.

Ops defined with custom_op are only explicitly generated in
mypyc.irbuild and won't be generated automatically. They are always
assigned to a module attribute, as otherwise they won't be accessible.

The actual ops are defined in other submodules of this package, grouped
by category.

Most operations have fallback implementations that apply to all possible
arguments and types. For example, there are generic implementations of
arbitrary function and method calls, and binary operators. These generic
implementations are typically slower than specialized ones, but we tend
to rely on them for infrequently used ops. It's impractical to have
optimized implementations of all ops.
"""

from typing import Dict, List, Optional, NamedTuple

from mypyc.ir.ops import (
    OpDescription, EmitterInterface, EmitCallback, StealsDescription, short_name
)
from mypyc.ir.rtypes import RType,  bool_rprimitive

CFunctionDescription = NamedTuple(
    'CFunctionDescription',  [('name', str),
                              ('arg_types', List[RType]),
                              ('return_type', RType),
                              ('c_function_name', str),
                              ('error_kind', int),
                              ('steals', StealsDescription),
                              ('priority', int)])

# Primitive binary ops (key is operator such as '+')
binary_ops = {}  # type: Dict[str, List[OpDescription]]

# Primitive unary ops (key is operator such as '-')
unary_ops = {}  # type: Dict[str, List[OpDescription]]

# Primitive ops for built-in functions (key is function name such as 'builtins.len')
func_ops = {}  # type: Dict[str, List[OpDescription]]

# Primitive ops for built-in methods (key is method name such as 'builtins.list.append')
method_ops = {}  # type: Dict[str, List[OpDescription]]

# Primitive ops for reading module attributes (key is name such as 'builtins.None')
name_ref_ops = {}  # type: Dict[str, OpDescription]

# CallC op for method call(such as 'str.join')
c_method_call_ops = {}  # type: Dict[str, List[CFunctionDescription]]

# CallC op for top level function call(such as 'builtins.list')
c_function_ops = {}  # type: Dict[str, List[CFunctionDescription]]

# CallC op for binary ops
c_binary_ops = {}  # type: Dict[str, List[CFunctionDescription]]


def simple_emit(template: str) -> EmitCallback:
    """Construct a simple PrimitiveOp emit callback function.

    It just applies a str.format template to
    'args', 'dest', 'comma_args', 'num_args', 'comma_if_args'.

    For more complex cases you need to define a custom function.
    """

    def emit(emitter: EmitterInterface, args: List[str], dest: str) -> None:
        comma_args = ', '.join(args)
        comma_if_args = ', ' if comma_args else ''

        emitter.emit_line(template.format(
            args=args,
            dest=dest,
            comma_args=comma_args,
            comma_if_args=comma_if_args,
            num_args=len(args)))

    return emit


def name_emit(name: str, target_type: Optional[str] = None) -> EmitCallback:
    """Construct a PrimitiveOp emit callback function that assigns a C name."""
    cast = "({})".format(target_type) if target_type else ""
    return simple_emit('{dest} = %s%s;' % (cast, name))


def call_emit(func: str) -> EmitCallback:
    """Construct a PrimitiveOp emit callback function that calls a C function."""
    return simple_emit('{dest} = %s({comma_args});' % func)


def call_void_emit(func: str) -> EmitCallback:
    return simple_emit('%s({comma_args});' % func)


def call_and_fail_emit(func: str) -> EmitCallback:
    # This is a hack for our always failing operations like CPy_Raise,
    # since we want the optimizer to see that it always fails but we
    # don't have an ERR_ALWAYS yet.
    # TODO: Have an ERR_ALWAYS.
    return simple_emit('%s({comma_args}); {dest} = 0;' % func)


def call_negative_bool_emit(func: str) -> EmitCallback:
    """Construct an emit callback that calls a function and checks for negative return.

    The negative return value is converted to a bool (true -> no error).
    """
    return simple_emit('{dest} = %s({comma_args}) >= 0;' % func)


def negative_int_emit(template: str) -> EmitCallback:
    """Construct a simple PrimitiveOp emit callback function that checks for -1 return."""

    def emit(emitter: EmitterInterface, args: List[str], dest: str) -> None:
        temp = emitter.temp_name()
        emitter.emit_line(template.format(args=args, dest='int %s' % temp,
                                          comma_args=', '.join(args)))
        emitter.emit_lines('if (%s < 0)' % temp,
                           '    %s = %s;' % (dest, emitter.c_error_value(bool_rprimitive)),
                           'else',
                           '    %s = %s;' % (dest, temp))

    return emit


def call_negative_magic_emit(func: str) -> EmitCallback:
    return negative_int_emit('{dest} = %s({comma_args});' % func)


def binary_op(op: str,
              arg_types: List[RType],
              result_type: RType,
              error_kind: int,
              emit: EmitCallback,
              format_str: Optional[str] = None,
              steals: StealsDescription = False,
              is_borrowed: bool = False,
              priority: int = 1) -> None:
    """Define a PrimitiveOp for a binary operation.

    Arguments are similar to func_op(), but exactly two argument types
    are expected.

    This will be automatically generated by matching against the AST.
    """
    assert len(arg_types) == 2
    ops = binary_ops.setdefault(op, [])
    if format_str is None:
        format_str = '{dest} = {args[0]} %s {args[1]}' % op
    desc = OpDescription(op, arg_types, result_type, False, error_kind, format_str, emit,
                         steals, is_borrowed, priority)
    ops.append(desc)


def unary_op(op: str,
             arg_type: RType,
             result_type: RType,
             error_kind: int,
             emit: EmitCallback,
             format_str: Optional[str] = None,
             steals: StealsDescription = False,
             is_borrowed: bool = False,
             priority: int = 1) -> OpDescription:
    """Define a PrimitiveOp for a unary operation.

    Arguments are similar to func_op(), but only a single argument type
    is expected.

    This will be automatically generated by matching against the AST.
    """
    ops = unary_ops.setdefault(op, [])
    if format_str is None:
        format_str = '{dest} = %s{args[0]}' % op
    desc = OpDescription(op, [arg_type], result_type, False, error_kind, format_str, emit,
                         steals, is_borrowed, priority)
    ops.append(desc)
    return desc


def func_op(name: str,
            arg_types: List[RType],
            result_type: RType,
            error_kind: int,
            emit: EmitCallback,
            format_str: Optional[str] = None,
            steals: StealsDescription = False,
            is_borrowed: bool = False,
            priority: int = 1) -> OpDescription:
    """Define a PrimitiveOp that implements a Python function call.

    This will be automatically generated by matching against the AST.

    Args:
        name: full name of the function
        arg_types: positional argument types for which this applies
        result_type: type of the return value
        error_kind: how errors are represented in the result (one of ERR_*)
        emit: called to construct C code for the op
        format_str: used to format the op in pretty-printed IR (if None, use
            default formatting)
        steals: description of arguments that this steals (ref count wise)
        is_borrowed: if True, returned value is borrowed (no need to decrease refcount)
        priority: if multiple ops match, the one with the highest priority is picked
    """
    ops = func_ops.setdefault(name, [])
    typename = ''
    if len(arg_types) == 1:
        typename = ' :: %s' % short_name(arg_types[0].name)
    if format_str is None:
        format_str = '{dest} = %s %s%s' % (short_name(name),
                                           ', '.join('{args[%d]}' % i
                                                     for i in range(len(arg_types))),
                                           typename)
    desc = OpDescription(name, arg_types, result_type, False, error_kind, format_str, emit,
                         steals, is_borrowed, priority)
    ops.append(desc)
    return desc


def method_op(name: str,
              arg_types: List[RType],
              result_type: Optional[RType],
              error_kind: int,
              emit: EmitCallback,
              steals: StealsDescription = False,
              is_borrowed: bool = False,
              priority: int = 1) -> OpDescription:
    """Define a primitive op that replaces a method call.

    Most arguments are similar to func_op().

    This will be automatically generated by matching against the AST.

    Args:
        name: short name of the method (for example, 'append')
        arg_types: argument types; the receiver is always the first argument
        result_type: type of the result, None if void
    """
    ops = method_ops.setdefault(name, [])
    assert len(arg_types) > 0
    args = ', '.join('{args[%d]}' % i
                     for i in range(1, len(arg_types)))
    type_name = short_name(arg_types[0].name)
    if name == '__getitem__':
        format_str = '{dest} = {args[0]}[{args[1]}] :: %s' % type_name
    else:
        format_str = '{dest} = {args[0]}.%s(%s) :: %s' % (name, args, type_name)
    desc = OpDescription(name, arg_types, result_type, False, error_kind, format_str, emit,
                         steals, is_borrowed, priority)
    ops.append(desc)
    return desc


def name_ref_op(name: str,
                result_type: RType,
                error_kind: int,
                emit: EmitCallback,
                is_borrowed: bool = False) -> OpDescription:
    """Define an op that is used to implement reading a module attribute.

    This will be automatically generated by matching against the AST.

    Most arguments are similar to func_op().

    Args:
        name: fully-qualified name (e.g. 'builtins.None')
    """
    assert name not in name_ref_ops, 'already defined: %s' % name
    format_str = '{dest} = %s' % short_name(name)
    desc = OpDescription(name, [], result_type, False, error_kind, format_str, emit,
                         False, is_borrowed, 0)
    name_ref_ops[name] = desc
    return desc


def custom_op(arg_types: List[RType],
              result_type: RType,
              error_kind: int,
              emit: EmitCallback,
              name: Optional[str] = None,
              format_str: Optional[str] = None,
              steals: StealsDescription = False,
              is_borrowed: bool = False,
              is_var_arg: bool = False) -> OpDescription:
    """Create a one-off op that can't be automatically generated from the AST.

    Note that if the format_str argument is not provided, then a
    format_str is generated using the name argument. The name argument
    only needs to be provided if the format_str argument is not
    provided.

    Most arguments are similar to func_op().

    If is_var_arg is True, the op takes an arbitrary number of positional
    arguments. arg_types should contain a single type, which is used for
    all arguments.
    """
    if name is not None and format_str is None:
        typename = ''
        if len(arg_types) == 1:
            typename = ' :: %s' % short_name(arg_types[0].name)
        format_str = '{dest} = %s %s%s' % (short_name(name),
                                       ', '.join('{args[%d]}' % i for i in range(len(arg_types))),
                                       typename)
    assert format_str is not None
    return OpDescription('<custom>', arg_types, result_type, is_var_arg, error_kind, format_str,
                         emit, steals, is_borrowed, 0)


def c_method_op(name: str,
                arg_types: List[RType],
                return_type: RType,
                c_function_name: str,
                error_kind: int,
                steals: StealsDescription = False,
                priority: int = 1) -> CFunctionDescription:
    ops = c_method_call_ops.setdefault(name, [])
    desc = CFunctionDescription(name, arg_types, return_type,
                                c_function_name, error_kind, steals, priority)
    ops.append(desc)
    return desc


def c_function_op(name: str,
                  arg_types: List[RType],
                  return_type: RType,
                  c_function_name: str,
                  error_kind: int,
                  steals: StealsDescription = False,
                  priority: int = 1) -> CFunctionDescription:
    ops = c_function_ops.setdefault(name, [])
    desc = CFunctionDescription(name, arg_types, return_type,
                                c_function_name, error_kind, steals, priority)
    ops.append(desc)
    return desc


def c_binary_op(name: str,
                arg_types: List[RType],
                return_type: RType,
                c_function_name: str,
                error_kind: int,
                steals: StealsDescription = False,
                priority: int = 1) -> CFunctionDescription:
    ops = c_binary_ops.setdefault(name, [])
    desc = CFunctionDescription(name, arg_types, return_type,
                            c_function_name, error_kind, steals, priority)
    ops.append(desc)
    return desc


def c_custom_op(arg_types: List[RType],
                return_type: RType,
                c_function_name: str,
                error_kind: int,
                steals: StealsDescription = False) -> CFunctionDescription:
    return CFunctionDescription('<custom>', arg_types, return_type,
                            c_function_name, error_kind, steals, 0)


# Import various modules that set up global state.
import mypyc.primitives.int_ops  # noqa
import mypyc.primitives.str_ops  # noqa
import mypyc.primitives.list_ops  # noqa
import mypyc.primitives.dict_ops  # noqa
import mypyc.primitives.tuple_ops  # noqa
import mypyc.primitives.misc_ops  # noqa
