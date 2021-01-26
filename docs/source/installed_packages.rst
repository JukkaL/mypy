.. _installed-packages:

Using installed packages
========================

:pep:`561` specifies how to mark a package as supporting type checking.
Below is a summary of how to create PEP 561 compatible packages and have
mypy use them in type checking.

Using PEP 561 compatible packages with mypy
*******************************************

Generally, you do not need to do anything to use installed packages that
support typing for the Python executable used to run mypy. Note that most
packages do not support typing. Packages that do support typing should be
automatically picked up by mypy and used for type checking.

By default, mypy searches for packages installed for the Python executable
running mypy. It is highly unlikely you want this situation if you have
installed typed packages in another Python's package directory.

Generally, you can use the :option:`--python-version <mypy --python-version>` flag and mypy will try to find
the correct package directory. If that fails, you can use the
:option:`--python-executable <mypy --python-executable>` flag to point to the exact executable, and mypy will
find packages installed for that Python executable.

Note that mypy does not support some more advanced import features, such as zip
imports and custom import hooks.

If you do not want to use typed packages, use the :option:`--no-site-packages <mypy --no-site-packages>` flag
to disable searching.

Note that stub-only packages (defined in :pep:`PEP 561: Stub-only Packages
<561#stub-only-packages>`) cannot be used with ``MYPYPATH``. If you want mypy
to find the package, it must be installed. For a package ``foo``, the name of
the stub-only package (``foo-stubs``) is not a legal package name, so mypy
will not find it, unless it is installed.

Making PEP 561 compatible packages
**********************************

:pep:`561` notes three main ways to distribute type information. The first is a
package that has only inline type annotations in the code itself. The second is
a package that ships :ref:`stub files <stub-files>` with type information
alongside the runtime code. The third method, also known as a "stub only
package" is a package that ships type information for a package separately as
stub files.

If you would like to publish a library package to a package repository (e.g.
PyPI) for either internal or external use in type checking, packages that
supply type information via type comments or annotations in the code should put
a ``py.typed`` file in their package directory. For example, with a directory
structure as follows

.. code-block:: text

    setup.py
    package_a/
        __init__.py
        lib.py
        py.typed

the ``setup.py`` might look like

.. code-block:: python

    from distutils.core import setup

    setup(
        name="SuperPackageA",
        author="Me",
        version="0.1",
        package_data={"package_a": ["py.typed"]},
        packages=["package_a"]
    )

.. note::

   If you use :doc:`setuptools <setuptools:index>`, you must pass the option ``zip_safe=False`` to
   ``setup()``, or mypy will not be able to find the installed package.

Some packages have a mix of stub files and runtime files. These packages also
require a ``py.typed`` file. An example can be seen below

.. code-block:: text

    setup.py
    package_b/
        __init__.py
        lib.py
        lib.pyi
        py.typed

the ``setup.py`` might look like:

.. code-block:: python

    from distutils.core import setup

    setup(
        name="SuperPackageB",
        author="Me",
        version="0.1",
        package_data={"package_b": ["py.typed", "lib.pyi"]},
        packages=["package_b"]
    )

In this example, both ``lib.py`` and the ``lib.pyi`` stub file exist. At
runtime, the Python interpreter will use ``lib.py``, but mypy will use
``lib.pyi`` instead.

If the package is stub-only (not imported at runtime), the package should have
a prefix of the runtime package name and a suffix of ``-stubs``.
A ``py.typed`` file is not needed for stub-only packages. For example, if we
had stubs for ``package_c``, we might do the following:

.. code-block:: text

    setup.py
    package_c-stubs/
        __init__.pyi
        lib.pyi

the ``setup.py`` might look like:

.. code-block:: python

    from distutils.core import setup

    setup(
        name="SuperPackageC",
        author="Me",
        version="0.1",
        package_data={"package_c-stubs": ["__init__.pyi", "lib.pyi"]},
        packages=["package_c-stubs"]
    )

While instructions above assure that the builded wheel contains the type files,
you may also need to modify your ``MANIFEST.in`` file to ensure their inclusion
inside ``sdist`` (``.tar.gz``) archive:

.. code-block:: text

    global-include *.pyi
    global-include *.typed
