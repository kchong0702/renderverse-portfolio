import pytest
from pydantic import BaseModel

from src.shared.adapters import Adapter, AdapterFactory, AdapterUnavailable


class _Shared(BaseModel):
    query: str
    """What to look for"""

    country: str | None = None
    """Where to look"""


class _Other(BaseModel):
    query: str
    """What to look for"""

    limit: int = 10
    """How many to return"""


def _adapter(name: str, query: type[BaseModel], seen: list, down: bool = False):
    async def run(given: BaseModel) -> str:
        seen.append(given)
        if down:
            raise AdapterUnavailable(f"{name} is down")
        return f"{name} ran"

    return Adapter[str](name=name, query=query, usage=f"{name} costs one.", run=run)


async def test_enabled_adapters_share_fields_named_alike_and_get_only_their_own():
    seen_a: list = []
    seen_b: list = []
    factory = AdapterFactory[str](
        _adapter("a", _Shared, seen_a), _adapter("b", _Other, seen_b)
    )
    enabled = factory.enable(["a", "b"])

    results, unavailable = await enabled.run(
        {"query": "dev", "country": "GB", "limit": 5}
    )

    assert sorted(enabled.arguments("Args").model_fields) == [
        "country",
        "limit",
        "query",
    ]
    assert seen_a == [_Shared(query="dev", country="GB")]
    assert seen_b == [_Other(query="dev", limit=5)]
    assert (results, unavailable) == (["a ran", "b ran"], [])
    assert enabled.usage == "a costs one. b costs one."


def test_arguments_take_extra_fields_such_as_an_injected_runtime():
    enabled = AdapterFactory[str](_adapter("a", _Shared, [])).enable(["a"])

    arguments = enabled.arguments("Args", runtime=(object, ...))

    assert "runtime" in arguments.model_fields


def test_adapters_that_disagree_on_a_field_are_refused():
    class _Clash(BaseModel):
        query: int

    enabled = AdapterFactory[str](
        _adapter("a", _Shared, []), _adapter("clash", _Clash, [])
    ).enable(["a", "clash"])

    with pytest.raises(ValueError, match="'query'"):
        enabled.arguments("Args")


def test_an_unknown_adapter_name_is_refused():
    factory = AdapterFactory[str](_adapter("a", _Shared, []))

    with pytest.raises(ValueError, match="linkedin"):
        factory.enable(["linkedin"])


async def test_an_unavailable_adapter_leaves_the_others_results():
    enabled = AdapterFactory[str](
        _adapter("a", _Shared, []), _adapter("b", _Other, [], down=True)
    ).enable(["a", "b"])

    assert await enabled.run({"query": "dev"}) == (["a ran"], ["b is down"])
