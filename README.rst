+-----------------------------------------------------------------------------------------------------------------------------------------------------------------+
|  IMPORTANT: This project is now hosted on Codeberg.                                                                                                             |
+=================================================================================================================================================================+
| The GitHub repository is NOT up to date. Please visit the `Codeberg repository <https://codeberg.org/jmcs/ecological>`_ for the latest version of this project. |
+-----------------------------------------------------------------------------------------------------------------------------------------------------------------+

==========
Ecological
==========

Python library for managing configuration data from environment variables using PEP 526 annotations.

Getting Started
===============
``Ecological`` lets you read and convert environment variables according to your configuration class definition.

For example, imagine that your application has a configurable integer ``port``, a boolean ``debug`` flag, and a string
``log_level`` that defaults to ``INFO``. You could declare your configuration as follows:

.. code-block:: python

    class Configuration(ecological.Config):
        port: int
        debug: bool
        log_level: str = "INFO"

And then set the environment variables ``PORT``, ``DEBUG`` and ``LOG_LEVEL``. ``Ecological`` will automatically set the
class properties from the environment variables with the same (but upper cased) name.

By default, Ecological sets the values at class definition time and assigns them to the class itself, so you do not need to
instantiate the class. If needed, you can change this behavior (see the Autoloading section).

Tutorial
--------
You can use the `tutorial <tutorial.ipynb>`_ to explore the library's basic features interactively.

Typing Support
==============
You can use ``Ecological`` with several types defined in PEP484_, for example:

.. code-block:: python


    class Configuration(ecological.Config):
        list_of_values: List[str]

Will automatically parse the environment variable value as a list.

.. note:: While this ensures that ``Configuration.list_of_values`` is a list, it does not verify that it contains only
          strings.

Prefixed Configuration
======================
You can also decide to prefix your application configuration, for example, to avoid collisions:

.. code-block:: python

    class Configuration(ecological.Config, prefix='myapp'):
        home: str


In this case, the ``home`` property will be read from the ``MYAPP_HOME`` environment variable.

Nested Configuration
=====================
``Ecological.Config`` also supports nested configurations, for example:

.. code-block:: python


    class Configuration(ecological.Config):
        integer: int

        class Nested(ecological.Config, prefix='nested'):
            boolean: bool

This way you can group related configuration properties hierarchically.

Advanced
========

Fine-grained Control
---------------------
You can control some behavior of how the configuration properties are set.

You can achieve this by providing an ``ecological.Variable`` instance as the default
value for an attribute, or by specifying global options at the class level:

.. code-block:: python

    my_source = {"KEY1": "VALUE1"}

    class Configuration(ecological.Config, transform=lambda v, wt: v, wanted_type=int, ...):
        my_var1: WantedType = ecological.Variable(transform=lambda v, wt: wt(v), source=my_source, ...)
        my_var2: str
        # ...

All available options and their meanings are described in the table below:

