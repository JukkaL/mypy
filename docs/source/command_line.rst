.. _command-line:

.. program:: mypy

The mypy command line
=====================

This section documents mypy's command line interface. You can view
a quick summary of the available flags by running :option:`mypy --help`.

.. note::

   Command line flags are liable to change between releases.


Specifying what to type check
*****************************

By default, you can specify what code you want mypy to type check
by passing in the paths to what you want to have type checked::

    $ mypy foo.py bar.py some_directory

Note that directories are checked recursively.

Mypy also lets you specify what code to type check in several other
ways. A short summary of the relevant flags is included below:
for full details, see :ref:`running-mypy`.

.. option:: -m MODULE, --module MODULE

    Asks mypy to type check the provided module. This flag may be
    repeated multiple times.

    Mypy *will not* recursively type check any submodules of the provided
    module.

.. option:: -p PACKAGE, --package PACKAGE

    Asks mypy to type check the provided package. This flag may be
    repeated multiple times.

    Mypy *will* recursively type check any submodules of the provided
    package. This flag is identical to :option:`--module` apart from this
    behavior.

.. option:: -c PROGRAM_TEXT, --command PROGRAM_TEXT

    Asks mypy to type check the provided string as a program.


.. option:: --exclude

    A regular expression that matches file names, directory names and paths
    which mypy should ignore while recursively discovering files to check.
    Use forward slashes on all platforms.

    For instance, to avoid discovering any files named `setup.py` you could
    pass ``--exclude '/setup\.py$'``. Similarly, you can ignore discovering
    directories with a given name by e.g. ``--exclude /build/`` or
    those matching a subpath with ``--exclude /project/vendor/``.

    Note that this flag only affects recursive discovery, that is, when mypy is
    discovering files within a directory tree or submodules of a package to
    check. If you pass a file or module explicitly it will still be checked. For
    instance, ``mypy --exclude '/setup.py$' but_still_check/setup.py``.

    Note that mypy will never recursively discover files and directories named
    "site-packages", "node_modules" or "__pycache__", or those whose name starts
    with a period, exactly as ``--exclude
    '/(site-packages|node_modules|__pycache__|\..*)/$'`` would. Mypy will also
    never recursively discover files with extensions other than ``.py`` or
    ``.pyi``.


Optional arguments
******************

.. option:: -h, --help

    Show help message and exit.

.. option:: -v, --verbose

    More verbose messages.

.. option:: -V, --version

    Show program's version number and exit.

.. _config-file-flag:

Config file
***********

.. option:: --config-file CONFIG_FILE

    This flag makes mypy read configuration settings from the given file.

    By default settings are read from ``mypy.ini``, ``.mypy.ini``, ``pyproject.toml``, or ``setup.cfg``
    in the current directory. Settings override mypy's built-in defaults and
    command line flags can override settings.

    Specifying :option:`--config-file= <--config-file>` (with no filename) will ignore *all*
    config files.

    See :ref:`config-file` for the syntax of configuration files.

.. option:: --warn-unused-configs

    This flag makes mypy warn about unused ``[mypy-<pattern>]`` config
    file sections.
    (This requires turning off incremental mode using :option:`--no-incremental`.)


.. _import-discovery:

Import discovery
****************

The following flags customize how exactly mypy discovers and follows
imports.

.. option:: --namespace-packages

    This flag enables import discovery to use namespace packages (see
    :pep:`420`).  In particular, this allows discovery of imported
    packages that don't have an ``__init__.py`` (or ``__init__.pyi``)
    file.

    Namespace packages are found (using the PEP 420 rules, which
    prefers "classic" packages over namespace packages) along the
    module search path -- this is primarily set from the source files
    passed on the command line, the ``MYPYPATH`` environment variable,
    and the :confval:`mypy_path` config option.

    This flag affects how mypy finds modules and packages explicitly passed on
    the command line. It also affects how mypy determines fully qualified module
    names for files passed on the command line. See :ref:`Mapping file paths to
    modules <mapping-paths-to-modules>` for details.

