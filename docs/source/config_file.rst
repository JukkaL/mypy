.. _config-file:

The mypy configuration file
===========================

Mypy is very configurable. This is most useful when introducing typing to
an existing codebase. See :ref:`existing-code` for concrete advice for
that situation.

Mypy supports reading configuration settings from a file with the following precedence order:

    1. ``./mypy.ini``
    2. ``./.mypy.ini``
    3. ``./pyproject.toml``
    4. ``./setup.cfg``
    5. ``$XDG_CONFIG_HOME/mypy/config``
    6. ``~/.config/mypy/config``
    7. ``~/.mypy.ini``

It is important to understand that there is no merging of configuration
files, as it would lead to ambiguity. The :option:`--config-file <mypy --config-file>`
command-line flag has the highest precedence and
must be correct; otherwise mypy will report an error and exit. Without the
command line option, mypy will look for configuration files in the
precedence order above.

Most flags correspond closely to :ref:`command-line flags
<command-line>` but there are some differences in flag names and some
flags may take a different value based on the module being processed.

Some flags support user home directory and environment variable expansion.
To refer to the user home directory, use ``~`` at the beginning of the path.
To expand environment variables use ``$VARNAME`` or ``${VARNAME}``.


Config file format
******************

The configuration file format is the usual
:doc:`ini file <python:library/configparser>` format. It should contain
section names in square brackets and flag settings of the form
`NAME = VALUE`. Comments start with ``#`` characters.

- A section named ``[mypy]`` must be present.  This specifies
  the global flags.

- Additional sections named ``[mypy-PATTERN1,PATTERN2,...]`` may be
  present, where ``PATTERN1``, ``PATTERN2``, etc., are comma-separated
  patterns of fully-qualified module names, with some components optionally
  replaced by the '*' character (e.g. ``foo.bar``, ``foo.bar.*``, ``foo.*.baz``).
  These sections specify additional flags that only apply to *modules*
  whose name matches at least one of the patterns.

  A pattern of the form ``qualified_module_name`` matches only the named module,
  while ``dotted_module_name.*`` matches ``dotted_module_name`` and any
  submodules (so ``foo.bar.*`` would match all of ``foo.bar``,
  ``foo.bar.baz``, and ``foo.bar.baz.quux``).

  Patterns may also be "unstructured" wildcards, in which stars may
  appear in the middle of a name (e.g
  ``site.*.migrations.*``). Stars match zero or more module
  components (so ``site.*.migrations.*`` can match ``site.migrations``).

  .. _config-precedence:

  When options conflict, the precedence order for configuration is:

    1. :ref:`Inline configuration <inline-config>` in the source file
    2. Sections with concrete module names (``foo.bar``)
    3. Sections with "unstructured" wildcard patterns (``foo.*.baz``),
       with sections later in the configuration file overriding
       sections earlier.
    4. Sections with "well-structured" wildcard patterns
       (``foo.bar.*``), with more specific overriding more general.
    5. Command line options.
    6. Top-level configuration file options.

The difference in precedence order between "structured" patterns (by
specificity) and "unstructured" patterns (by order in the file) is
unfortunate, and is subject to change in future versions.

.. note::

   The :confval:`warn_unused_configs` flag may be useful to debug misspelled
   section names.

.. note::

   Configuration flags are liable to change between releases.


Per-module and global options
*****************************

Some of the config options may be set either globally (in the ``[mypy]`` section)
or on a per-module basis (in sections like ``[mypy-foo.bar]``).

If you set an option both globally and for a specific module, the module configuration
options take precedence. This lets you set global defaults and override them on a
module-by-module basis. If multiple pattern sections match a module, :ref:`the options from the
most specific section are used where they disagree <config-precedence>`.

Some other options, as specified in their description,
may only be set in the global section (``[mypy]``).


Inverting option values
***********************

Options that take a boolean value may be inverted by adding ``no_`` to
their name or by (when applicable) swapping their prefix from
``disallow`` to ``allow`` (and vice versa).


Example ``mypy.ini``
********************

Here is an example of a ``mypy.ini`` file. To use this config file, place it at the root
of your repo and run mypy.

.. code-block:: ini

    # Global options:

    [mypy]
    warn_return_any = True
    warn_unused_configs = True

    # Per-module options:

    [mypy-mycode.foo.*]
    disallow_untyped_defs = True

    [mypy-mycode.bar]
    warn_return_any = False

    [mypy-somelibrary]
    ignore_missing_imports = True

