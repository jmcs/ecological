"""
Provides ``cast`` function (default transform function for variables of `config.Config`)
mitigating a number of `typing` module quirks that happen across Python versions.
"""
import ast
import collections
from typing import AnyStr, ByteString, Dict, FrozenSet, List, Set, Tuple

try:
    from typing import GenericMeta

    PEP560 = False
except ImportError:
    GenericMeta = None
    PEP560 = True


_NOT_IMPORTED = object()

try:  # Types added in Python 3.6.1
    from typing import Counter, Deque
except ImportError:
    Deque = Counter = _NOT_IMPORTED

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


def _cast_typing_old(wanted_type: type) -> type:
    """
    Casts typing types in Python < 3.7
    """
    wanted_type = TYPING_TO_REGULAR_TYPE.get(wanted_type, wanted_type)
    if isinstance(wanted_type, GenericMeta):
        # Fallback to try to map complex typing types to real types
        for base in wanted_type.__bases__:
            # if not isinstance(base, Generic):
            #    # If it's not a Generic class then it can be a real type
            #    wanted_type = base
            #    break
            if base in TYPING_TO_REGULAR_TYPE:
                # The mapped type in bases is most likely the base type for complex types
                # (for example List[int])
                wanted_type = TYPING_TO_REGULAR_TYPE[base]
                break
    return wanted_type


def _cast_typing_pep560(wanted_type: type) -> type:
    """
    Casts typing types in Python >= 3.7
    See https://www.python.org/dev/peps/pep-0560/
    """
    # If it's in the dict in Python >= 3.7 we know how to handle it
    if wanted_type in TYPING_TO_REGULAR_TYPE:
        return TYPING_TO_REGULAR_TYPE.get(wanted_type, wanted_type)

    try:
        return wanted_type.__origin__
    except AttributeError:  # This means it's (probably) not a typing type
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
        wanted_type = wanted_type.__supertype__

    # If it's another typing type replace it with the real type
    if PEP560:  # python >= 3.7
        wanted_type = _cast_typing_pep560(wanted_type)
    else:
        wanted_type = _cast_typing_old(wanted_type)

    if wanted_type in TYPES_THAT_NEED_TO_BE_PARSED:
        value = (
            ast.literal_eval(representation)
            if isinstance(representation, str)
            else representation
        )
        return wanted_type(value)
    else:
        return wanted_type(representation)