.. option:: --explicit-package-bases

    This flag tells mypy that top-level packages will be based in either the
    current directory, or a member of the ``MYPYPATH`` environment variable or
    :confval:`mypy_path` config option. This option is only useful in
    conjunction with :option:`--namespace-packages`. See :ref:`Mapping file
    paths to modules <mapping-paths-to-modules>` for details.

.. option:: --ignore-missing-imports

    This flag makes mypy ignore all missing imports. It is equivalent
    to adding ``# type: ignore`` comments to all unresolved imports
    within your codebase.

    Note that this flag does *not* suppress errors about missing names
    in successfully resolved modules. For example, if one has the
    following files::

        package/__init__.py
        package/mod.py

    Then mypy will generate the following errors with :option:`--ignore-missing-imports`:

    .. code-block:: python

        import package.unknown      # No error, ignored
        x = package.unknown.func()  # OK. 'func' is assumed to be of type 'Any'

        from package import unknown          # No error, ignored
        from package.mod import NonExisting  # Error: Module has no attribute 'NonExisting'

    For more details, see :ref:`ignore-missing-imports`.

.. option:: --follow-imports {normal,silent,skip,error}

    This flag adjusts how mypy follows imported modules that were not
    explicitly passed in via the command line.

    The default option is ``normal``: mypy will follow and type check
    all modules. For more information on what the other options do,
    see :ref:`Following imports <follow-imports>`.

.. option:: --follow-imports-for-stubs

    This flag will cause mypy to respect the ``--follow-imports``
    setting even for stub (``.pyi``) files.

    Used in conjunction with ``--follow-imports=skip``, this can be used
    to suppress the import of modules from ``typeshed``, replacing them
    with ``Any``.

    Used in conjunction with ``--follow-imports=error``, this can be used
    to make any use of a ``typeshed`` module an error.

.. option:: --python-executable EXECUTABLE

    This flag will have mypy collect type information from :pep:`561`
    compliant packages installed for the Python executable ``EXECUTABLE``.
    If not provided, mypy will use PEP 561 compliant packages installed for
    the Python executable running mypy.

    See :ref:`installed-packages` for more on making PEP 561 compliant packages.

.. option:: --no-site-packages

    This flag will disable searching for :pep:`561` compliant packages. This
    will also disable searching for a usable Python executable.

    Use this  flag if mypy cannot find a Python executable for the version of
    Python being checked, and you don't need to use PEP 561 typed packages.
    Otherwise, use :option:`--python-executable`.

.. option:: --no-silence-site-packages

    By default, mypy will suppress any error messages generated within :pep:`561`
    compliant packages. Adding this flag will disable this behavior.


.. _platform-configuration:

Platform configuration
**********************

By default, mypy will assume that you intend to run your code using the same
operating system and Python version you are using to run mypy itself. The
following flags let you modify this behavior.

For more information on how to use these flags, see :ref:`version_and_platform_checks`.

.. option:: --python-version X.Y

    This flag will make mypy type check your code as if it were
    run under Python version X.Y. Without this option, mypy will default to using
    whatever version of Python is running mypy. Note that the :option:`-2` and
    :option:`--py2` flags are aliases for :option:`--python-version 2.7 <--python-version>`.

    This flag will attempt to find a Python executable of the corresponding
    version to search for :pep:`561` compliant packages. If you'd like to
    disable this, use the :option:`--no-site-packages` flag (see
    :ref:`import-discovery` for more details).

.. option:: -2, --py2

    Equivalent to running :option:`--python-version 2.7 <--python-version>`.

    .. note::

        To check Python 2 code with mypy, you'll need to install mypy with
        ``pip install 'mypy[python2]'``.

.. option:: --platform PLATFORM

    This flag will make mypy type check your code as if it were
    run under the given operating system. Without this option, mypy will
    default to using whatever operating system you are currently using.

    The ``PLATFORM`` parameter may be any string supported by
    :py:data:`sys.platform`.

