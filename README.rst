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

    class Configuration(ecological.AutoConfig):
        port: int
        debug: bool
        log_level: str = "INFO"

And then set the environment variables ``PORT``, ``DEBUG`` and ``LOG_LEVEL``. ``Ecological`` will automatically set the
class properties from the environment variables with the same (but upper cased) name.

The values are set at the class definition type and assigned to the class itself (i.e. the class doesn't need to be
instantiated).

Typing Support
==============
``Ecological`` also supports some of the types defined in PEP484_, for example:

.. code-block:: python


    class Configuration(ecological.AutoConfig):
        list_of_values: List[str]

Will automatically parse the environment variable value as a list.

.. note:: Please note that while this will ensure ``Configuration.list_of_values`` is a list it will not check that it
          contains only strings.

Prefixed Configuration
======================
You can also decide to prefix your application configuration, for example, to avoid collisions:

.. code-block:: python

    class Configuration(ecological.AutoConfig, prefix='myapp'):
        home: str


In this case the ``home`` property will be fetched from the ``MYAPP_HOME`` environment property.


Caveats and Known Limitations
=============================

- ``Ecological`` doesn't support (public) methods in ``AutoConfig`` classes


Advanced Usage
==============

Fine-grained control
--------------------
You can control how the configuration properties are set by providing a ``ecological.Variable`` instance as the default
value.

``ecological.Variable`` receives the following parameters:

- ``variable_name`` (mandatory) - exact name of the environment variable that will be used.
- ``default`` (optional) - default value for the property if it isn't set.
- ``transform`` (optional) - function that converts the string in the environment to the value and type you
  expect in your application. The default ``transform`` function will try to cast the string to the annotation 
  type of the property.

Transformation function
.......................

The transformation function receive two parameters, a string ``representation`` with the raw value, and a
``wanted_type`` with the value of the annotation (usually, but not mandatorily a ``type``).

Nested Configuration
--------------------
``Ecological.AutoConfig`` also supports nested configurations, for example:


.. code-block:: python


    class Configuration(ecological.AutoConfig):
        integer: int

        class Nested(ecological.AutoConfig, prefix='nested'):
            boolean: bool

This way you can group related configuration properties hierarchically.

.. _PEP484: https://www.python.org/dev/peps/pep-0484/
.. _PEP526: https://www.python.org/dev/peps/pep-0526/
