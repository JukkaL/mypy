"""Bool register elimination optimization.

Example input:

  L1:
    r0 = f()
    b = r0
    goto L3
  L2:
    r1 = g()
    b = r1
    goto L3
  L3:
    if b goto L4 else goto L5

The register b is redundant and we replace the assignments with two copies of
the branch in L3:

  L1:
    r0 = f()
    if r0 goto L4 else goto L5
  L2:
    r1 = g()
    if r1 goto L4 else goto L5

This helps generate simpler IR for tagged integers comparisons, for example.
"""

from __future__ import annotations

from mypyc.ir.func_ir import FuncIR
from mypyc.ir.ops import Assign, BasicBlock, Branch, Goto, Register, Unreachable
from mypyc.irbuild.ll_builder import LowLevelIRBuilder
from mypyc.options import CompilerOptions
from mypyc.transform.ir_transform import IRTransform


def do_flag_elimination(fn: FuncIR, options: CompilerOptions) -> None:
    # Find registers that are used exactly once as source, and in a branch.
    counts: dict[Register, int] = {}
    branches: dict[Register, Branch] = {}
    labels: dict[Register, BasicBlock] = {}
    for block in fn.blocks:
        for i, op in enumerate(block.ops):
            for src in op.sources():
                if isinstance(src, Register):
                    counts[src] = counts.get(src, 0) + 1
            if i == 0 and isinstance(op, Branch) and isinstance(op.value, Register):
                branches[op.value] = op
                labels[op.value] = block

    # Based on these we can find the candidate registers.
    candidates: set[Register] = {
        r for r in branches if counts.get(r, 0) == 1 and r not in fn.arg_regs
    }

    # Remove candidates with invalid assignments.
    for block in fn.blocks:
        for i, op in enumerate(block.ops):
            if isinstance(op, Assign) and op.dest in candidates:
                next_op = block.ops[i + 1]
                if not (isinstance(next_op, Goto) and next_op.label is labels[op.dest]):
                    # Not right
                    candidates.remove(op.dest)

    b = LowLevelIRBuilder(None, options)
    t = FlagEliminationTransform(b, {x: y for x, y in branches.items() if x in candidates})
    t.transform_blocks(fn.blocks)
    fn.blocks = b.blocks


class FlagEliminationTransform(IRTransform):
    def __init__(self, builder: LowLevelIRBuilder, m: dict[Register, Branch]) -> None:
        super().__init__(builder)
        self.m = m
        self.rev = {x for x in m.values()}

    def visit_assign(self, op: Assign) -> None:
        orig = self.m.get(op.dest)
        if orig:
            b = Branch(op.src, orig.true, orig.false, orig.op, orig.line, rare=orig.rare)
            b.negated = orig.negated
            b.traceback_entry = orig.traceback_entry
            self.add(b)
        else:
            self.add(op)

    def visit_goto(self, op: Goto) -> None:
        # This is a no-op if basic block already terminated
        self.builder.goto(op.label)

    def visit_branch(self, op: Branch) -> None:
        if op in self.rev:
            self.add(Unreachable())
        else:
            self.add(op)