.. _always-true:

.. option:: --always-true NAME

    This flag will treat all variables named ``NAME`` as
    compile-time constants that are always true.  This flag may
    be repeated.

.. option:: --always-false NAME

    This flag will treat all variables named ``NAME`` as
    compile-time constants that are always false.  This flag may
    be repeated.


.. _disallow-dynamic-typing:

Disallow dynamic typing
***********************

The ``Any`` type is used represent a value that has a :ref:`dynamic type <dynamic-typing>`.
The ``--disallow-any`` family of flags will disallow various uses of the ``Any`` type in
a module -- this lets us strategically disallow the use of dynamic typing in a controlled way.

The following options are available:

.. option:: --disallow-any-unimported

    This flag disallows usage of types that come from unfollowed imports
    (such types become aliases for ``Any``). Unfollowed imports occur either
    when the imported module does not exist or when :option:`--follow-imports=skip <--follow-imports>`
    is set.

.. option:: --disallow-any-expr

    This flag disallows all expressions in the module that have type ``Any``.
    If an expression of type ``Any`` appears anywhere in the module
    mypy will output an error unless the expression is immediately
    used as an argument to :py:func:`~typing.cast` or assigned to a variable with an
    explicit type annotation.

    In addition, declaring a variable of type ``Any``
    or casting to type ``Any`` is not allowed. Note that calling functions
    that take parameters of type ``Any`` is still allowed.

.. option:: --disallow-any-decorated

    This flag disallows functions that have ``Any`` in their signature
    after decorator transformation.

.. option:: --disallow-any-explicit

    This flag disallows explicit ``Any`` in type positions such as type
    annotations and generic type parameters.

.. option:: --disallow-any-generics

    This flag disallows usage of generic types that do not specify explicit
    type parameters. Moreover, built-in collections (such as :py:class:`list` and
    :py:class:`dict`) become disallowed as you should use their aliases from the :py:mod:`typing`
    module (such as :py:class:`List[int] <typing.List>` and :py:class:`Dict[str, str] <typing.Dict>`).

.. option:: --disallow-subclassing-any

    This flag reports an error whenever a class subclasses a value of
    type ``Any``.  This may occur when the base class is imported from
    a module that doesn't exist (when using
    :option:`--ignore-missing-imports`) or is
    ignored due to :option:`--follow-imports=skip <--follow-imports>` or a
    ``# type: ignore`` comment on the ``import`` statement.

    Since the module is silenced, the imported class is given a type of ``Any``.
    By default mypy will assume that the subclass correctly inherited
    the base class even though that may not actually be the case.  This
    flag makes mypy raise an error instead.


.. _untyped-definitions-and-calls:

Untyped definitions and calls
*****************************

The following flags configure how mypy handles untyped function
definitions or calls.

.. option:: --disallow-untyped-calls

    This flag reports an error whenever a function with type annotations
    calls a function defined without annotations.

.. option:: --disallow-untyped-defs

    This flag reports an error whenever it encounters a function definition
    without type annotations.

.. option:: --disallow-incomplete-defs

    This flag reports an error whenever it encounters a partly annotated
    function definition.

.. option:: --check-untyped-defs

    This flag is less severe than the previous two options -- it type checks
    the body of every function, regardless of whether it has type annotations.
    (By default the bodies of functions without annotations are not type
    checked.)

    It will assume all arguments have type ``Any`` and always infer ``Any``
    as the return type.

.. option:: --disallow-untyped-decorators

    This flag reports an error whenever a function with type annotations
    is decorated with a decorator without annotations.


.. _none-and-optional-handling:

None and Optional handling
**************************

The following flags adjust how mypy handles values of type ``None``.
For more details, see :ref:`no_strict_optional`.

.. _no-implicit-optional:

