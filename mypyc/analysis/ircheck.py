"""Utilities for checking that internal ir is valid and consistent."""
from typing import List, Union, Set, Tuple
from mypyc.ir.pprint import format_func
from mypyc.ir.ops import (
    OpVisitor, BasicBlock, Op, ControlOp, Goto, Branch, Return, Unreachable,
    Assign, AssignMulti, LoadErrorValue, LoadLiteral, GetAttr, SetAttr, LoadStatic,
    InitStatic, TupleGet, TupleSet, IncRef, DecRef, Call, MethodCall, Cast,
    Box, Unbox, RaiseStandardError, CallC, Truncate, LoadGlobal, IntOp, ComparisonOp,
    LoadMem, SetMem, GetElementPtr, LoadAddress, KeepAlive, Register, Integer,
    BaseAssign
)
from mypyc.ir.rtypes import RType, RPrimitive, RUnion, is_object_rprimitive, RInstance, RArray, int_rprimitive, list_rprimitive, dict_rprimitive, set_rprimitive, range_rprimitive, str_rprimitive, bytes_rprimitive, tuple_rprimitive
from mypyc.ir.func_ir import FuncIR, FUNC_STATICMETHOD


class FnError(object):
    def __init__(self, source: Union[Op, BasicBlock], desc: str) -> None:
        self.source = source
        self.desc = desc

    def __eq__(self, other: object) -> bool:
        return isinstance(other, FnError) and self.source == other.source and \
            self.desc == other.desc

    def __repr__(self) -> str:
        return f"FnError(source={self.source}, desc={self.desc})"


def check_func_ir(fn: FuncIR) -> List[FnError]:
    """Applies validations to a given function ir and returns a list of errors found."""
    errors = []

    op_set = set()

    for block in fn.blocks:
        if not block.terminated:
            errors.append(FnError(
                source=block.ops[-1] if block.ops else block,
                desc="Block not terminated",
            ))
        for op in block.ops[:-1]:
            if isinstance(op, ControlOp):
                errors.append(FnError(
                    source=op,
                    desc="Block has operations after control op",
                ))

            if op in op_set:
                errors.append(FnError(
                    source=op,
                    desc="Func has a duplicate op",
                ))
            op_set.add(op)

    errors.extend(check_op_sources_valid(fn))
    if errors:
        return errors

    op_checker = OpChecker(fn)
    for block in fn.blocks:
        for op in block.ops:
            op.accept(op_checker)

    return op_checker.errors


class IrCheckException(Exception):
    pass


def assert_func_ir_valid(fn: FuncIR) -> None:
    errors = check_func_ir(fn)
    if errors:
        raise IrCheckException("Internal error: Generated invalid IR: \n" + "\n".join(
            format_func(fn, [(e.source, e.desc) for e in errors])),
        )


def check_op_sources_valid(fn: FuncIR) -> List[FnError]:
    errors = []
    valid_ops: Set[Op] = set()
    valid_registers: Set[Register] = set()

    for block in fn.blocks:
        valid_ops.update(block.ops)

        valid_registers.update([
            op.dest for op in block.ops if isinstance(op, BaseAssign)
        ])

    valid_registers.update(fn.arg_regs)

    for block in fn.blocks:
        for op in block.ops:
            for source in op.sources():
                if isinstance(source, Integer):
                    pass
                elif isinstance(source, Op):
                    if source not in valid_ops:
                        errors.append(FnError(source=op, desc=f"Invalid op reference to op of type {type(source).__name__}"))
                elif isinstance(source, Register):
                    if source not in valid_registers:
                        errors.append(FnError(source=op, desc=f"Invalid op reference to register {source.name}"))

    return errors


disjoint_types = set([
    int_rprimitive.name,
    bytes_rprimitive.name,
    str_rprimitive.name,
    dict_rprimitive.name,
    list_rprimitive.name,
    set_rprimitive.name,
    tuple_rprimitive.name,
    range_rprimitive.name,
])


def can_coerce_to(src: RType, dest: RType) -> bool:
    """Check if src can be assigned to dest_rtype.
    
    Currently okay to have false positives.
    """
    if isinstance(dest, RUnion):
        return any(can_coerce_to(src, d) for d in dest.items)

    if isinstance(dest, RPrimitive):
        if isinstance(src, RPrimitive):
            # If either src or dest is a disjoint type, then they must both be.
            if src.name in disjoint_types and dest.name in disjoint_types:
                return src.name == dest.name
            return src.size == dest.size
        if isinstance(src, RInstance):
            return is_object_rprimitive(dest)
        if isinstance(src, RUnion):
            # IR doesn't have the ability to narrow unions based on
            # control flow, so cannot be a strict all() here.
            return any(can_coerce_to(s, dest) for s in src.items)
        return False

    return True


