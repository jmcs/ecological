"""
Provides ``cast`` function (default transform function for variables of `config.Config`)
mitigating a number of `typing` module quirks that happen across Python versions.
"""

import ast
import collections
from typing import (
    AnyStr,
    ByteString,
    Dict,
    FrozenSet,
    List,
    Set,
    Tuple,
    Counter,
    Deque,
    cast as typing_cast,
)


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
    Tuple: tuple,
}


def _cast_typing_pep560(wanted_type: type) -> type:
    """
    Casts typing types in Python >= 3.7
    See https://www.python.org/dev/peps/pep-0560/
    """
    # If it's in the dict in Python >= 3.7 we know how to handle it
    if wanted_type in TYPING_TO_REGULAR_TYPE:
        return TYPING_TO_REGULAR_TYPE.get(wanted_type, wanted_type)

    if hasattr(wanted_type, "__origin__"):
        return typing_cast(type, wanted_type.__origin__)

    # This means it's (probably) not a typing type
    return wanted_type


def cast(representation: str, wanted_type: type):
    """
    Casts the string ``representation`` to the ``wanted type``.
    This function also supports some ``typing`` types by mapping them to 'real' types.

    Some types, like ``bool`` and ``list``, need to be parsed with ast.
    """
    # The only distinguishing feature of NewType (both before and after PEP560)
    # is its __supertype__ field, which it is the only "typing" member to have.
    # Since newtypes can be nested, we process __supertype__ as long as available.
    while hasattr(wanted_type, "__supertype__"):
        wanted_type = typing_cast(type, wanted_type.__supertype__)

    wanted_type = _cast_typing_pep560(wanted_type)

    if wanted_type in TYPES_THAT_NEED_TO_BE_PARSED:
        value = (
            ast.literal_eval(representation)
            if isinstance(representation, str)
            else representation
        )
        return wanted_type(value)
    else:
        return wanted_type(representation)
