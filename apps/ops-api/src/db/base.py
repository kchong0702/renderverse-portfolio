from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, ClassVar, override

from pydantic import JsonValue, TypeAdapter
from sqlalchemy import JSON, Dialect, MetaData, String, TypeDecorator
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase

JsonType = JSON().with_variant(JSONB(), "postgresql")

_NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


def utcnow() -> datetime:
    return datetime.now(UTC)


class EnumString[E: StrEnum](TypeDecorator[E]):
    impl = String
    """A plain string column, so a new member needs no migration"""

    cache_ok = True
    """Safe to cache: the enum is the only state and it never changes"""

    def __init__(self, enum: type[E]):
        """Store the enum's members by value, checked against the enum on every
        write and read"""
        super().__init__()
        self._enum = enum

    @override
    def process_bind_param(self, value: E | None, dialect: Dialect) -> str | None:
        """The member's value"""
        return None if value is None else self._enum(value).value

    @override
    def process_result_value(self, value: str | None, dialect: Dialect) -> E | None:
        """The member the stored value names"""
        return None if value is None else self._enum(value)


class PydanticJson[T](TypeDecorator[T]):
    impl = JsonType
    """JSONB on Postgres, JSON elsewhere"""

    cache_ok = True
    """Safe to cache: the adapter is the only state and it never changes"""

    def __init__(self, adapter: TypeAdapter[T]):
        """Store values of the adapter's type as their JSON, checked again on every read"""
        super().__init__()
        self._adapter = adapter

    @override
    def process_bind_param(self, value: T | None, dialect: Dialect) -> JsonValue:
        """The value as JSON-ready data"""
        return None if value is None else self._adapter.dump_python(value, mode="json")

    @override
    def process_result_value(self, value: JsonValue, dialect: Dialect) -> T | None:
        """The stored JSON parsed back into the type"""
        return None if value is None else self._adapter.validate_python(value)


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=_NAMING_CONVENTION)
    type_annotation_map: ClassVar = {dict[str, Any]: JsonType, list[Any]: JsonType}


__all__ = ["Base", "EnumString", "JsonType", "PydanticJson", "utcnow"]