+-------------------+---------------+-----------------+-------------------------------------------------+-------------------------------------------------------------------+
| Option            | Class level   | Variable level  | Default                                         | Description                                                       |
+===================+===============+=================+=================================================+===================================================================+
| ``prefix``        | yes           | no              | ``None``                                        | A prefix that is uppercased and prepended when a variable name    |
|                   |               |                 |                                                 | is derived from an attribute name.                                |
+-------------------+---------------+-----------------+-------------------------------------------------+-------------------------------------------------------------------+
| ``variable_name`` | yes           | yes             | Derived from attribute name and prefixed        | When specified on the variable level it states                    |
|                   |               |                 | with ``prefix`` if specified; uppercased.       | the exact name of the source variable that will be used.          |
|                   |               |                 |                                                 |                                                                   |
|                   |               |                 |                                                 | When specified on the class level it is treated as a function     |
|                   |               |                 |                                                 | that returns a variable name from the attribute name with         |
|                   |               |                 |                                                 | the following signature:                                          |
|                   |               |                 |                                                 |                                                                   |
|                   |               |                 |                                                 | ``def func(attribute_name: str, prefix: Optional[str] = None)``   |
+-------------------+---------------+-----------------+-------------------------------------------------+-------------------------------------------------------------------+
| ``default``       | no            | yes             | (no default)                                    | Default value for the property if it isn't set.                   |
+-------------------+---------------+-----------------+-------------------------------------------------+-------------------------------------------------------------------+
| ``transform``     | yes           | yes             | A source value is casted to the ``wanted_type`` | A function that converts a value from the ``source`` to the value |
|                   |               |                 | In case of non-scalar types (+ scalar ``bool``) | and ``wanted_type`` you expect with the following signature:      |
|                   |               |                 | the value is Python-parsed first.               |                                                                   |
|                   |               |                 |                                                 | ``def func(source_value: str, wanted_type: Union[Type, str])``    |
+-------------------+---------------+-----------------+-------------------------------------------------+-------------------------------------------------------------------+
| ``source``        | yes           | yes             | ``os.environ``                                  | Dictionary that the value will be loaded from.                    |
+-------------------+---------------+-----------------+-------------------------------------------------+-------------------------------------------------------------------+
| ``wanted_type``   | yes           | yes             | ``str``                                         | Desired Python type of the attribute's value.                     |
|                   |               |                 |                                                 |                                                                   |
|                   |               |                 |                                                 | On the variable level it is specified via a type annotation on    |
|                   |               |                 |                                                 | the attribute: ``my_var_1: my_wanted_type``.                      |
|                   |               |                 |                                                 |                                                                   |
|                   |               |                 |                                                 | However it can be also specified on the class level, then it acts |
|                   |               |                 |                                                 | as a default when the annotation is not provided:                 |
|                   |               |                 |                                                 |                                                                   |
|                   |               |                 |                                                 | ``class MyConfig(ecological.Config, wanted_type=int, ...)``       |
+-------------------+---------------+-----------------+-------------------------------------------------+-------------------------------------------------------------------+

The following rules apply when options are resolved:

- when options are specified on both levels (variable and class),
  the variable ones take precedence over class ones,
- when some options are missing on the variable level, their default values
  are taken from the class level,
- it is not necessary to assign an ``ecological.Variable`` instance to
  change the behavior; it can still be changed on the class level (globally).

Autoloading
------------
You can defer or disable autoloading of variable values by specifying the ``autoload`` option in the class definition.

On class creation (default)
~~~~~~~~~~~~~~~~~~~~~~~~~~~
When you do not provide an option, values are loaded immediately on class creation and assigned to class attributes:

.. code-block:: python

    class Configuration(ecological.Config):
        port: int
    # Values already read and set at this point.
    # assert Configuration.port == <value-of-PORT-env-var>

Never
~~~~~
When you choose this option, no autoloading happens. To set variable values, you must call the ``Config.load`` method explicitly:

.. code-block:: python

    class Configuration(ecological.Config, autoload=ecological.Autoload.NEVER):
        port: int
    # Values not set at this point.
    # Accessing Configuration.port would throw AttributeError.

    Configuration.load()
    # Values read and set at this point.
    # assert Configuration.port == <value-of-PORT-env-var>

On object instance initialization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
If you prefer to load and store attribute values on the object instance instead of the class itself, the ``Autoload.OBJECT`` strategy can be used:

.. code-block:: python

    class Configuration(ecological.Config, autoload=ecological.Autoload.OBJECT):
        port: int
    # Values not set at this point.

    config = Configuration()
    # Values read and set at this point on ``config``.
    # assert config.port == <value-of-PORT-env-var>
    # Accessing ``Configuration.port`` would throw AttributeError.

Caveats and Known Limitations
=============================

- ``Ecological`` doesn't support (public) methods in ``Config`` classes

.. _PEP484: https://www.python.org/dev/peps/pep-0484/
.. _PEP526: https://www.python.org/dev/peps/pep-0526/