This config file specifies two global options in the ``[mypy]`` section. These two
options will:

1.  Report an error whenever a function returns a value that is inferred
    to have type ``Any``.

2.  Report any config options that are unused by mypy. (This will help us catch typos
    when making changes to our config file).

Next, this module specifies three per-module options. The first two options change how mypy
type checks code in ``mycode.foo.*`` and ``mycode.bar``, which we assume here are two modules
that you wrote. The final config option changes how mypy type checks ``somelibrary``, which we
assume here is some 3rd party library you've installed and are importing. These options will:

1.  Selectively disallow untyped function definitions only within the ``mycode.foo``
    package -- that is, only for function definitions defined in the
    ``mycode/foo`` directory.

2.  Selectively *disable* the "function is returning any" warnings within
    ``mycode.bar`` only. This overrides the global default we set earlier.

3.  Suppress any error messages generated when your codebase tries importing the
    module ``somelibrary``. This is useful if ``somelibrary`` is some 3rd party library
    missing type hints.


.. _config-file-import-discovery:

Import discovery
****************

For more information, see the :ref:`Import discovery <import-discovery>`
section of the command line docs.

.. confval:: mypy_path

    :type: string

    Specifies the paths to use, after trying the paths from ``MYPYPATH`` environment
    variable.  Useful if you'd like to keep stubs in your repo, along with the config file.
    Multiple paths are always separated with a ``:`` or ``,`` regardless of the platform.
    User home directory and environment variables will be expanded.

    Relative paths are treated relative to the working directory of the mypy command,
    not the config file.
    Use the ``MYPY_CONFIG_FILE_DIR`` environment variable to refer to paths relative to
    the config file (e.g. ``mypy_path = $MYPY_CONFIG_FILE_DIR/src``).

    This option may only be set in the global section (``[mypy]``).

    **Note:** On Windows, use UNC paths to avoid using ``:`` (e.g. ``\\127.0.0.1\X$\MyDir`` where ``X`` is the drive letter).