.. option:: --no-implicit-optional

    This flag causes mypy to stop treating arguments with a ``None``
    default value as having an implicit :py:data:`~typing.Optional` type.

    For example, by default mypy will assume that the ``x`` parameter
    is of type ``Optional[int]`` in the code snippet below since
    the default parameter is ``None``:

    .. code-block:: python

        def foo(x: int = None) -> None:
            print(x)

    If this flag is set, the above snippet will no longer type check:
    we must now explicitly indicate that the type is ``Optional[int]``:

    .. code-block:: python

        def foo(x: Optional[int] = None) -> None:
            print(x)

.. option:: --no-strict-optional

    This flag disables strict checking of :py:data:`~typing.Optional`
    types and ``None`` values. With this option, mypy doesn't
    generally check the use of ``None`` values -- they are valid
    everywhere. See :ref:`no_strict_optional` for more about this feature.

    **Note:** Strict optional checking was enabled by default starting in
    mypy 0.600, and in previous versions it had to be explicitly enabled
    using ``--strict-optional`` (which is still accepted).


.. _configuring-warnings:

Configuring warnings
********************

The follow flags enable warnings for code that is sound but is
potentially problematic or redundant in some way.

.. option:: --warn-redundant-casts

    This flag will make mypy report an error whenever your code uses
    an unnecessary cast that can safely be removed.

.. option:: --warn-unused-ignores

    This flag will make mypy report an error whenever your code uses
    a ``# type: ignore`` comment on a line that is not actually
    generating an error message.

    This flag, along with the :option:`--warn-redundant-casts` flag, are both
    particularly useful when you are upgrading mypy. Previously,
    you may have needed to add casts or ``# type: ignore`` annotations
    to work around bugs in mypy or missing stubs for 3rd party libraries.

    These two flags let you discover cases where either workarounds are
    no longer necessary.

.. option:: --no-warn-no-return

    By default, mypy will generate errors when a function is missing
    return statements in some execution paths. The only exceptions
    are when:

    -   The function has a ``None`` or ``Any`` return type
    -   The function has an empty body or a body that is just
        ellipsis (``...``). Empty functions are often used for
        abstract methods.

    Passing in :option:`--no-warn-no-return` will disable these error
    messages in all cases.

.. option:: --warn-return-any

    This flag causes mypy to generate a warning when returning a value
    with type ``Any`` from a function declared with a non-``Any`` return type.

.. option:: --warn-unreachable

    This flag will make mypy report an error whenever it encounters
    code determined to be unreachable or redundant after performing type analysis.
    This can be a helpful way of detecting certain kinds of bugs in your code.

    For example, enabling this flag will make mypy report that the ``x > 7``
    check is redundant and that the ``else`` block below is unreachable.

    .. code-block:: python

        def process(x: int) -> None:
            # Error: Right operand of "or" is never evaluated
            if isinstance(x, int) or x > 7:
                # Error: Unsupported operand types for + ("int" and "str")
                print(x + "bad")
            else:
                # Error: 'Statement is unreachable' error
                print(x + "bad")

    To help prevent mypy from generating spurious warnings, the "Statement is
    unreachable" warning will be silenced in exactly two cases:

    1.  When the unreachable statement is a ``raise`` statement, is an
        ``assert False`` statement, or calls a function that has the :py:data:`~typing.NoReturn`
        return type hint. In other words, when the unreachable statement
        throws an error or terminates the program in some way.
    2.  When the unreachable statement was *intentionally* marked as unreachable
        using :ref:`version_and_platform_checks`.

    .. note::

        Mypy currently cannot detect and report unreachable or redundant code
        inside any functions using :ref:`type-variable-value-restriction`.

        This limitation will be removed in future releases of mypy.


.. _miscellaneous-strictness-flags:

Miscellaneous strictness flags
******************************

This section documents any other flags that do not neatly fall under any
of the above sections.

.. option:: --allow-untyped-globals

    This flag causes mypy to suppress errors caused by not being able to fully
    infer the types of global and class variables.

