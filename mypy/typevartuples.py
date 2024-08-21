"""Helpers for interacting with type var tuples."""

from __future__ import annotations

from typing import Sequence

from mypy.types import (
    AnyType,
    Instance,
    ProperType,
    Type,
    TypeVarLikeType,
    TypeVarTupleType,
    UnpackType,
    get_proper_type,
    split_with_prefix_and_suffix,
)


def split_with_instance(
    typ: Instance,
) -> tuple[tuple[Type, ...], tuple[Type, ...], tuple[Type, ...]]:
    assert typ.type.type_var_tuple_prefix is not None
    assert typ.type.type_var_tuple_suffix is not None
    return split_with_prefix_and_suffix(
        typ.args, typ.type.type_var_tuple_prefix, typ.type.type_var_tuple_suffix
    )


def extract_unpack(types: Sequence[Type]) -> ProperType | None:
    """Given a list of types, extracts either a single type from an unpack, or returns None."""
    if len(types) == 1:
        if isinstance(types[0], UnpackType):
            return get_proper_type(types[0].type)
    return None


def erased_vars(type_vars: Sequence[TypeVarLikeType], type_of_any: int) -> list[Type]:
    args: list[Type] = []
    for tv in type_vars:
        # Valid erasure for *Ts is *tuple[Any, ...], not just Any.
        if isinstance(tv, TypeVarTupleType):
            args.append(UnpackType(tv.tuple_fallback.copy_modified(args=[AnyType(type_of_any)])))
        else:
            args.append(AnyType(type_of_any))
    return args
