.. image:: https://travis-ci.org/jmcs/ecological.svg?branch=master
    :target: https://travis-ci.org/jmcs/ecological

.. image:: https://api.codacy.com/project/badge/Grade/1ff45d0e1a5a40b8ad0569e3edb0539d
   :alt: Codacy Badge
   :target: https://www.codacy.com/app/jmcs/ecological?utm_source=github.com&utm_medium=referral&utm_content=jmcs/ecological&utm_campaign=badger
   
.. image:: https://api.codacy.com/project/badge/Coverage/1ff45d0e1a5a40b8ad0569e3edb0539d    
   :target: https://www.codacy.com/app/jmcs/ecological?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=jmcs/ecological&amp;utm_campaign=Badge_Coverage

==========
Ecological
==========

``Ecological`` combines PEP526_ and environment variables to make the configuration of
`12 factor apps <https://12factor.net/config>`_ easy.

Getting Started
===============
``Ecological`` automatically gets and converts environment variables according to the configuration class definition.

For example, imagine your application has a configurable (integer) Port and (boolean) Debug flag and a (string) Log
Level, that is ``INFO`` by default, you could simply declare your configuration as:

.. code-block:: python

    class Configuration(ecological.Config):
        port: int
        debug: bool
        log_level: str = "INFO"

And then set the environment variables ``PORT``, ``DEBUG`` and ``LOG_LEVEL``. ``Ecological`` will automatically set the
class properties from the environment variables with the same (but upper cased) name.

By default the values are set at the class definition type and assigned to the class itself (i.e. the class doesn't need to be
instantiated). If needed this behavior can be changed (see the next section).

Typing Support
==============
``Ecological`` also supports some of the types defined in PEP484_, for example:

.. code-block:: python


    class Configuration(ecological.Config):
        list_of_values: List[str]

Will automatically parse the environment variable value as a list.

.. note:: Please note that while this will ensure ``Configuration.list_of_values`` is a list it will not check that it
          contains only strings.

Prefixed Configuration
======================
You can also decide to prefix your application configuration, for example, to avoid collisions:

.. code-block:: python

    class Configuration(ecological.Config, prefix='myapp'):
        home: str


In this case the ``home`` property will be fetched from the ``MYAPP_HOME`` environment property.

Nested Configuration
=====================
``Ecological.Config`` also supports nested configurations, for example:

.. code-block:: python


    class Configuration(ecological.Config):
        integer: int

        class Nested(ecological.Config, prefix='nested'):
            boolean: bool

This way you can group related configuration properties hierarchically.

Fine-grained Control
====================
You can control how the configuration properties are set by providing a ``ecological.Variable`` instance as the default
value for an attribute or by specifying global options on the class level:

.. code-block:: python

    my_source: Dict = {"KEY1": "VALUE1"}

    class Configuration(ecological.Config, transform=lambda v, wt: v, wanted_type=int, ...):
        my_var1: WantedType = ecological.Variable(transform=lambda v, wt: wt(v), source=my_source, ...)
        my_var2: str
        # ...

All possible options and their meaning can be found in the table below:

+-------------------+---------------+-----------------+-------------------------------------------------+-------------------------------------------------------------------+
| Option            | Class level   | Variable level  | Default                                         | Description                                                       |
+===================+===============+=================+=================================================+===================================================================+
| ``prefix``        | yes           | no              | ``None``                                        | A prefix that is prepended when a variable name is derived from   |
|                   |               |                 |                                                 | an attribute name.                                                |
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
|                   |               |                 | (``ecological.casting.cast``).                  | and ``wanted_type`` you expect with the following signature:      |
|                   |               |                 |                                                 |                                                                   |
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

.. note:: Please mind that in the case of specyfing options on both levels (variable and class)
          the variable ones take precedence over class ones.

Autoloading
===========
It is possible to defer/disable autoloading (setting) of variable values by specifying the ``autoload`` option on class definition.

On class creation (default)
---------------------------
When no option is provided values are loaded immediately on class creation and assigned to class attributes:

.. code-block:: python

    class Configuration(ecological.Config):
        port: int
    # Values already read and set at this point.
    # assert Configuration.port == <value-of-PORT-env-var>

Never
------
When this option is chosen, no autoloading happens. In order to set variable values, the ``Config.load`` method needs to be called explicitly:

.. code-block:: python

    class Configuration(ecological.Config, autoload=ecological.Autoload.NEVER):
        port: int
    # Values not set at this point.
    # Accessing Configuration.port would throw AttributeError.

    Configuration.load()
    # Values read and set at this point.
    # assert Configuration.port == <value-of-PORT-env-var>

On object instance initialization
----------------------------------
If it is preferred to load and store attribute values on the object instance instead of the class itself, the ``Autoload.OBJECT`` strategy can be used:

.. code-block:: python

    class Configuration(ecological.Config, autoload=ecological.Autoload.OBJECT):
        port: int
    # Values not set at this point.

    config = Configuration()
    # Values read and set at this point on ``config``.
    # assert config.port == <value-of-PORT-env-var>
    # Accessing ``Configuration.port`` would throw AttributeError.

Tutorial
========
The `tutorial <tutorial.ipynb>`_ includes real examples of all the available
features.

Caveats and Known Limitations
=============================

- ``Ecological`` doesn't support (public) methods in ``Config`` classes

.. _PEP484: https://www.python.org/dev/peps/pep-0484/
.. _PEP526: https://www.python.org/dev/peps/pep-0526/
