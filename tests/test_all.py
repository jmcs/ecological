#!/usr/bin/python3

import typing

import pytest

import ecological


def test_regular_types(monkeypatch):
    monkeypatch.setenv("INTEGER", "42")
    monkeypatch.setenv("BOOLEAN", "False")
    monkeypatch.setenv("ANY_STR", "AnyStr Example")
    monkeypatch.setenv("TEXT", "Text Example")
    monkeypatch.setenv("DICT", "{'key': 'value'}")
    monkeypatch.setenv("LIST", "[1, 2, 3]")

    class Configuration(ecological.AutoConfig):
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
    assert Configuration.dict == {'key': 'value'}
    assert Configuration.list == [1, 2, 3]


def test_nested(monkeypatch):
    monkeypatch.setenv("INTEGER", "42")
    monkeypatch.setenv("NESTED_BOOLEAN", "False")

    class Configuration(ecological.AutoConfig):
        integer: int

        class Nested(ecological.AutoConfig, prefix='nested'):
            boolean: bool

    assert Configuration.integer == 42
    assert Configuration.Nested.boolean is False


def test_explicit_variable(monkeypatch):
    monkeypatch.setenv("TEST_Integer", "42")

    class Configuration(ecological.AutoConfig, prefix="this_is_going_to_be_ignored"):
        var1a = ecological.Variable("TEST_Integer", transform=lambda v, wt: int(v))
        var1b: str = ecological.Variable("TEST_Integer", transform=lambda v, wt: v * 2)
        var2: bool = ecological.Variable("404", default=False)

    assert Configuration.var1a == 42
    assert Configuration.var1b == "4242"
    assert Configuration.var2 is False


def test_prefix(monkeypatch):
    monkeypatch.setenv("PREFIX_INTEGER", "42")
    monkeypatch.setenv("PREFIX_BOOLEAN", "False")
    monkeypatch.setenv("PREFIX_NOT_DEFAULT", "Not Default")

    class Configuration(ecological.AutoConfig, prefix="prefix"):
        integer: int
        boolean: bool
        default: str = "Default"
        not_default: typing.AnyStr

    assert Configuration.integer == 42
    assert Configuration.boolean is False
    assert Configuration.default == "Default"
    assert Configuration.not_default == "Not Default"


def test_invalid_value(monkeypatch):
    monkeypatch.setenv("INVALID", "Invalid integer")

    with pytest.raises(ValueError):
        class Configuration(ecological.AutoConfig):
            invalid: int


def test_no_default():
    with pytest.raises(AttributeError):
        class Configuration(ecological.AutoConfig):
            no_default: int
            bool_var: bool = False
