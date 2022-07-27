"""Primitive set (and frozenset) ops."""

from mypyc.primitives.registry import (
    load_address_op,
    function_op,
    method_op,
    binary_op,
    ERR_NEG_INT,
)
from mypyc.ir.ops import ERR_MAGIC, ERR_FALSE
from mypyc.ir.rtypes import (
    object_rprimitive,
    bool_rprimitive,
    set_rprimitive,
    c_int_rprimitive,
    pointer_rprimitive,
    bit_rprimitive,
)


# Get the 'builtins.set' type object.
load_address_op(name="builtins.set", type=object_rprimitive, src="PySet_Type")

# Get the 'builtins.frozenset' tyoe object.
load_address_op(name="builtins.frozenset", type=object_rprimitive, src="PyFrozenSet_Type")

# Construct an empty set.
new_set_op = function_op(
    name="builtins.set",
    arg_types=[],
    return_type=set_rprimitive,
    c_function_name="PySet_New",
    error_kind=ERR_MAGIC,
    extra_int_constants=[(0, pointer_rprimitive)],
)

# set(obj)
function_op(
    name="builtins.set",
    arg_types=[object_rprimitive],
    return_type=set_rprimitive,
    c_function_name="PySet_New",
    error_kind=ERR_MAGIC,
)

# frozenset(obj)
function_op(
    name="builtins.frozenset",
    arg_types=[object_rprimitive],
    return_type=object_rprimitive,
    c_function_name="PyFrozenSet_New",
    error_kind=ERR_MAGIC,
)

# item in set
binary_op(
    name="in",
    arg_types=[object_rprimitive, set_rprimitive],
    return_type=c_int_rprimitive,
    c_function_name="PySet_Contains",
    error_kind=ERR_NEG_INT,
    truncated_type=bool_rprimitive,
    ordering=[1, 0],
)

# set.remove(obj)
method_op(
    name="remove",
    arg_types=[set_rprimitive, object_rprimitive],
    return_type=bit_rprimitive,
    c_function_name="CPySet_Remove",
    error_kind=ERR_FALSE,
)

# set.discard(obj)
method_op(
    name="discard",
    arg_types=[set_rprimitive, object_rprimitive],
    return_type=c_int_rprimitive,
    c_function_name="PySet_Discard",
    error_kind=ERR_NEG_INT,
)

# set.add(obj)
set_add_op = method_op(
    name="add",
    arg_types=[set_rprimitive, object_rprimitive],
    return_type=c_int_rprimitive,
    c_function_name="PySet_Add",
    error_kind=ERR_NEG_INT,
)

# set.update(obj)
#
# This is not a public API but looks like it should be fine.
set_update_op = method_op(
    name="update",
    arg_types=[set_rprimitive, object_rprimitive],
    return_type=c_int_rprimitive,
    c_function_name="_PySet_Update",
    error_kind=ERR_NEG_INT,
)

# set.clear()
method_op(
    name="clear",
    arg_types=[set_rprimitive],
    return_type=c_int_rprimitive,
    c_function_name="PySet_Clear",
    error_kind=ERR_NEG_INT,
)

# set.pop()
method_op(
    name="pop",
    arg_types=[set_rprimitive],
    return_type=object_rprimitive,
    c_function_name="PySet_Pop",
    error_kind=ERR_MAGIC,
)
