"""Primitive bytes ops."""

from mypyc.ir.rtypes import object_rprimitive
from mypyc.primitives.registry import load_address_op


# Get the 'bytes' type object.
load_address_op(
    name='builtins.bytes',
    type=object_rprimitive,
    src='PyBytes_Type')
