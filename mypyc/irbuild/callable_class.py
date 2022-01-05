"""Generate a class that represents a nested function.

The class defines __call__ for calling the function and allows access to
non-local variables defined in outer scopes.
"""

from typing import List

from mypy.nodes import LambdaExpr

from mypyc.common import SELF_NAME, ENV_ATTR_NAME
from mypyc.ir.ops import BasicBlock, Return, Call, SetAttr, Value, Register
from mypyc.ir.rtypes import RInstance, object_rprimitive, none_rprimitive, str_rprimitive
from mypyc.ir.func_ir import FuncIR, FuncSignature, RuntimeArg, FuncDecl
from mypyc.ir.class_ir import ClassIR
from mypyc.irbuild.builder import IRBuilder
from mypyc.irbuild.context import FuncInfo, ImplicitClass
from mypyc.primitives.misc_ops import method_new_op


def setup_callable_class(builder: IRBuilder) -> None:
    """Generate an (incomplete) callable class representing function.

    This can be a nested function or a function within a non-extension
    class.  Also set up the 'self' variable for that class.

    This takes the most recently visited function and returns a
    ClassIR to represent that function. Each callable class contains
    an environment attribute which points to another ClassIR
    representing the environment class where some of its variables can
    be accessed.

    Note that some methods, such as '__call__', are not yet
    created here. Use additional functions, such as
    add_call_to_callable_class(), to add them.

    Return a newly constructed ClassIR representing the callable
    class for the nested function.
    """
    # Check to see that the name has not already been taken. If so,
    # rename the class. We allow multiple uses of the same function
    # name because this is valid in if-else blocks. Example:
    #
    #     if True:
    #         def foo():          ---->    foo_obj()
    #             return True
    #     else:
    #         def foo():          ---->    foo_obj_0()
    #             return False
    name = base_name = '{}_obj'.format(builder.fn_info.namespaced_name())
    count = 0
    while name in builder.callable_class_names:
        name = base_name + '_' + str(count)
        count += 1
    builder.callable_class_names.add(name)

    # Define the actual callable class ClassIR, and set its
    # environment to point at the previously defined environment
    # class.
    callable_class_ir = ClassIR(name, builder.module_name, is_generated=True)

    # The functools @wraps decorator attempts to call setattr on
    # nested functions, so we create a dict for these nested
    # functions.
    # https://github.com/python/cpython/blob/3.7/Lib/functools.py#L58
    if builder.fn_info.is_nested:
        callable_class_ir.has_dict = True

    # If the enclosing class doesn't contain nested (which will happen if
    # this is a toplevel lambda), don't set up an environment.
    if builder.fn_infos[-2].contains_nested:
        callable_class_ir.attributes[ENV_ATTR_NAME] = RInstance(
            builder.fn_infos[-2].env_class
        )
    callable_class_ir.mro = [callable_class_ir]
    builder.fn_info.callable_class = ImplicitClass(callable_class_ir)
    builder.classes.append(callable_class_ir)

    # Add a 'self' variable to the environment of the callable class,
    # and store that variable in a register to be accessed later.
    self_target = builder.add_self_to_env(callable_class_ir)
    builder.fn_info.callable_class.self_reg = builder.read(self_target, builder.fn_info.fitem.line)


def add_init_to_callable_class(builder: IRBuilder, fn_info: FuncInfo) -> None:
    """Generate a '__init__' method for a callable class representing a nested function.

    The init method simply adds back the '__name__' attribute which non-nested functions
    do have.
    """
    class_ir = fn_info.callable_class.ir
    class_ir.needs_getseters = True
    class_ir.attributes['__name__'] = str_rprimitive
    fn_name_value = '<lambda>' if isinstance(fn_info.fitem, LambdaExpr) else fn_info.name

    with builder.enter_method(class_ir, '__init__', none_rprimitive, fn_info):
        fn_name = builder.load_str(fn_name_value)
        builder.add(SetAttr(builder.self(), '__name__', fn_name, fn_info.fitem.line))
        builder.add(Return(builder.none()))


def add_call_to_callable_class(builder: IRBuilder,
                               args: List[Register],
                               blocks: List[BasicBlock],
                               sig: FuncSignature,
                               fn_info: FuncInfo) -> FuncIR:
    """Generate a '__call__' method for a callable class representing a nested function.

    This takes the blocks and signature associated with a function
    definition and uses those to build the '__call__' method of a
    given callable class, used to represent that function.
    """
    # Since we create a method, we also add a 'self' parameter.
    sig = FuncSignature((RuntimeArg(SELF_NAME, object_rprimitive),) + sig.args, sig.ret_type)
    call_fn_decl = FuncDecl('__call__', fn_info.callable_class.ir.name, builder.module_name, sig)
    call_fn_ir = FuncIR(call_fn_decl, args, blocks,
                        fn_info.fitem.line, traceback_name=fn_info.fitem.name)
    fn_info.callable_class.ir.methods['__call__'] = call_fn_ir
    fn_info.callable_class.ir.method_decls['__call__'] = call_fn_decl
    return call_fn_ir


def add_get_to_callable_class(builder: IRBuilder, fn_info: FuncInfo) -> None:
    """Generate the '__get__' method for a callable class."""
    line = fn_info.fitem.line
    with builder.enter_method(
            fn_info.callable_class.ir, '__get__', object_rprimitive, fn_info,
            self_type=object_rprimitive):
        instance = builder.add_argument('instance', object_rprimitive)
        builder.add_argument('owner', object_rprimitive)

        # If accessed through the class, just return the callable
        # object. If accessed through an object, create a new bound
        # instance method object.
        instance_block, class_block = BasicBlock(), BasicBlock()
        comparison = builder.translate_is_op(
            builder.read(instance), builder.none_object(), 'is', line
        )
        builder.add_bool_branch(comparison, class_block, instance_block)

        builder.activate_block(class_block)
        builder.add(Return(builder.self()))

        builder.activate_block(instance_block)
        builder.add(Return(builder.call_c(method_new_op,
                                          [builder.self(), builder.read(instance)], line)))


def instantiate_callable_class(builder: IRBuilder, fn_info: FuncInfo) -> Value:
    """Create an instance of a callable class for a function.

    Calls to the function will actually call this instance.

    Note that fn_info refers to the function being assigned, whereas
    builder.fn_info refers to the function encapsulating the function
    being turned into a callable class.
    """
    fitem = fn_info.fitem
    func_reg = builder.add(Call(fn_info.callable_class.ir.ctor, [], fitem.line))

    # Set the environment attribute of the callable class to point at
    # the environment class defined in the callable class' immediate
    # outer scope. Note that there are three possible environment
    # class registers we may use. This depends on what the encapsulating
    # (parent) function is:
    #
    # - A nested function: the callable class is instantiated
    #   from the current callable class' '__call__' function, and hence
    #   the callable class' environment register is used.
    # - A generator function: the callable class is instantiated
    #   from the '__next__' method of the generator class, and hence the
    #   environment of the generator class is used.
    # - Regular function: we use the environment of the original function.
    curr_env_reg = None
    if builder.fn_info.is_generator:
        curr_env_reg = builder.fn_info.generator_class.curr_env_reg
    elif builder.fn_info.is_nested:
        curr_env_reg = builder.fn_info.callable_class.curr_env_reg
    elif builder.fn_info.contains_nested:
        curr_env_reg = builder.fn_info.curr_env_reg
    if curr_env_reg:
        builder.add(SetAttr(func_reg, ENV_ATTR_NAME, curr_env_reg, fitem.line))
    return func_reg
