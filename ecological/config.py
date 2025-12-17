"""
The heart of the library.
See ``README.rst`` and ``Configuration`` class for more details.
"""

import dataclasses
import enum
import os
import warnings
from typing import (
    Any,
    Dict,
    Optional,
    Protocol,
    Type,
    get_type_hints,
    cast as typing_cast,
)

# Aliased in order to avoid a conflict with the _Options.transform attribute.
from . import transform as transform_module

_NO_DEFAULT = object()
VariableName = str
VariableValue = str | bytes
Source = Dict[VariableName, VariableValue]


class TransformCallable(Protocol):
    def __call__(self, representation: str, wanted_type: Type) -> Any: ...


class VariableNameFactory(Protocol):
    def __call__(
        self, attr_name: str, prefix: Optional[str] = None
    ) -> VariableName: ...


class Autoload(enum.Enum):
    """
    Represents different approaches to the attribute values
    autoloading on ``Config`` class:

    - ``Autoload.CLASS`` - load variable values to class on its subclass creation,
    - ``Autoload.OBJECT`` - load variable values to object instance on its initialization,
    - ``Autoload.NEVER`` - does not perform any autoloading; ``Config.load`` method needs to be called explicitly.
    """

    CLASS = "CLASS"
    OBJECT = "OBJECT"
    NEVER = "NEVER"


def _generate_environ_name(
    attr_name: str, prefix: Optional[str] = None
) -> VariableName:
    """
    Outputs an environment variable name based on the ``Configuration``'s
    subclass attribute name and the optional prefix.

    >>> _generate_environ_name("attr_name", prefix="prefixed")
    "PREFIXED_ATTR_NAME"
    """
    variable_name = ""
    if prefix:
        variable_name += f"{prefix}_"
    variable_name += attr_name

    return variable_name.upper()


@dataclasses.dataclass
class _Options:
    """
    Acts as the container for metaclass keyword arguments provided during
    ``Config`` class creation.
    """

    prefix: Optional[str] = None
    autoload: Autoload = Autoload.CLASS
    source: Source = dataclasses.field(default_factory=lambda: os.environ)
    transform: TransformCallable = transform_module.cast
    wanted_type: Type = str
    variable_name: VariableNameFactory = _generate_environ_name

    @classmethod
    def from_dict(cls, options_dict: Dict) -> "_Options":
        """
        Produces ``_Options`` instance from given dictionary.
        Items are deleted from ``options_dict`` as a side-effect.
        """
        options_kwargs = {}
        for field in dataclasses.fields(cls):
            value = options_dict.pop(field.name, None)
            if value is None:
                continue

            options_kwargs[field.name] = value

        try:
            return cls(**options_kwargs)
        except TypeError as e:
            raise ValueError(
                f"Invalid options for Config class: {options_dict}."
            ) from e


@dataclasses.dataclass
class Variable:
    """
    Represents a single variable from the configuration source
    and user preferences how to process it.
    """

    variable_name: VariableName | None = None
    default: Any = _NO_DEFAULT
    transform: TransformCallable | None = None
    source: Source | None = None
    wanted_type: Type = dataclasses.field(init=False)

    def set_defaults(
        self,
        *,
        variable_name: VariableName,
        transform: TransformCallable,
        source: Source,
        wanted_type: Type,
    ):
        """
        Sets missing properties of the instance of `Variable`` in order to
        be able to fetch its value with the ``Variable.get`` method.
        """
        self.variable_name = self.variable_name or variable_name
        self.transform = self.transform or transform
        self.source = self.source or source
        self.wanted_type = wanted_type

    def get(self) -> VariableValue:
        """
        Fetches a value of variable from the ``self.source`` and invoke the
        ``self.transform`` operation on it. Falls back to ``self.default``
        if the value is not found.
        """
        if self.source is None:
            raise ValueError("Source for variable is not set.")

        if self.variable_name is None:
            raise ValueError("Variable name is not set.")

        try:
            raw_value = self.source[self.variable_name]
        except KeyError:
            if self.default is _NO_DEFAULT:
                raise AttributeError(
                    f"Configuration error: {self.variable_name!r} is not set."
                ) from None
            else:
                return self.default

        if self.transform is None:
            raise ValueError(
                f"Transform function for {self.variable_name!r} is not set."
            )

        try:
            return self.transform(typing_cast(str, raw_value), self.wanted_type)
        except (ValueError, SyntaxError) as e:
            raise ValueError(
                f"Invalid configuration for {self.variable_name!r}."
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
        cls._options = _Options.from_dict(kwargs)
        super().__init_subclass__(**kwargs)
        if cls._options.autoload is Autoload.CLASS:
            cls.load(cls)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        cls = type(self)
        if cls._options.autoload is Autoload.OBJECT:
            cls.load(self)

    @classmethod
    def load(cls: Type["Config"], target_obj: Optional[object] = None):
        """
        Fetches and converts values of variables declared as attributes on ``cls`` according
        to their specification and finally assigns them to the corresponding attributes
        on ``target_obj`` (which by default is ``cls`` itself).
        """
        target_obj = target_obj or cls
        cls_dict = vars(cls).copy()
        attr_types: Dict[str, type] = get_type_hints(cls)
        # There is no single place that has all class attributes regardless of
        # having default value or not. Thus the keys of cls.__annotations__ and
        # cls.__dict__ are merged providing a complete list.
        attr_names = set(cls_dict).union(attr_types.keys())

        for attr_name in attr_names:
            # Omit private and nested configuration attributes
            # (Attribute value can be the instance of Config itself).
            if attr_name.startswith("_"):
                continue
            attr_value = cls_dict.get(attr_name, _NO_DEFAULT)
            if type(attr_value) is cls:
                continue
            attr_type = attr_types.get(attr_name, cls._options.wanted_type)

            if isinstance(attr_value, Variable):
                variable = attr_value
            else:
                variable = Variable(default=attr_value)
            variable.set_defaults(
                variable_name=cls._options.variable_name(
                    attr_name, prefix=cls._options.prefix
                ),
                transform=cls._options.transform,
                source=cls._options.source,
                wanted_type=attr_type,
            )

            setattr(target_obj, attr_name, variable.get())


class AutoConfig(Config, autoload=Autoload.NEVER):
    """
    DEPRECATED: For backward compatibility purposes only; please use ``ecological.Config`` instead.
    """

    def __init_subclass__(cls, prefix: Optional[str] = None, **kwargs):
        warnings.warn(
            "ecological.AutoConfig is deprecated, please use ecological.Config instead.",
            DeprecationWarning,
        )
        super().__init_subclass__(prefix=prefix, autoload=Autoload.CLASS)
