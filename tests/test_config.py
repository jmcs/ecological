#!/usr/bin/python3

import os
import typing

import pytest

import ecological

pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning")


@pytest.fixture(
    params=[
        pytest.param(ecological.AutoConfig, id="AutoConfig"),
        pytest.param(ecological.Config, id="Config"),
    ]
)
def base_class(request):
    return request.param


def test_regular_types(monkeypatch, base_class):
    monkeypatch.setenv("INTEGER", "42")
    monkeypatch.setenv("BOOLEAN", "False")
    monkeypatch.setenv("ANY_STR", "AnyStr Example")
    monkeypatch.setenv("TEXT", "Text Example")
    monkeypatch.setenv("DICT", "{'key': 'value'}")
    monkeypatch.setenv("LIST", "[1, 2, 3]")

    class Configuration(base_class):
        integer: int
        boolean: bool
        any_str: typing.AnyStr
        default: str = "Default Value"
        text: typing.Text
        dict: typing.Dict[str, str]
        list: typing.List[int]

    assert Configuration.integer == 42
    assert Configuration.boolean is False
    assert Configuration.any_str == "AnyStr Example"
    assert Configuration.default == "Default Value"
    assert Configuration.text == "Text Example"
    assert Configuration.dict == {"key": "value"}
    assert Configuration.list == [1, 2, 3]


def test_nested(monkeypatch, base_class):
    monkeypatch.setenv("INTEGER", "42")
    monkeypatch.setenv("NESTED_BOOLEAN", "False")

    class Configuration(base_class):
        integer: int

        class Nested(ecological.AutoConfig, prefix="nested"):
            boolean: bool

    assert Configuration.integer == 42
    assert Configuration.Nested.boolean is False


def test_explicit_variable(monkeypatch, base_class):
    monkeypatch.setenv("TEST_Integer", "42")

    class Configuration(base_class, prefix="this_is_going_to_be_ignored"):
        var1a = ecological.Variable("TEST_Integer", transform=lambda v, wt: int(v))
        var1b: str = ecological.Variable("TEST_Integer", transform=lambda v, wt: v * 2)
        var2: bool = ecological.Variable("404", default=False)

    assert Configuration.var1a == 42
    assert Configuration.var1b == "4242"
    assert Configuration.var2 is False


def test_prefix(monkeypatch, base_class):
    monkeypatch.setenv("PREFIX_INTEGER", "42")
    monkeypatch.setenv("PREFIX_BOOLEAN", "False")
    monkeypatch.setenv("PREFIX_NOT_DEFAULT", "Not Default")

    class Configuration(base_class, prefix="prefix"):
        integer: int
        boolean: bool
        default: str = "Default"
        not_default: typing.AnyStr

    assert Configuration.integer == 42
    assert Configuration.boolean is False
    assert Configuration.default == "Default"
    assert Configuration.not_default == "Not Default"


def test_invalid_value_regular_type(monkeypatch, base_class):
    monkeypatch.setenv("PARAM_REGULAR_TYPE", "not an integer")

    with pytest.raises(ValueError):

        class Configuration(base_class):
            param_regular_type: int


def test_invalid_value_parsed_type(monkeypatch, base_class):
    monkeypatch.setenv("PARAM_PARSED_TYPE", "not a list")

    with pytest.raises(ValueError):

        class Configuration(base_class):
            param_parsed_type: list = ["param_1", "param_2"]


def test_no_default(base_class):
    with pytest.raises(AttributeError):

        class Configuration(base_class):
            no_default: int
            bool_var: bool = False


def test_simple_newtype(monkeypatch, base_class):
    monkeypatch.setenv("INTEGER", "2")

    Integer = typing.NewType("Integer", int)

    class Configuration(base_class):
        integer: Integer

    assert Configuration.integer == 2


def test_nested_newtype(monkeypatch, base_class):
    monkeypatch.setenv("ID", "2")

    Integer = typing.NewType("Integer", int)
    Id = typing.NewType("Id", Integer)

    class Configuration(base_class):
        id: Id

    assert Configuration.id == 2


def test_parametric_newtype(monkeypatch, base_class):
    monkeypatch.setenv("INTEGERS", "[1, 2, 3]")

    ListOfIntegers = typing.NewType("ListOfIntegers", typing.List[int])

    class Configuration(base_class):
        integers: ListOfIntegers

    assert Configuration.integers == [1, 2, 3]