.. option:: --allow-redefinition

    By default, mypy won't allow a variable to be redefined with an
    unrelated type. This flag enables redefinition of a variable with an
    arbitrary type *in some contexts*: only redefinitions within the
    same block and nesting depth as the original definition are allowed.
    Example where this can be useful:

    .. code-block:: python

       def process(items: List[str]) -> None:
           # 'items' has type List[str]
           items = [item.split() for item in items]
           # 'items' now has type List[List[str]]
           ...

.. option:: --local-partial-types

    In mypy, the most common cases for partial types are variables initialized using ``None``,
    but without explicit ``Optional`` annotations. By default, mypy won't check partial types
    spanning module top level or class top level. This flag changes the behavior to only allow
    partial types at local level, therefore it disallows inferring variable type for ``None``
    from two assignments in different scopes. For example:

    .. code-block:: python

        from typing import Optional

        a = None  # Need type annotation here if using --local-partial-types
        b = None  # type: Optional[int]

        class Foo:
            bar = None  # Need type annotation here if using --local-partial-types
            baz = None  # type: Optional[int]

            def __init__(self) -> None:
                self.bar = 1

        reveal_type(Foo().bar)  # Union[int, None] without --local-partial-types

    Note: this option is always implicitly enabled in mypy daemon and will become
    enabled by default for mypy in a future release.

.. option:: --no-implicit-reexport

    By default, imported values to a module are treated as exported and mypy allows
    other modules to import them. This flag changes the behavior to not re-export unless
    the item is imported using from-as or is included in ``__all__``. Note this is
    always treated as enabled for stub files. For example:

    .. code-block:: python

       # This won't re-export the value
       from foo import bar
       # This will re-export it as bar and allow other modules to import it
       from foo import bar as bar
       # This will also re-export bar
       from foo import bar
       __all__ = ['bar']


.. option:: --strict-equality

    By default, mypy allows always-false comparisons like ``42 == 'no'``.
    Use this flag to prohibit such comparisons of non-overlapping types, and
    similar identity and container checks:

    .. code-block:: python

       from typing import List, Text

       items: List[int]
       if 'some string' in items:  # Error: non-overlapping container check!
           ...

       text: Text
       if text != b'other bytes':  # Error: non-overlapping equality check!
           ...

       assert text is not None  # OK, check against None is allowed as a special case.

.. option:: --strict

    This flag mode enables all optional error checking flags.  You can see the
    list of flags enabled by strict mode in the full :option:`mypy --help` output.

    Note: the exact list of flags enabled by running :option:`--strict` may change
    over time.

.. option:: --disable-error-code

    This flag allows disabling one or multiple error codes globally.

    .. code-block:: python

        # no flag
        x = 'a string'
        x.trim()  # error: "str" has no attribute "trim"  [attr-defined]

        # --disable-error-code attr-defined
        x = 'a string'
        x.trim()

.. option:: --enable-error-code

    This flag allows enabling one or multiple error codes globally.

    Note: This flag will override disabled error codes from the --disable-error-code
    flag

    .. code-block:: python

        # --disable-error-code attr-defined
        x = 'a string'
        x.trim()

        # --disable-error-code attr-defined --enable-error-code attr-defined
        x = 'a string'
        x.trim()  # error: "str" has no attribute "trim"  [attr-defined]

.. _configuring-error-messages:

Configuring error messages
**************************

The following flags let you adjust how much detail mypy displays
in error messages.

.. option:: --show-error-context

    This flag will precede all errors with "note" messages explaining the
    context of the error. For example, consider the following program:

    .. code-block:: python

        class Test:
            def foo(self, x: int) -> int:
                return x + "bar"

    Mypy normally displays an error message that looks like this::

        main.py:3: error: Unsupported operand types for + ("int" and "str")

    If we enable this flag, the error message now looks like this::

        main.py: note: In member "foo" of class "Test":
        main.py:3: error: Unsupported operand types for + ("int" and "str")

