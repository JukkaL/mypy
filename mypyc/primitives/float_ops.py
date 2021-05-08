"""Primitive float ops."""

from mypyc.ir.ops import ERR_NEVER, ERR_MAGIC, ComparisonOp
from mypyc.ir.rtypes import (
    int_rprimitive, bool_rprimitive, float_rprimitive, object_rprimitive,
    str_rprimitive, bit_rprimitive, RType
)
from mypyc.primitives.registry import (
    function_op, binary_op
)


# float(str)
function_op(
    name='builtins.float',
    arg_types=[str_rprimitive],
    return_type=float_rprimitive,
    c_function_name='PyFloat_FromString',
    error_kind=ERR_MAGIC)

# abs(float)
function_op(
    name='builtins.abs',
    arg_types=[float_rprimitive],
    return_type=float_rprimitive,
    c_function_name='PyNumber_Absolute',
    error_kind=ERR_MAGIC)

#binary operations

def float_binary_op(name: str, c_function_name: str,
                  return_type: RType = float_rprimitive,
                  error_kind: float = ERR_NEVER) -> None:
    binary_op(name=name,
              arg_types=[float_rprimitive, float_rprimitive],
              return_type=return_type,
              c_function_name=c_function_name,
              error_kind=error_kind)


float_binary_op('+', 'PyFloat_Add')
