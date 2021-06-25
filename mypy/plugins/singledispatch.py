from mypy.plugins.common import add_method_to_class
from mypy.nodes import ARG_POS, Argument, Block, ClassDef, SymbolTable, TypeInfo, Var
from mypy.checker import TypeChecker
from mypy.subtypes import is_subtype
from mypy.types import (
    AnyType, CallableType, Instance, NoneType, Overloaded, Type, TypeOfAny, get_proper_type,
    UnionType
)
from mypy.plugin import CheckerPluginInterface, FunctionContext, MethodContext, MethodSigContext
from typing import Dict, List, NamedTuple, Optional, Sequence, TypeVar, cast
from typing_extensions import Final, TypedDict

SingledispatchInfo = TypedDict('SingledispatchInfo', {
    'fallback': CallableType,
    # dict of dispatch type to the registered function
    # dispatch type is stored separately from function because the dispatch type might be different
    # from the type of the first argument if a type is passed as an argument to register
    # TODO: use Instance for register type because register requires register type to be subclass
    # of type
    'registered': Dict[Type, CallableType],
})

RegisterCallableInfo = NamedTuple('RegisterCallableInfo', [
    ('register_type', Type),
    ('singledispatch_obj', Instance),
])

SINGLEDISPATCH_TYPE = 'functools._SingleDispatchCallable'

# key that we use for everything we store in TypeInfo metadata
METADATA_KEY = 'singledispatch'

SINGLEDISPATCH_REGISTER_METHOD = '{}.register'.format(SINGLEDISPATCH_TYPE)  # type: Final

SINGLEDISPATCH_CALLABLE_CALL_METHOD = '{}.__call__'.format(SINGLEDISPATCH_TYPE)  # type: Final


def get_singledispatch_info(typ: Instance) -> 'SingledispatchInfo':
    return typ.type.metadata[METADATA_KEY]  # type: ignore


T = TypeVar('T')


def get_first_arg(args: List[List[T]]) -> Optional[T]:
    """Get the element that corresponds to the first argument passed to the function"""
    if args and args[0]:
        return args[0][0]
    return None


REGISTER_RETURN_CLASS = '_SingleDispatchRegisterCallable'

REGISTER_CALLABLE_CALL_METHOD = 'functools.{}.__call__'.format(
    REGISTER_RETURN_CLASS
)  # type: Final


def make_fake_register_class_instance(api: CheckerPluginInterface, type_args: Sequence[Type]
                                      ) -> Instance:
    defn = ClassDef(REGISTER_RETURN_CLASS, Block([]))
    defn.fullname = 'functools.{}'.format(REGISTER_RETURN_CLASS)
    info = TypeInfo(SymbolTable(), defn, "functools")
    obj_type = api.named_generic_type('builtins.object', []).type
    info.bases = [Instance(obj_type, [])]
    info.mro = [info, obj_type]
    defn.info = info

    func_arg = Argument(Var('name'), AnyType(TypeOfAny.implementation_artifact), None, ARG_POS)
    add_method_to_class(api, defn, '__call__', [func_arg], NoneType())

    return Instance(info, type_args)


def create_singledispatch_function_callback(ctx: FunctionContext) -> Type:
    """Called for functools.singledispatch"""
    # TODO: check that there's only one argument
    func_type = get_proper_type(get_first_arg(ctx.arg_types))
    if isinstance(func_type, CallableType):
        metadata = {
            'fallback': func_type,
            'registered': {}
        }  # type: SingledispatchInfo

        # singledispatch returns an instance of functools._SingleDispatchCallable according to
        # typeshed
        singledispatch_obj = get_proper_type(ctx.default_return_type)
        assert isinstance(singledispatch_obj, Instance)
        # mypy shows an error when assigning TypedDict to a regular dict
        singledispatch_obj.type.metadata[METADATA_KEY] = metadata  # type: ignore

    return ctx.default_return_type


