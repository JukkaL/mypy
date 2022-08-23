"""Utilities for type argument inference."""

from __future__ import annotations

from typing import NamedTuple, Sequence

from mypy.constraints import (
    SUBTYPE_OF,
    SUPERTYPE_OF,
    infer_constraints,
    infer_constraints_for_callable,
)
from mypy.nodes import ArgKind
from mypy.solve import solve_constraints
from mypy.types import CallableType, Instance, Type, TypeVarId


class ArgumentInferContext(NamedTuple):
    """Type argument inference context.

    We need this because we pass around ``Mapping`` and ``Iterable`` types.
    These types are only known by ``TypeChecker`` itself.
    It is required for ``*`` and ``**`` argument inference.

    https://github.com/python/mypy/issues/11144
    """

    mapping_type: Instance
    iterable_type: Instance


def infer_function_type_arguments(
    callee_type: CallableType,
    arg_types: Sequence[Type | None],
    arg_kinds: list[ArgKind],
    formal_to_actual: list[list[int]],
    context: ArgumentInferContext,
    strict: bool = True,
) -> list[Type | None]:
    """Infer the type arguments of a generic function.

    Return an array of lower bound types for the type variables -1 (at
    index 0), -2 (at index 1), etc. A lower bound is None if a value
    could not be inferred.

    Arguments:
      callee_type: the target generic function
      arg_types: argument types at the call site (each optional; if None,
                 we are not considering this argument in the current pass)
      arg_kinds: nodes.ARG_* values for arg_types
      formal_to_actual: mapping from formal to actual variable indices
    """
    # Infer constraints.
    constraints = infer_constraints_for_callable(
        callee_type, arg_types, arg_kinds, formal_to_actual, context
    )

    # Solve constraints.
    type_vars = callee_type.type_var_ids()
    return solve_constraints(type_vars, constraints, strict)


def infer_type_arguments(
    type_var_ids: list[TypeVarId], template: Type, actual: Type, is_supertype: bool = False
) -> list[Type | None]:
    # Like infer_function_type_arguments, but only match a single type
    # against a generic type.
    constraints = infer_constraints(template, actual, SUPERTYPE_OF if is_supertype else SUBTYPE_OF)
    return solve_constraints(type_var_ids, constraints)
