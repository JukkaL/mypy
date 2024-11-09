.. Mypy documentation main file, created by
   sphinx-quickstart on Sun Sep 14 19:50:35 2014.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to mypy documentation!
==============================

Mypy is a static type checker for Python.

Type checkers help ensure that you're using variables and functions in your code
correctly. With mypy, add type hints (:pep:`484`)
to your Python programs, and mypy will warn you when you use those types
incorrectly.

Python is a dynamic language, so usually you'll only see errors in your code
when you attempt to run it. Mypy is a *static* checker, so it finds bugs
in your programs without even running them!

Here is a small example to whet your appetite:

.. code-block:: python

   number = input("What is your favourite number?")
   print("It is", number + 1)  # error: Unsupported operand types for + ("str" and "int")

Adding type hints for mypy does not interfere with the way your program would
otherwise run. Think of type hints as similar to comments! You can always use
the Python interpreter to run your code, even if mypy reports errors.

Mypy is designed with gradual typing in mind. This means you can add type
hints to your code base slowly and that you can always fall back to dynamic
typing when static typing is not convenient.

Mypy has a powerful and easy-to-use type system, supporting features such as
type inference, generics, callable types, tuple types, union types,
structural subtyping and more. Using mypy will make your programs easier to
understand, debug, and maintain.

.. note::

   Although mypy is production ready, there may be occasional changes
   that break backward compatibility. The mypy development team tries to
   minimize the impact of changes to user code. In case of a major breaking
   change, mypy's major version will be bumped.

Contents
--------

.. toctree::
   :maxdepth: 2
   :caption: First steps

   getting_started
   cheat_sheet_py3
   existing_code

.. _overview-type-system-reference:

.. toctree::
   :maxdepth: 2
   :caption: Type system reference

   builtin_types
   type_inference_and_annotations
   kinds_of_types
   class_basics
   runtime_troubles
   protocols
   dynamic_typing
   type_narrowing
   duck_type_compatibility
   stubs
   generics
   more_types
   literal_types
   typed_dict
   final_attrs
   metaclasses

.. toctree::
   :maxdepth: 2
   :caption: Configuring and running mypy

   running_mypy
   command_line
   config_file
   inline_config
   mypy_daemon
   installed_packages
   extending_mypy
   stubgen
   stubtest

.. toctree::
   :maxdepth: 2
   :caption: Miscellaneous

   common_issues
   supported_python_features
   error_codes
   error_code_list
   error_code_list2
   additional_features
   faq
   changelog

.. toctree::
   :hidden:
   :caption: Project Links

   GitHub <https://github.com/python/mypy>
   Website <https://mypy-lang.org/>

Indices and tables
==================

* :ref:`genindex`
* :ref:`search`