def singledispatch_register_callback(ctx: MethodContext) -> Type:
    """Called for functools._SingleDispatchCallable.register"""
    if isinstance(ctx.type, Instance):
        # TODO: check that there's only one argument
        first_arg_type = get_proper_type(get_first_arg(ctx.arg_types))
        if isinstance(first_arg_type, (CallableType, Overloaded)) and first_arg_type.is_type_obj():
            # HACK: We receieved a class as an argument to register. We need to be able
            # to access the function that register is being applied to, and the typeshed definition
            # of register has it return a generic Callable, so we create a new
            # SingleDispatchRegisterCallable class, define a __call__ method, and then add a
            # plugin hook for that.

            # is_subtype doesn't work when the right type is Overloaded, so we need the
            # actual type
            register_type = first_arg_type.items()[0].ret_type
            type_args = RegisterCallableInfo(register_type, ctx.type)
            register_callable = make_fake_register_class_instance(
                ctx.api,
                type_args
            )
            return register_callable
        elif isinstance(first_arg_type, CallableType):
            # TODO: do more checking for registered functions
            register_function(ctx.type, first_arg_type)

    # register doesn't modify the function it's used on
    return ctx.default_return_type


def register_function(singledispatch_obj: Instance, func: Type,
                      register_arg: Optional[Type] = None) -> None:

    func = get_proper_type(func)
    if not isinstance(func, CallableType):
        return
    metadata = get_singledispatch_info(singledispatch_obj)
    dispatch_type = get_dispatch_type(func, register_arg)
    if dispatch_type is None:
        # TODO: report an error here that singledispatch requires at least one argument
        # (might want to do the error reporting in get_dispatch_type)
        return
    # TODO: report an error if we're overwriting another function (which would happen if multiple
    # registered functions have the same dispatch type)
    metadata['registered'][dispatch_type] = func


def get_dispatch_type(func: CallableType, register_arg: Optional[Type]) -> Optional[Type]:
    if register_arg is not None:
        return register_arg
    if func.arg_types:
        return func.arg_types[0]
    return None


def call_singledispatch_function_after_register_argument(ctx: MethodContext) -> Type:
    """Called on the function after passing a type to register"""
    register_callable = ctx.type
    if isinstance(register_callable, Instance):
        type_args = RegisterCallableInfo(*register_callable.args)  # type: ignore
        func = get_first_arg(ctx.arg_types)
        if func is not None:
            register_function(type_args.singledispatch_obj, func, type_args.register_type)
    return ctx.default_return_type


def rename_func(func: CallableType, new_name: CallableType) -> CallableType:
    """Return a new CallableType that is `function` with the name of `new_name`"""
    if new_name.name is not None:
        signature_used = func.with_name(new_name.name)
    else:
        signature_used = func
    return signature_used


def call_singledispatch_function_callback(ctx: MethodSigContext) -> CallableType:
    """Called for functools._SingleDispatchCallable.__call__"""
    if not isinstance(ctx.type, Instance):
        return ctx.default_signature
    metadata = get_singledispatch_info(ctx.type)
    first_arg = get_first_arg(ctx.args)
    if first_arg is None:
        return ctx.default_signature
    # TODO: find a way to get the type of the first argument with the public API
    # (expr_checker probably isn't part of the public API)
    passed_type = cast(TypeChecker, ctx.api).expr_checker.accept(first_arg)
    fallback = metadata['fallback']

    # Find all possible implementations that may get called based on the passed type
    impls = get_possible_impls(passed_type, metadata['registered'], fallback)

    # use the fallback's name so that error messages say that the arguments to
    # the fallback are incorrect (instead of saying arguments to the registered
    # implementation are incorrect)
    possible_impls = list(rename_func(func, fallback) for func in impls)
    if len(possible_impls) > 1:
        # the type signature technically says we're returning CallableType, but returning
        # Overloaded seems to work fine and there doesn't appear to be a better way of telling
        # mypy that there are multiple possible functions that could get used
        return Overloaded(possible_impls)  # type: ignore
    elif len(possible_impls) == 1:
        return possible_impls[0]
    else:
        # we should have at least included the fallback in possible_impls even if none of the
        # other registered implementations matched
        assert False, 'should have at least one singledispatch implementation'


def get_possible_impls(passed_type: Type, registered: Dict[Type, CallableType],
                       fallback: CallableType) -> List[CallableType]:
    """Get all possible registered implementations that could get called"""
    passed_type = get_proper_type(passed_type)
    impls = []
    if isinstance(passed_type, UnionType):
        for item in passed_type.relevant_items():
            impls.extend(get_possible_impls(item, registered, fallback))
        return impls
    else:
        for dispatch_type, func, in registered.items():
            # TODO: search in the order that singledispatch would (starting with implementations
            # that have the same class as the passed type and going up the mro) - This might pick
            # a more general implementation than would get picked by singledispatch
            if is_subtype(passed_type, dispatch_type):
                impls.append(func)
                return impls
        impls.append(fallback)
    return impls