def test_parametric_newtype_with_newtype_parameter(monkeypatch, base_class):
    monkeypatch.setenv("MEMBER_IDS", "[1, 2, 3]")

    Integer = typing.NewType("Integer", int)
    Id = typing.NewType("Id", Integer)

    ListOfIds = typing.NewType("ListOfIds", typing.List[Id])

    MemberIds = typing.NewType("MemberIds", ListOfIds)

    class Configuration(base_class):
        member_ids: MemberIds

    assert Configuration.member_ids == [1, 2, 3]


def test_autoload_values_on_object_init(monkeypatch):
    class Configuration(ecological.Config, autoload=ecological.Autoload.OBJECT):
        a: str
        b: int = 2

    monkeypatch.setenv("A", "a")
    monkeypatch.setenv("B", "3")
    config = Configuration()

    assert config.a == "a"
    assert config.b == 3


def test_load_values_explictly(monkeypatch):
    class Configuration(ecological.Config, autoload=ecological.Autoload.NEVER):
        a: str
        b: bool = False

    monkeypatch.setenv("A", "a")
    monkeypatch.setenv("B", "True")
    Configuration.load()

    assert Configuration.a == "a"
    assert Configuration.b is True


def test_deprecation_warning_is_emitted_on_autoconfig():
    with pytest.warns(DeprecationWarning):

        class Configuration(ecological.AutoConfig):
            pass


def test_config_autoload_is_ignored_on_autoconfig():
    with pytest.raises(AttributeError):

        class Configuration(ecological.AutoConfig, autoload=ecological.Autoload.NEVER):
            my_var1: str


def test_variable_is_loaded_from_source(monkeypatch, base_class):
    monkeypatch.setitem(os.environb, b"A_BYTES", b"a-bytes-value")

    class Configuration(base_class):
        a_bytes: bytes = ecological.Variable(b"A_BYTES", source=os.environb)

    assert Configuration.a_bytes == b"a-bytes-value"


def test_global_transform_option_is_used_as_default(monkeypatch):
    monkeypatch.setenv("IMPLICIT", "a")
    monkeypatch.setenv("VAR_WITH_TRANSFORM", "b")
    monkeypatch.setenv("VAR_WITHOUT_TRANSFORM", "c")

    class Configuration(ecological.Config, transform=lambda *args: "GLOBAL_TRANSFORM"):
        implicit: str
        var_without_transform = ecological.Variable("VAR_WITHOUT_TRANSFORM")
        var_with_transform: int = ecological.Variable(
            "VAR_WITH_TRANSFORM", transform=lambda *args: "VAR_TRANSFORM"
        )

    assert Configuration.implicit == "GLOBAL_TRANSFORM"
    assert Configuration.var_with_transform == "VAR_TRANSFORM"
    assert Configuration.var_without_transform == "GLOBAL_TRANSFORM"


def test_global_source_option_is_used_as_default(monkeypatch):
    my_dict = {"IMPLICIT": "a", "VAR_WITHOUT_SOURCE": "b"}
    monkeypatch.setenv("VAR_WITH_SOURCE", "c")

    class Configuration(ecological.Config, source=my_dict):
        implicit: str
        var_without_source = ecological.Variable("VAR_WITHOUT_SOURCE")
        var_with_source = ecological.Variable("VAR_WITH_SOURCE", source=os.environ)

    assert Configuration.implicit == "a"
    assert Configuration.var_without_source == "b"
    assert Configuration.var_with_source == "c"


def test_global_wanted_type_option_is_used_as_default(monkeypatch):
    monkeypatch.setenv("IMPLICIT_1", "1")
    monkeypatch.setenv("IMPLICIT_WITH_TYPE_2", "2")

    class Configuration(ecological.Config, wanted_type=int):
        implicit_1 = 99
        implicit_with_type_2: str

    assert Configuration.implicit_1 == 1
    assert Configuration.implicit_with_type_2 == "2"


def test_variable_name_is_calculation_is_used_as_default(monkeypatch):
    monkeypatch.setenv("IMPLICIT_THIS_IS_CRAZY", "1")
    monkeypatch.setenv("MY_ARBITRARY_NAME", "2")

    def my_variable_name(attr_name, prefix=None):
        return (attr_name + "_THIS_IS_CRAZY").upper()

    class Configuration(ecological.Config, variable_name=my_variable_name):
        implicit: str
        var_with_name = ecological.Variable("MY_ARBITRARY_NAME")

    assert Configuration.implicit == "1"
    assert Configuration.var_with_name == "2"
