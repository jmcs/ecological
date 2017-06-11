from typing import (AnyStr, ByteString, Callable, Counter, Deque, Dict, FrozenSet,
                    GenericMeta, List, Optional, Set, Tuple, Any, TypeVar)

import os

import ast

import collections

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
    This function also supports some ``typing``types by mapping them to 'real' types.

    Some types need to be parsed with ast.
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

    def get(self, wanted_type: WantedType) -> WantedType:
        """
        Gets ``self.variable_name`` from the environment and tries to cast it to ``wanted_type``.
        If ``self.default`` is ``_NO_DEFAULT`` and the env variable is not set this will raise an ``AttributeError``.
        If casting fails, this function will raise a ``ValueError``.

        :param wanted_type: type to return
        :return: value as wanted_type
        """
        raw_value = os.environ.get(self.name, self.default)
        if raw_value is _NO_DEFAULT:
            raise AttributeError(f"Configuration error: '{self.name}' is not set.")

        try:
            value = self.transform(raw_value, wanted_type)
        except ValueError as e:
            raise ValueError(f"Invalid configuration for '{self.name}': {e}.")

        return value


class ConfigMeta(type):
    def __new__(cls, class_name, super_classes, attribute_dict: Dict[str, Any],
                prefix: Optional[str] = None):
        # TODO document this
        annotations: Dict[str, type] = attribute_dict.get('__annotations__', {})

        # Add attributes without defaults to the the attribute dict
        attribute_dict.update({attribute_name: _NO_DEFAULT
                               for attribute_name in annotations.keys()
                               if attribute_name not in attribute_dict})

        for attribute_name, default_value in attribute_dict.items():
            if attribute_name.startswith('_'):
                # private attributes are not changed
                continue
            default = attribute_dict.get(attribute_name, _NO_DEFAULT)
            if isinstance(default, Variable):
                attribute = default
            elif isinstance(default, ConfigMeta):
                # passthrough for nested configs
                attribute_dict[attribute_name] = default
                continue
            else:
                if prefix:
                    env_variable_name = f"{prefix}_{attribute_name}".upper()
                else:
                    env_variable_name = attribute_name.upper()
                attribute = Variable(env_variable_name, default)

            attribute_type = annotations.get(attribute_name, str)  # by default attributes are strings
            value = attribute.get(attribute_type)
            attribute_dict[attribute_name] = value

        return type.__new__(cls, class_name, super_classes, attribute_dict)


class AutoConfig(metaclass=ConfigMeta):
    # TODO document this
    pass
