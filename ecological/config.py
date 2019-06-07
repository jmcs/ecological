import dataclasses
import enum
import os
import warnings
from typing import Any, Callable, Dict, NewType, Optional, Union, get_type_hints

from . import casting

VariableName = NewType("VariableName", Union[str, bytes])
VariableValue = NewType("VariableValue", Union[str, bytes])
Source = NewType("Source", Dict[VariableName, VariableValue])
TransformCallable = NewType("TransformCallable", Callable[[VariableValue, type], Any])
_NO_DEFAULT = object()


class Variable:
    def __init__(
        self,
        variable_name: Optional[VariableName] = None,
        default: Any = _NO_DEFAULT,
        *,
        transform: Optional[TransformCallable] = None,
        source: Optional[Source] = None,
    ):
        self.name = variable_name
        self.default = default
        self.transform = transform
        self.source = source


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
    source: Source = os.environ
    transform: TransformCallable = casting.cast

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
    def fetch_source_value(
        cls: "Config", attr_name: str, attr_value: Any, attr_type: type
    ):
        if isinstance(attr_value, Variable):
            source_name = attr_value.name
            default = attr_value.default
            transform = attr_value.transform or cls._options.transform
            source = attr_value.source or cls._options.source
        else:
            source_name = attr_name
            if cls._options.prefix:
                source_name = f"{cls._options.prefix}_{source_name}"
            source_name = source_name.upper()

            default = attr_value
            transform = cls._options.transform
            source = cls._options.source

        try:
            raw_value = source[source_name]
        except KeyError as e:
            if default is _NO_DEFAULT:
                raise AttributeError(
                    f"Configuration error: '{source_name}' is not set."
                ) from e
            else:
                return default

        try:
            return transform(raw_value, attr_type)
        except (ValueError, SyntaxError) as e:
            raise ValueError(f"Invalid configuration for '{source_name}': {e}.")

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
        cls_dict = vars(cls).copy()
        attr_types: Dict[str, type] = get_type_hints(cls)
        attr_names = set(cls_dict).union(attr_types.keys())

        for attr_name in attr_names:
            if attr_name.startswith("_") or isinstance(attr_name, cls):
                continue

            attr_value = cls_dict.get(attr_name, _NO_DEFAULT)
            attr_type = attr_types.get(attr_name, str)

            source_value = cls.fetch_source_value(attr_name, attr_value, attr_type)
            setattr(target_obj, attr_name, source_value)


# DEPRECATED: For backward compatibility purposes only
class AutoConfig(Config, autoload=Autoload.NEVER):
    def __init_subclass__(cls, prefix: Optional[str] = None, **kwargs):
        warnings.warn(
            "ecological.AutoConfig is deprecated, please use ecological.Config instead.",
            DeprecationWarning,
        )
        super().__init_subclass__(prefix=prefix, autoload=Autoload.CLASS)
