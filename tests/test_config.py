#!/usr/bin/python3

import typing

import pytest

import ecological


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
