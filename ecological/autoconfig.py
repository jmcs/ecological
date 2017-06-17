from typing import (AnyStr, ByteString, Callable, Dict, FrozenSet, GenericMeta, List, Optional, Set,
                    Tuple, Any, TypeVar, Union)

import os

import ast

import collections

_NOT_IMPORTED = object()

try:  # Types added in Python 3.6.1
    from typing import Counter, Deque
except ImportError:
    Deque = Counter = _NOT_IMPORTED

_NO_DEFAULT = object()
TYPES_THAT_NEED_TO_BE_PARSED = [bool, list, set, tuple, dict]
TYPING_TO_REGULAR_TYPE = {
    AnyStr: str,
    ByteString: bytes,
    Counter: collections.Counter,
    Deque: collections.deque,
    Dict: dict,
    FrozenSet: frozenset,
    List: list,
    Set: set,
    Tuple: tuple
}

WantedType = TypeVar('WantedType')


def cast(representation: str, wanted_type: type):
    """
    Casts the string ``representation`` to the ``wanted type``.
    This function also supports some ``typing`` types by mapping them to 'real' types.

    Some types, like ``bool`` and ``list``, need to be parsed with ast.
    """
    # If it's a typing meta replace it with the real type
    wanted_type = TYPING_TO_REGULAR_TYPE.get(wanted_type, wanted_type)
    if isinstance(wanted_type, GenericMeta):
        # Fallback to try to replace typing metas to real types
        wanted_type = wanted_type.__bases__[0]
    if wanted_type in TYPES_THAT_NEED_TO_BE_PARSED:
        value = (ast.literal_eval(representation)
                 if isinstance(representation, str)
                 else representation)
        return wanted_type(value)
    else:
        return wanted_type(representation)


class Variable:
    """
    Class to handle specific properties
    """

    def __init__(self, variable_name: str, default=_NO_DEFAULT, *,
                 transform: Callable[[str, type], Any] = cast):
        """
        :param variable_name: Environment variable to get
        :param default: Default value.
        :param transform: function to convert the env string to the wanted type
        """
        self.name = variable_name
        self.default = default
        self.transform = transform

    def get(self, wanted_type: WantedType) -> Union[WantedType, Any]:
        """
        Gets ``self.variable_name`` from the environment and tries to cast it to ``wanted_type``.

        If ``self.default`` is ``_NO_DEFAULT`` and the env variable is not set this will raise an
        ``AttributeError``, if the ``self.default`` is set to something else, its value will be
        returned.

        If casting fails, this function will raise a ``ValueError``.

        :param wanted_type: type to return
        :return: value as wanted_type
        """
        try:
            raw_value = os.environ[self.name]
        except KeyError:
            if self.default is _NO_DEFAULT:
                raise AttributeError(f"Configuration error: '{self.name}' is not set.")
            else:
                return self.default

        try:
            value = self.transform(raw_value, wanted_type)
        except ValueError as e:
            raise ValueError(f"Invalid configuration for '{self.name}': {e}.")

        return value


class ConfigMeta(type):
    """
    Metaclass that does the "magic" behind ``AutoConfig``.
    """

    # noinspection PyInitNewSignature
    def __new__(mcs, class_name, super_classes, attribute_dict: Dict[str, Any],
                prefix: Optional[str] = None):
        """
        The new class' ``attribute_dict`` includes attributes with a default value and some special
        keys like ``__annotations__`` which includes annotations of all attributes, including the
        ones that don't have a value.

        To simplify the class building process ``ConfigMeta`` injects the annotated attributes that
        don't have a value in the ``attribute_dict`` with a ``_NO_DEFAULT`` sentinel object.

        After this ``ConfigMeta`` goes through all the public attributes of the class, and does one
        of three things:

        - If the attribute value is an instance of ``ConfigMeta`` it is kept as is to allow nested
          configuration.
        - If the attribute value is of type ``Variable``, ``ConfigMeta`` will class its ``get``
          method with the attribute's annotation type as the only parameter
        - Otherwise, ``ConfigMeta`` will create a ``Variable`` instance, with
          "{prefix}_{attribute_name}" as the environment variable name and the attribute value
          (the default value or ``_NO_DEFAULT``) and do the same process as the previous point.
        """
        annotations: Dict[str, type] = attribute_dict.get('__annotations__', {})

        # Add attributes without defaults to the the attribute dict
        attribute_dict.update({attribute_name: _NO_DEFAULT
                               for attribute_name in annotations.keys()
                               if attribute_name not in attribute_dict})

        for attribute_name, default_value in attribute_dict.items():
            if attribute_name.startswith('_'):
                # private attributes are not changed
                continue
            if isinstance(default_value, Variable):
                attribute = default_value
            elif isinstance(default_value, ConfigMeta):
                # passthrough for nested configs
                attribute_dict[attribute_name] = default_value
                continue
            else:
                if prefix:
                    env_variable_name = f"{prefix}_{attribute_name}".upper()
                else:
                    env_variable_name = attribute_name.upper()
                attribute = Variable(env_variable_name, default_value)

            attribute_type = annotations.get(attribute_name,
                                             str)  # by default attributes are strings
            value = attribute.get(attribute_type)
            attribute_dict[attribute_name] = value

        # noinspection PyTypeChecker
        return type.__new__(mcs, class_name, super_classes, attribute_dict)


class AutoConfig(metaclass=ConfigMeta):
    """
    When ``AutoConfig`` sub classes are created ``Ecological`` will automatically set it's
    attributes based on the environment variables.

    For example if ``DEBUG`` is set to ``"True"`` and ``PORT`` is set to ``"8080"`` and your
    configuration class looks like::

        class Configuration(ecological.AutoConfig):
            port: int
            debug: bool

    ``Configuration.port`` will be ``8080`` and ``Configuration.debug`` will be ``True``, with the
    correct types.

    Caveats and Known Limitations
    =============================

    - ``Ecological`` doesn't support (public) methods in ``AutoConfig`` classes.

    Further Information
    ===================

    Further information is available in the ``README.rst``.

    """
    # TODO Document errors, typing support, prefix
    pass