class OpChecker(OpVisitor[None]):
    def __init__(self, parent_fn: FuncIR) -> None:
        self.parent_fn = parent_fn
        self.errors: List[FnError] = []

    def fail(self, source: Op, desc: str) -> None:
        self.errors.append(FnError(source=source, desc=desc))

    def check_control_op_targets(self, op: ControlOp) -> None:
        for target in op.targets():
            if target not in self.parent_fn.blocks:
                self.fail(source=op, desc=f"Invalid control operation target: {target.label}")

    def check_type_coercion(self, op: Op, src: RType, dest: RType) -> None:
        if not can_coerce_to(src, dest):
            self.fail(source=op, desc=f"Cannot coerce source type {src.name} to dest type {dest.name}")

    def visit_goto(self, op: Goto) -> None:
        self.check_control_op_targets(op)

    def visit_branch(self, op: Branch) -> None:
        self.check_control_op_targets(op)

    def visit_return(self, op: Return) -> None:
        self.check_type_coercion(op, op.value.type, self.parent_fn.decl.sig.ret_type)

    def visit_unreachable(self, op: Unreachable) -> None:
        # Unreachables are checked at a higher level since validation
        # requires access to the entire basic block.
        pass

    def visit_assign(self, op: Assign) -> None:
        self.check_type_coercion(op, op.src.type, op.dest.type)

    def visit_assign_multi(self, op: AssignMulti) -> None:
        for src in op.src:
            assert isinstance(op.dest.type, RArray)
            self.check_type_coercion(op, src.type, op.dest.type.item_type)

    def visit_load_error_value(self, op: LoadErrorValue) -> None:
        # Currently it is assumed that all types have an error value.
        # Once this is fixed we can validate that the rtype here actually
        # has an error value.
        pass

    def check_tuple_items_valid_literals(self, op: LoadLiteral, t: Tuple[object, ...]) -> None:
        for x in t:
            if x is not None and not isinstance(x, (str, bytes, bool, int, float, complex, tuple)):
                self.fail(op, f"Invalid type for item of tuple literal: {type(x)})")
            if isinstance(x, tuple):
                self.check_tuple_items_valid_literals(op, x)

    def visit_load_literal(self, op: LoadLiteral) -> None:
        expected_type = None
        if op.value is None:
            expected_type = "builtins.object"
        elif isinstance(op.value, int):
            expected_type = "builtins.int"
        elif isinstance(op.value, str):
            expected_type = "builtins.str"
        elif isinstance(op.value, bytes):
            expected_type = "builtins.bytes"
        elif isinstance(op.value, bool):
            expected_type = "builtins.object"
        elif isinstance(op.value, float):
            expected_type = "builtins.float"
        elif isinstance(op.value, complex):
            expected_type = "builtins.object"
        elif isinstance(op.value, tuple):
            expected_type = "builtins.tuple"
            self.check_tuple_items_valid_literals(op, op.value)

        assert expected_type is not None, "Missed a case for LoadLiteral check"
            
        if op.type.name not in [expected_type, "builtins.object"]:
            self.fail(op, f"Invalid literal value for type: value has type {expected_type}, but op has type {op.type.name}") 

    def visit_get_attr(self, op: GetAttr) -> None:
        # Nothing to do.
        pass

    def visit_set_attr(self, op: SetAttr) -> None:
        # Nothing to do.
        pass

    # Static operations cannot be checked at the function level.
    def visit_load_static(self, op: LoadStatic) -> None:
        pass

    def visit_init_static(self, op: InitStatic) -> None:
        pass

    def visit_tuple_get(self, op: TupleGet) -> None:
        # Nothing to do.
        pass

    def visit_tuple_set(self, op: TupleSet) -> None:
        # Nothing to do.
        pass

    def visit_inc_ref(self, op: IncRef) -> None:
        # Nothing to do.
        pass

    def visit_dec_ref(self, op: DecRef) -> None:
        # Nothing to do.
        pass

    def visit_call(self, op: Call) -> None:
        # Length is checked in constructor, and return type is set
        # in a way that can't be incorrect
        for arg_value, arg_runtime in zip(op.args, op.fn.sig.args):
            self.check_type_coercion(op, arg_value.type, arg_runtime.type)

    def visit_method_call(self, op: MethodCall) -> None:
        # Similar to above, but we must look up method first.
        method_decl = op.receiver_type.class_ir.method_decl(op.method)
        if method_decl.kind == FUNC_STATICMETHOD:
            decl_index = 0
        else:
            decl_index = 1

        if len(op.args) + decl_index != len(method_decl.sig.args):
            self.fail(op, "Incorrect number of args for method call.")

        # Skip the receiver argument (self)
        for arg_value, arg_runtime in zip(op.args, method_decl.sig.args[decl_index:]):
            self.check_type_coercion(op, arg_value.type, arg_runtime.type)

    def visit_cast(self, op: Cast) -> None:
        pass

    def visit_box(self, op: Box) -> None:
        pass

    def visit_unbox(self, op: Unbox) -> None:
        pass

    def visit_raise_standard_error(self, op: RaiseStandardError) -> None:
        pass

    def visit_call_c(self, op: CallC) -> None:
        pass

    def visit_truncate(self, op: Truncate) -> None:
        pass

    def visit_load_global(self, op: LoadGlobal) -> None:
        pass

    def visit_int_op(self, op: IntOp) -> None:
        pass

    def visit_comparison_op(self, op: ComparisonOp) -> None:
        pass

    def visit_load_mem(self, op: LoadMem) -> None:
        pass

    def visit_set_mem(self, op: SetMem) -> None:
        pass

    def visit_get_element_ptr(self, op: GetElementPtr) -> None:
        pass

    def visit_load_address(self, op: LoadAddress) -> None:
        pass

    def visit_keep_alive(self, op: KeepAlive) -> None:
        pass
