from typing import List, Dict

from mypyc.ir.ops import BasicBlock, LoadInt, Assign
from mypyc.ir.rtypes import is_short_int_rprimitive, is_int_rprimitive


def find_constant_integer_registers(blocks: List[BasicBlock],
                                    convert_tagged: bool = False) -> Dict[str, int]:
    """
    Find all registers with constant integer values.

    Returns a mapping from register names to int values
    """
    const_int_regs = {}  # type: Dict[str, int]
    for block in blocks:
        for op in block.ops:
            if isinstance(op, LoadInt):
                const_int_regs[op.name] = op.value
    return const_int_regs
