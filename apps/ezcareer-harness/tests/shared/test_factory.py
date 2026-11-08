import pytest

from src.shared.factory import Factory


def test_create_builds_an_item_once_and_returns_the_same_one_after():
    built: list[str] = []

    def build() -> object:
        built.append("x")
        return object()

    factory = Factory[object]({"x": build})

    assert factory.create("x") is factory.create("x")
    assert built == ["x"]


def test_each_name_gets_its_own_item():
    factory = Factory[list]({"a": list, "b": list})

    assert factory.create("a") is not factory.create("b")


def test_an_unknown_name_is_refused_with_the_known_ones():
    factory = Factory[list]({"a": list})

    with pytest.raises(ValueError, match="'linkedin'.*\\['a'\\]"):
        factory.create("linkedin")