.. option:: --show-column-numbers

    This flag will add column offsets to error messages.
    For example, the following indicates an error in line 12, column 9
    (note that column offsets are 0-based)::

        main.py:12:9: error: Unsupported operand types for / ("int" and "str")

.. option:: --show-error-codes

    This flag will add an error code ``[<code>]`` to error messages. The error
    code is shown after each error message::

        prog.py:1: error: "str" has no attribute "trim"  [attr-defined]

    See :ref:`error-codes` for more information.

.. option:: --pretty

    Use visually nicer output in error messages: use soft word wrap,
    show source code snippets, and show error location markers.

.. option:: --no-color-output

    This flag will disable color output in error messages, enabled by default.

.. option:: --no-error-summary

    This flag will disable error summary. By default mypy shows a summary line
    including total number of errors, number of files with errors, and number
    of files checked.

.. option:: --show-absolute-path

    Show absolute paths to files.


.. _incremental:

Incremental mode
****************

By default, mypy will store type information into a cache. Mypy
will use this information to avoid unnecessary recomputation when
it type checks your code again.  This can help speed up the type
checking process, especially when most parts of your program have
not changed since the previous mypy run.

If you want to speed up how long it takes to recheck your code
beyond what incremental mode can offer, try running mypy in
:ref:`daemon mode <mypy_daemon>`.

.. option:: --no-incremental

    This flag disables incremental mode: mypy will no longer reference
    the cache when re-run.

    Note that mypy will still write out to the cache even when
    incremental mode is disabled: see the :option:`--cache-dir` flag below
    for more details.

.. option:: --cache-dir DIR

    By default, mypy stores all cache data inside of a folder named
    ``.mypy_cache`` in the current directory. This flag lets you
    change this folder. This flag can also be useful for controlling
    cache use when using :ref:`remote caching <remote-cache>`.

    This setting will override the ``MYPY_CACHE_DIR`` environment
    variable if it is set.

    Mypy will also always write to the cache even when incremental
    mode is disabled so it can "warm up" the cache. To disable
    writing to the cache, use ``--cache-dir=/dev/null`` (UNIX)
    or ``--cache-dir=nul`` (Windows).

.. option:: --sqlite-cache

    Use an `SQLite`_ database to store the cache.

.. option:: --cache-fine-grained

    Include fine-grained dependency information in the cache for the mypy daemon.

.. option:: --skip-version-check

    By default, mypy will ignore cache data generated by a different
    version of mypy. This flag disables that behavior.

.. option:: --skip-cache-mtime-checks

    Skip cache internal consistency checks based on mtime.


Advanced options
****************

The following flags are useful mostly for people who are interested
in developing or debugging mypy internals.

.. option:: --pdb

    This flag will invoke the Python debugger when mypy encounters
    a fatal error.

.. option:: --show-traceback, --tb

    If set, this flag will display a full traceback when mypy
    encounters a fatal error.

.. option:: --raise-exceptions

    Raise exception on fatal error.

.. option:: --custom-typing-module MODULE

    This flag lets you use a custom module as a substitute for the
    :py:mod:`typing` module.

.. option:: --custom-typeshed-dir DIR

    This flag specifies the directory where mypy looks for standard library typeshed
    stubs, instead of the typeshed that ships with mypy.  This is
    primarily intended to make it easier to test typeshed changes before
    submitting them upstream, but also allows you to use a forked version of
    typeshed.

    Note that this doesn't affect third-party library stubs.

.. _warn-incomplete-stub:

.. option:: --warn-incomplete-stub

    This flag modifies both the :option:`--disallow-untyped-defs` and
    :option:`--disallow-incomplete-defs` flags so they also report errors
    if stubs in typeshed are missing type annotations or has incomplete
    annotations. If both flags are missing, :option:`--warn-incomplete-stub`
    also does nothing.

    This flag is mainly intended to be used by people who want contribute
    to typeshed and would like a convenient way to find gaps and omissions.

    If you want mypy to report an error when your codebase *uses* an untyped
    function, whether that function is defined in typeshed or not, use the
    :option:`--disallow-untyped-calls` flag. See :ref:`untyped-definitions-and-calls`
    for more details.