.. confval:: files

    :type: comma-separated list of strings

    A comma-separated list of paths which should be checked by mypy if none are given on the command
    line. Supports recursive file globbing using :py:mod:`glob`, where ``*`` (e.g. ``*.py``) matches
    files in the current directory and ``**/`` (e.g. ``**/*.py``) matches files in any directories below
    the current one. User home directory and environment variables will be expanded.

    This option may only be set in the global section (``[mypy]``).

.. confval:: modules

    :type: comma-separated list of strings

    A comma-separated list of packages which should be checked by mypy if none are given on the command
    line. Mypy *will not* recursively type check any submodules of the provided
    module.

    This option may only be set in the global section (``[mypy]``).


.. confval:: packages

    :type: comma-separated list of strings

    A comma-separated list of packages which should be checked by mypy if none are given on the command
    line.  Mypy *will* recursively type check any submodules of the provided
    package. This flag is identical to :confval:`modules` apart from this
    behavior.

    This option may only be set in the global section (``[mypy]``).

.. confval:: exclude

    :type: regular expression

    A regular expression that matches file names, directory names and paths
    which mypy should ignore while recursively discovering files to check.
    Use forward slashes (``/``) as directory separators on all platforms.

    .. code-block:: ini

      [mypy]
      exclude = (?x)(
          ^one\.py$    # files named "one.py"
          | two\.pyi$  # or files ending with "two.pyi"
          | ^three\.   # or files starting with "three."
        )

    Crafting a single regular expression that excludes multiple files while remaining
    human-readable can be a challenge. The above example demonstrates one approach.
    ``(?x)`` enables the ``VERBOSE`` flag for the subsequent regular expression, which
    :py:data:`ignores most whitespace and supports comments <re.VERBOSE>`.
    The above is equivalent to: ``(^one\.py$|two\.pyi$|^three\.)``.

    For more details, see :option:`--exclude <mypy --exclude>`.

    This option may only be set in the global section (``[mypy]``).

    .. note::

       Note that the TOML equivalent differs slightly. It can be either a single string
       (including a multi-line string) -- which is treated as a single regular
       expression -- or an array of such strings. The following TOML examples are
       equivalent to the above INI example.

       Array of strings:

       .. code-block:: toml

          [tool.mypy]
          exclude = [
              "^one\\.py$",  # TOML's double-quoted strings require escaping backslashes
              'two\.pyi$',  # but TOML's single-quoted strings do not
              '^three\.',
          ]

       A single, multi-line string:

       .. code-block:: toml

          [tool.mypy]
          exclude = '''(?x)(
              ^one\.py$    # files named "one.py"
              | two\.pyi$  # or files ending with "two.pyi"
              | ^three\.   # or files starting with "three."
          )'''  # TOML's single-quoted strings do not require escaping backslashes

       See :ref:`using-a-pyproject-toml`.

.. confval:: namespace_packages

    :type: boolean
    :default: True

    Enables :pep:`420` style namespace packages.  See the
    corresponding flag :option:`--no-namespace-packages <mypy --no-namespace-packages>`
    for more information.

    This option may only be set in the global section (``[mypy]``).

.. confval:: explicit_package_bases

    :type: boolean
    :default: False

    This flag tells mypy that top-level packages will be based in either the
    current directory, or a member of the ``MYPYPATH`` environment variable or
    :confval:`mypy_path` config option. This option is only useful in
    the absence of `__init__.py`. See :ref:`Mapping file
    paths to modules <mapping-paths-to-modules>` for details.

    This option may only be set in the global section (``[mypy]``).

.. confval:: ignore_missing_imports

    :type: boolean
    :default: False

    Suppresses error messages about imports that cannot be resolved.

    If this option is used in a per-module section, the module name should
    match the name of the *imported* module, not the module containing the
    import statement.

.. confval:: follow_imports

    :type: string
    :default: ``normal``

    Directs what to do with imports when the imported module is found
    as a ``.py`` file and not part of the files, modules and packages
    provided on the command line.

    The four possible values are ``normal``, ``silent``, ``skip`` and
    ``error``.  For explanations see the discussion for the
    :option:`--follow-imports <mypy --follow-imports>` command line flag.

    Using this option in a per-module section (potentially with a wildcard,
    as described at the top of this page) is a good way to prevent mypy from
    checking portions of your code.

    If this option is used in a per-module section, the module name should
    match the name of the *imported* module, not the module containing the
    import statement.

.. confval:: follow_imports_for_stubs

    :type: boolean
    :default: False

    Determines whether to respect the :confval:`follow_imports` setting even for
    stub (``.pyi``) files.

    Used in conjunction with :confval:`follow_imports=skip <follow_imports>`, this can be used
    to suppress the import of a module from ``typeshed``, replacing it
    with ``Any``.

    Used in conjunction with :confval:`follow_imports=error <follow_imports>`, this can be used
    to make any use of a particular ``typeshed`` module an error.

    .. note::

         This is not supported by the mypy daemon.

.. confval:: python_executable

    :type: string

    Specifies the path to the Python executable to inspect to collect
    a list of available :ref:`PEP 561 packages <installed-packages>`. User
    home directory and environment variables will be expanded. Defaults to
    the executable used to run mypy.

    This option may only be set in the global section (``[mypy]``).

.. confval:: no_site_packages

    :type: boolean
    :default: False

    Disables using type information in installed packages (see :pep:`561`).
    This will also disable searching for a usable Python executable. This acts
    the same as :option:`--no-site-packages <mypy --no-site-packages>` command
    line flag.

.. confval:: no_silence_site_packages

    :type: boolean
    :default: False

    Enables reporting error messages generated within installed packages (see
    :pep:`561` for more details on distributing type information). Those error
    messages are suppressed by default, since you are usually not able to
    control errors in 3rd party code.

    This option may only be set in the global section (``[mypy]``).


Platform configuration
**********************

.. confval:: python_version

    :type: string

    Specifies the Python version used to parse and check the target
    program.  The string should be in the format ``MAJOR.MINOR`` --
    for example ``2.7``.  The default is the version of the Python
    interpreter used to run mypy.

    This option may only be set in the global section (``[mypy]``).

.. confval:: platform

    :type: string

    Specifies the OS platform for the target program, for example
    ``darwin`` or ``win32`` (meaning OS X or Windows, respectively).
    The default is the current platform as revealed by Python's
    :py:data:`sys.platform` variable.

    This option may only be set in the global section (``[mypy]``).

.. confval:: always_true

    :type: comma-separated list of strings

    Specifies a list of variables that mypy will treat as
    compile-time constants that are always true.

.. confval:: always_false

    :type: comma-separated list of strings

    Specifies a list of variables that mypy will treat as
    compile-time constants that are always false.


Disallow dynamic typing
***********************

For more information, see the :ref:`Disallow dynamic typing <disallow-dynamic-typing>`
section of the command line docs.

.. confval:: disallow_any_unimported

    :type: boolean
    :default: False

    Disallows usage of types that come from unfollowed imports (anything imported from
    an unfollowed import is automatically given a type of ``Any``).

.. confval:: disallow_any_expr

    :type: boolean
    :default: False

    Disallows all expressions in the module that have type ``Any``.

.. confval:: disallow_any_decorated

    :type: boolean
    :default: False

    Disallows functions that have ``Any`` in their signature after decorator transformation.

.. confval:: disallow_any_explicit

    :type: boolean
    :default: False

    Disallows explicit ``Any`` in type positions such as type annotations and generic
    type parameters.

.. confval:: disallow_any_generics

    :type: boolean
    :default: False

    Disallows usage of generic types that do not specify explicit type parameters.

.. confval:: disallow_subclassing_any

    :type: boolean
    :default: False

    Disallows subclassing a value of type ``Any``.


Untyped definitions and calls
*****************************

For more information, see the :ref:`Untyped definitions and calls <untyped-definitions-and-calls>`
section of the command line docs.

.. confval:: disallow_untyped_calls

    :type: boolean
    :default: False

    Disallows calling functions without type annotations from functions with type
    annotations. Note that when used in per-module options, it enables/disables
    this check **inside** the module(s) specified, not for functions that come
    from that module(s), for example config like this:

    .. code-block:: ini

        [mypy]
        disallow_untyped_calls = True

        [mypy-some.library.*]
        disallow_untyped_calls = False

    will disable this check inside ``some.library``, not for your code that
    imports ``some.library``. If you want to selectively disable this check for
    all your code that imports ``some.library`` you should instead use
    :confval:`untyped_calls_exclude`, for example:

    .. code-block:: ini

        [mypy]
        disallow_untyped_calls = True
        untyped_calls_exclude = some.library

.. confval:: untyped_calls_exclude

    :type: comma-separated list of strings

    Selectively excludes functions and methods defined in specific packages,
    modules, and classes from action of :confval:`disallow_untyped_calls`.
    This also applies to all submodules of packages (i.e. everything inside
    a given prefix). Note, this option does not support per-file configuration,
    the exclusions list is defined globally for all your code.

.. confval:: disallow_untyped_defs

    :type: boolean
    :default: False

    Disallows defining functions without type annotations or with incomplete type
    annotations (a superset of :confval:`disallow_incomplete_defs`).

    For example, it would report an error for :code:`def f(a, b)` and :code:`def f(a: int, b)`.

.. confval:: disallow_incomplete_defs

    :type: boolean
    :default: False

    Disallows defining functions with incomplete type annotations, while still
    allowing entirely unannotated definitions.

    For example, it would report an error for :code:`def f(a: int, b)` but not :code:`def f(a, b)`.

.. confval:: check_untyped_defs

    :type: boolean
    :default: False

    Type-checks the interior of functions without type annotations.

.. confval:: disallow_untyped_decorators

    :type: boolean
    :default: False

    Reports an error whenever a function with type annotations is decorated with a
    decorator without annotations.


.. _config-file-none-and-optional-handling:

None and Optional handling
**************************

For more information, see the :ref:`None and Optional handling <none-and-optional-handling>`
section of the command line docs.

.. confval:: implicit_optional

    :type: boolean
    :default: False

    Causes mypy to treat parameters with a ``None``
    default value as having an implicit optional type (``T | None``).

    **Note:** This was True by default in mypy versions 0.980 and earlier.

.. confval:: strict_optional

    :type: boolean
    :default: True

    Effectively disables checking of optional
    types and ``None`` values. With this option, mypy doesn't
    generally check the use of ``None`` values -- it is treated
    as compatible with every type.

    .. warning::

        ``strict_optional = false`` is evil. Avoid using it and definitely do
        not use it without understanding what it does.


Configuring warnings
********************

For more information, see the :ref:`Configuring warnings <configuring-warnings>`
section of the command line docs.

.. confval:: warn_redundant_casts

    :type: boolean
    :default: False

    Warns about casting an expression to its inferred type.

    This option may only be set in the global section (``[mypy]``).

.. confval:: warn_unused_ignores

    :type: boolean
    :default: False

    Warns about unneeded ``# type: ignore`` comments.

.. confval:: warn_no_return

    :type: boolean
    :default: True

    Shows errors for missing return statements on some execution paths.

.. confval:: warn_return_any

    :type: boolean
    :default: False

    Shows a warning when returning a value with type ``Any`` from a function
    declared with a non- ``Any`` return type.

.. confval:: warn_unreachable

    :type: boolean
    :default: False

    Shows a warning when encountering any code inferred to be unreachable or
    redundant after performing type analysis.


Suppressing errors
******************

Note: these configuration options are available in the config file only. There is
no analog available via the command line options.

.. confval:: ignore_errors

    :type: boolean
    :default: False

    Ignores all non-fatal errors.


Miscellaneous strictness flags
******************************

For more information, see the :ref:`Miscellaneous strictness flags <miscellaneous-strictness-flags>`
section of the command line docs.

.. confval:: allow_untyped_globals

    :type: boolean
    :default: False

    Causes mypy to suppress errors caused by not being able to fully
    infer the types of global and class variables.

.. confval:: allow_redefinition

    :type: boolean
    :default: False

    Allows variables to be redefined with an arbitrary type, as long as the redefinition
    is in the same block and nesting level as the original definition.
    Example where this can be useful:

    .. code-block:: python

       def process(items: list[str]) -> None:
           # 'items' has type list[str]
           items = [item.split() for item in items]
           # 'items' now has type list[list[str]]

    The variable must be used before it can be redefined:

    .. code-block:: python

        def process(items: list[str]) -> None:
           items = "mypy"  # invalid redefinition to str because the variable hasn't been used yet
           print(items)
           items = "100"  # valid, items now has type str
           items = int(items)  # valid, items now has type int

.. confval:: local_partial_types

    :type: boolean
    :default: False

    Disallows inferring variable type for ``None`` from two assignments in different scopes.
    This is always implicitly enabled when using the :ref:`mypy daemon <mypy_daemon>`.

.. confval:: disable_error_code

    :type: comma-separated list of strings

    Allows disabling one or multiple error codes globally.

.. confval:: enable_error_code

    :type: comma-separated list of strings

    Allows enabling one or multiple error codes globally.

    Note: This option will override disabled error codes from the disable_error_code option.

.. confval:: extra_checks

   :type: boolean
   :default: False

   This flag enables additional checks that are technically correct but may be impractical in real code.
   See :option:`mypy --extra-checks` for more info.

.. confval:: implicit_reexport

    :type: boolean
    :default: True

    By default, imported values to a module are treated as exported and mypy allows
    other modules to import them. When false, mypy will not re-export unless
    the item is imported using from-as or is included in ``__all__``. Note that mypy
    treats stub files as if this is always disabled. For example:

    .. code-block:: python

       # This won't re-export the value
       from foo import bar
       # This will re-export it as bar and allow other modules to import it
       from foo import bar as bar
       # This will also re-export bar
       from foo import bar
       __all__ = ['bar']

.. confval:: strict_concatenate

   :type: boolean
   :default: False

   Make arguments prepended via ``Concatenate`` be truly positional-only.

.. confval:: strict_equality

   :type: boolean
   :default: False

   Prohibit equality checks, identity checks, and container checks between
   non-overlapping types.

.. confval:: strict

   :type: boolean
   :default: False

   Enable all optional error checking flags.  You can see the list of
   flags enabled by strict mode in the full :option:`mypy --help`
   output.

   Note: the exact list of flags enabled by :confval:`strict` may
   change over time.


Configuring error messages
**************************

For more information, see the :ref:`Configuring error messages <configuring-error-messages>`
section of the command line docs.

These options may only be set in the global section (``[mypy]``).

.. confval:: show_error_context

    :type: boolean
    :default: False

    Prefixes each error with the relevant context.

.. confval:: show_column_numbers

    :type: boolean
    :default: False

    Shows column numbers in error messages.

.. confval:: show_error_code_links

    :type: boolean
    :default: False

    Shows documentation link to corresponding error code.

.. confval:: hide_error_codes

    :type: boolean
    :default: False

    Hides error codes in error messages. See :ref:`error-codes` for more information.

.. confval:: pretty

    :type: boolean
    :default: False

    Use visually nicer output in error messages: use soft word wrap,
    show source code snippets, and show error location markers.

.. confval:: color_output

    :type: boolean
    :default: True

    Shows error messages with color enabled.

.. confval:: error_summary

    :type: boolean
    :default: True

    Shows a short summary line after error messages.

.. confval:: show_absolute_path

    :type: boolean
    :default: False

    Show absolute paths to files.

.. confval:: force_uppercase_builtins

    :type: boolean
    :default: False

    Always use ``List`` instead of ``list`` in error messages,
    even on Python 3.9+.

.. confval:: force_union_syntax

    :type: boolean
    :default: False

    Always use ``Union[]`` and ``Optional[]`` for union types
    in error messages (instead of the ``|`` operator),
    even on Python 3.10+.

Incremental mode
****************

These options may only be set in the global section (``[mypy]``).

.. confval:: incremental

    :type: boolean
    :default: True

    Enables :ref:`incremental mode <incremental>`.

.. confval:: cache_dir

    :type: string
    :default: ``.mypy_cache``

    Specifies the location where mypy stores incremental cache info.
    User home directory and environment variables will be expanded.
    This setting will be overridden by the ``MYPY_CACHE_DIR`` environment
    variable.

    Note that the cache is only read when incremental mode is enabled
    but is always written to, unless the value is set to ``/dev/null``
    (UNIX) or ``nul`` (Windows).

.. confval:: sqlite_cache

    :type: boolean
    :default: False

    Use an `SQLite`_ database to store the cache.

.. confval:: cache_fine_grained

    :type: boolean
    :default: False

    Include fine-grained dependency information in the cache for the mypy daemon.

.. confval:: skip_version_check

    :type: boolean
    :default: False

    Makes mypy use incremental cache data even if it was generated by a
    different version of mypy. (By default, mypy will perform a version
    check and regenerate the cache if it was written by older versions of mypy.)

.. confval:: skip_cache_mtime_checks

    :type: boolean
    :default: False

    Skip cache internal consistency checks based on mtime.


Advanced options
****************

These options may only be set in the global section (``[mypy]``).

.. confval:: plugins

    :type: comma-separated list of strings

    A comma-separated list of mypy plugins. See :ref:`extending-mypy-using-plugins`.

.. confval:: pdb

    :type: boolean
    :default: False

    Invokes :mod:`pdb` on fatal error.

.. confval:: show_traceback

    :type: boolean
    :default: False

    Shows traceback on fatal error.

.. confval:: raise_exceptions

    :type: boolean
    :default: False

    Raise exception on fatal error.

.. confval:: custom_typing_module

    :type: string

    Specifies a custom module to use as a substitute for the :py:mod:`typing` module.

.. confval:: custom_typeshed_dir

    :type: string

    This specifies the directory where mypy looks for standard library typeshed
    stubs, instead of the typeshed that ships with mypy.  This is
    primarily intended to make it easier to test typeshed changes before
    submitting them upstream, but also allows you to use a forked version of
    typeshed.

    User home directory and environment variables will be expanded.

    Note that this doesn't affect third-party library stubs. To test third-party stubs,
    for example try ``MYPYPATH=stubs/six mypy ...``.

.. confval:: warn_incomplete_stub

    :type: boolean
    :default: False

    Warns about missing type annotations in typeshed.  This is only relevant
    in combination with :confval:`disallow_untyped_defs` or :confval:`disallow_incomplete_defs`.


Report generation
*****************

If these options are set, mypy will generate a report in the specified
format into the specified directory.

.. warning::

  Generating reports disables incremental mode and can significantly slow down
  your workflow. It is recommended to enable reporting only for specific runs
  (e.g. in CI).

.. confval:: any_exprs_report

    :type: string

    Causes mypy to generate a text file report documenting how many
    expressions of type ``Any`` are present within your codebase.

.. confval:: cobertura_xml_report

    :type: string

    Causes mypy to generate a Cobertura XML type checking coverage report.

    To generate this report, you must either manually install the `lxml`_
    library or specify mypy installation with the setuptools extra
    ``mypy[reports]``.

.. confval:: html_report / xslt_html_report

    :type: string

    Causes mypy to generate an HTML type checking coverage report.

    To generate this report, you must either manually install the `lxml`_
    library or specify mypy installation with the setuptools extra
    ``mypy[reports]``.

.. confval:: linecount_report

    :type: string

    Causes mypy to generate a text file report documenting the functions
    and lines that are typed and untyped within your codebase.

.. confval:: linecoverage_report

    :type: string

    Causes mypy to generate a JSON file that maps each source file's
    absolute filename to a list of line numbers that belong to typed
    functions in that file.

.. confval:: lineprecision_report

    :type: string

    Causes mypy to generate a flat text file report with per-module
    statistics of how many lines are typechecked etc.

.. confval:: txt_report / xslt_txt_report

    :type: string

    Causes mypy to generate a text file type checking coverage report.

    To generate this report, you must either manually install the `lxml`_
    library or specify mypy installation with the setuptools extra
    ``mypy[reports]``.

.. confval:: xml_report

    :type: string

    Causes mypy to generate an XML type checking coverage report.

    To generate this report, you must either manually install the `lxml`_
    library or specify mypy installation with the setuptools extra
    ``mypy[reports]``.


Miscellaneous
*************

These options may only be set in the global section (``[mypy]``).

.. confval:: junit_xml

    :type: string

    Causes mypy to generate a JUnit XML test result document with
    type checking results. This can make it easier to integrate mypy
    with continuous integration (CI) tools.

.. confval:: scripts_are_modules

    :type: boolean
    :default: False

    Makes script ``x`` become module ``x`` instead of ``__main__``.  This is
    useful when checking multiple scripts in a single run.

.. confval:: warn_unused_configs

    :type: boolean
    :default: False

    Warns about per-module sections in the config file that do not
    match any files processed when invoking mypy.
    (This requires turning off incremental mode using :confval:`incremental = False <incremental>`.)

.. confval:: verbosity

    :type: integer
    :default: 0

    Controls how much debug output will be generated.  Higher numbers are more verbose.


.. _using-a-pyproject-toml:

Using a pyproject.toml file
***************************

Instead of using a ``mypy.ini`` file, a ``pyproject.toml`` file (as specified by
`PEP 518`_) may be used instead. A few notes on doing so:

* The ``[mypy]`` section should have ``tool.`` prepended to its name:

  * I.e., ``[mypy]`` would become ``[tool.mypy]``

* The module specific sections should be moved into ``[[tool.mypy.overrides]]`` sections:

  * For example, ``[mypy-packagename]`` would become:

.. code-block:: toml

  [[tool.mypy.overrides]]
  module = 'packagename'
  ...

* Multi-module specific sections can be moved into a single ``[[tool.mypy.overrides]]`` section with a
  module property set to an array of modules:

  * For example, ``[mypy-packagename,packagename2]`` would become:

.. code-block:: toml

  [[tool.mypy.overrides]]
  module = [
      'packagename',
      'packagename2'
  ]
  ...

* The following care should be given to values in the ``pyproject.toml`` files as compared to ``ini`` files:

  * Strings must be wrapped in double quotes, or single quotes if the string contains special characters

  * Boolean values should be all lower case

Please see the `TOML Documentation`_ for more details and information on
what is allowed in a ``toml`` file. See `PEP 518`_ for more information on the layout
and structure of the ``pyproject.toml`` file.

Example ``pyproject.toml``
**************************

Here is an example of a ``pyproject.toml`` file. To use this config file, place it at the root
of your repo (or append it to the end of an existing ``pyproject.toml`` file) and run mypy.

.. code-block:: toml

    # mypy global options:

    [tool.mypy]
    python_version = "2.7"
    warn_return_any = true
    warn_unused_configs = true
    exclude = [
        '^file1\.py$',  # TOML literal string (single-quotes, no escaping necessary)
        "^file2\\.py$",  # TOML basic string (double-quotes, backslash and other characters need escaping)
    ]

    # mypy per-module options:

    [[tool.mypy.overrides]]
    module = "mycode.foo.*"
    disallow_untyped_defs = true

    [[tool.mypy.overrides]]
    module = "mycode.bar"
    warn_return_any = false

    [[tool.mypy.overrides]]
    module = [
        "somelibrary",
        "some_other_library"
    ]
    ignore_missing_imports = true

.. _lxml: https://pypi.org/project/lxml/
.. _SQLite: https://www.sqlite.org/
.. _PEP 518: https://www.python.org/dev/peps/pep-0518/
.. _TOML Documentation: https://toml.io/
