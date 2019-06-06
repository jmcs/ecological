import ast
import collections
import dataclasses
import enum
import os
import warnings
from typing import (
    Any,
    AnyStr,
    ByteString,
    Callable,
    Dict,
    FrozenSet,
    List,
    NewType,
    Optional,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
    get_type_hints,
)

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
    Tuple: tuple,
}

WantedType = TypeVar("WantedType")


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


VariableName = NewType("VariableName", Union[str, bytes])
VariableValue = NewType("VariableValue", Union[str, bytes])


class Variable:
    """
    Class to handle specific properties
    """

    def __init__(
        self,
        variable_name: VariableName,
        default=_NO_DEFAULT,
        *,
        transform: Callable[[str, type], Any] = cast,
        source: Dict[VariableName, VariableValue] = os.environ,
    ):
        """
        :param variable_name: Environment variable to get
        :param default: Default value.
        :param transform: function to convert the env string to the wanted type
        """
        self.name = variable_name
        self.default = default
        self.transform = transform
        self.source = source

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
            raw_value = self.source[self.name]
        except KeyError:
            if self.default is _NO_DEFAULT:
                raise AttributeError(f"Configuration error: '{self.name}' is not set.")
            else:
                return self.default

        try:
            value = self.transform(raw_value, wanted_type)
        except (ValueError, SyntaxError) as e:
            raise ValueError(f"Invalid configuration for '{self.name}': {e}.")

        return value


class Autoload(enum.Enum):
    """
    Represents different approaches to the attribute values
    autoloading on ``Config`` class:

    - ``Autoload.CLASS`` - load variable values to class on its subclass creation,
    - ``Autoload.OBJECT`` - load variable values to object instance on its initialization,
    - ``Autoload.NEVER`` - does not perform any autoloading; ``Config.load`` method needs to called explicitly.
    """

    CLASS = "CLASS"
    OBJECT = "OBJECT"
    NEVER = "NEVER"


@dataclasses.dataclass
class _Options:
    """
    Acts as a container for metaclass keyword arguments provided during 
    ``Config`` class creation. 
    """

    prefix: Optional[str] = None
    autoload: Autoload = Autoload.CLASS

    @classmethod
    def from_metaclass_kwargs(cls, metaclass_kwargs: Dict) -> "Options":
        """
        Produces ``_Options`` instance from given dictionary.
        Items are deleted from ``metaclass_kwargs`` as a side-effect.
        """
        options_kwargs = {}
        for field in dataclasses.fields(cls):
            value = metaclass_kwargs.pop(field.name, None)
            if value is None:
                continue

            options_kwargs[field.name] = value

        try:
            return cls(**options_kwargs)
        except TypeError as e:
            raise ValueError(
                f"Invalid options for Config class: {metaclass_kwargs}."
            ) from e


class Config:
    """
    When ``Config`` subclasses are created, by default ``Ecological`` will set their
    attributes automatically based on the corresponding environment variables.

    For example if ``DEBUG`` is set to ``"True"`` and ``PORT`` is set to ``"8080"`` and your
    configuration class looks like::

        class Configuration(ecological.Config):
            port: int
            debug: bool

    ``Configuration.port`` will be ``8080`` and ``Configuration.debug`` will be ``True``, with the
    correct types.

    It is possible to defer the calculation of attribute values by specifying the ``autoload``
    keyword argument on your class definition. For possible strategies see the ``Autoload`` class definition.
    
    Caveats and Known Limitations
    =============================

    - ``Ecological`` doesn't support (public) methods in ``Config`` classes.

    Further Information
    ===================

    Further information is available in the ``README.rst``.
    """

    _options: _Options

    def __init_subclass__(cls, **kwargs):
        cls._options = _Options.from_metaclass_kwargs(kwargs)
        super().__init_subclass__(**kwargs)
        if cls._options.autoload is Autoload.CLASS:
            cls.load(cls)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        cls = type(self)
        if cls._options.autoload is Autoload.OBJECT:
            cls.load(self)

    @classmethod
    def load(cls: "Config", target_obj: Optional[object] = None):
        """
        The class' ``attribute_dict`` includes attributes with a default value and some special
        keys like ``__annotations__`` which includes annotations of all attributes, including the
        ones that don't have a value.

        To simplify the class building process the annotated attributes that don't have a value
        in the ``attribute_dict`` are injected with a ``_NO_DEFAULT`` sentinel object.

        After this all the public attributes of the class are iterated over and one
        of three things is performed:

        - If the attribute value is an instance of ``Config`` it is kept as is to allow nested
            configuration.
        - If the attribute value is of type ``Variable``, ``Config`` will call its ``get``
            method with the attribute's annotation type as the only parameter
        - Otherwise, ``Config`` will create a ``Variable`` instance, with
            "{prefix}_{attribute_name}" as the environment variable name and the attribute value
            (the default value or ``_NO_DEFAULT``) and do the same process as in the previous point.
        """
        target_obj = target_obj or cls
        annotations: Dict[str, type] = get_type_hints(cls)
        attribute_dict = vars(cls).copy()
        prefix = cls._options.prefix

        # Add attributes without defaults to the the attribute dict
        attribute_dict.update(
            {
                attribute_name: _NO_DEFAULT
                for attribute_name in annotations.keys()
                if attribute_name not in attribute_dict
            }
        )

        for attribute_name, default_value in attribute_dict.items():
            if attribute_name.startswith("_"):
                # private attributes are not changed
                continue
            if isinstance(default_value, Variable):
                attribute = default_value
            elif isinstance(default_value, Config):
                # passthrough for nested configs
                setattr(target_obj, attribute_name, default_value)
                continue
            else:
                if prefix:
                    env_variable_name = f"{prefix}_{attribute_name}".upper()
                else:
                    env_variable_name = attribute_name.upper()
                attribute = Variable(env_variable_name, default_value)

            attribute_type = annotations.get(
                attribute_name, str
            )  # by default attributes are strings
            value = attribute.get(attribute_type)
            setattr(target_obj, attribute_name, value)


# DEPRECATED: For backward compatibility purposes only
class AutoConfig(Config, autoload=Autoload.NEVER):
    def __init_subclass__(cls, prefix: Optional[str] = None, **kwargs):
        warnings.warn(
            "ecological.AutoConfig is deprecated, please use ecological.Config instead.",
            DeprecationWarning,
        )
        super().__init_subclass__(prefix=prefix, autoload=Autoload.CLASS)