.. _shadow-file:

.. option:: --shadow-file SOURCE_FILE SHADOW_FILE

    When mypy is asked to type check ``SOURCE_FILE``, this flag makes mypy
    read from and type check the contents of ``SHADOW_FILE`` instead. However,
    diagnostics will continue to refer to ``SOURCE_FILE``.

    Specifying this argument multiple times (``--shadow-file X1 Y1 --shadow-file X2 Y2``)
    will allow mypy to perform multiple substitutions.

    This allows tooling to create temporary files with helpful modifications
    without having to change the source file in place. For example, suppose we
    have a pipeline that adds ``reveal_type`` for certain variables.
    This pipeline is run on ``original.py`` to produce ``temp.py``.
    Running ``mypy --shadow-file original.py temp.py original.py`` will then
    cause mypy to type check the contents of ``temp.py`` instead of  ``original.py``,
    but error messages will still reference ``original.py``.


Report generation
*****************

If these flags are set, mypy will generate a report in the specified
format into the specified directory.

.. option:: --any-exprs-report DIR

    Causes mypy to generate a text file report documenting how many
    expressions of type ``Any`` are present within your codebase.

.. option:: --cobertura-xml-report DIR

    Causes mypy to generate a Cobertura XML type checking coverage report.

    You must install the `lxml`_ library to generate this report.

.. option:: --html-report / --xslt-html-report DIR

    Causes mypy to generate an HTML type checking coverage report.

    You must install the `lxml`_ library to generate this report.

.. option:: --linecount-report DIR

    Causes mypy to generate a text file report documenting the functions
    and lines that are typed and untyped within your codebase.

.. option:: --linecoverage-report DIR

    Causes mypy to generate a JSON file that maps each source file's
    absolute filename to a list of line numbers that belong to typed
    functions in that file.

.. option:: --lineprecision-report DIR

    Causes mypy to generate a flat text file report with per-module
    statistics of how many lines are typechecked etc.

.. option:: --txt-report / --xslt-txt-report DIR

    Causes mypy to generate a text file type checking coverage report.

    You must install the `lxml`_ library to generate this report.

.. option:: --xml-report DIR

    Causes mypy to generate an XML type checking coverage report.

    You must install the `lxml`_ library to generate this report.

Miscellaneous
*************

.. option:: --install-types

    This flag causes mypy to install known missing stub packages for
    third-party libraries using pip.  It will display the pip command
    line to run, and expects a confirmation before installing
    anything.

    If you use this option without providing any files or modules to
    type check, mypy will install stub packages suggested during the
    previous mypy run. If there are files or modules to type check,
    mypy first type checks those, and proposes to install missing
    stubs at the end of the run, but only if any missing modules were
    detected.

    .. note::

        This is new in mypy 0.900. Previous mypy versions included a
        selection of third-party package stubs, instead of having them
        installed separately.

.. option:: --junit-xml JUNIT_XML

    Causes mypy to generate a JUnit XML test result document with
    type checking results. This can make it easier to integrate mypy
    with continuous integration (CI) tools.

.. option:: --find-occurrences CLASS.MEMBER

    This flag will make mypy print out all usages of a class member
    based on static type information. This feature is experimental.

.. option:: --scripts-are-modules

    This flag will give command line arguments that appear to be
    scripts (i.e. files whose name does not end in ``.py``)
    a module name derived from the script name rather than the fixed
    name :py:mod:`__main__`.

    This lets you check more than one script in a single mypy invocation.
    (The default :py:mod:`__main__` is technically more correct, but if you
    have many scripts that import a large package, the behavior enabled
    by this flag is often more convenient.)

.. _lxml: https://pypi.org/project/lxml/
.. _SQLite: https://www.sqlite.org/
