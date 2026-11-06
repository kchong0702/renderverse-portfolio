from src.app import models  # noqa: F401  (registers the tables)
from src.core.db.base import Base
from src.core.db.mixins import AuditMixin

# users itself, and sign-in attempts, which count emails that may have no user
_NOT_OWNED = {"users", "auth_sign_in_attempts"}


def test_every_table_belongs_to_a_user():
    missing = [
        name
        for name, table in Base.metadata.tables.items()
        if name not in _NOT_OWNED and "user_id" not in table.columns
    ]

    assert missing == [], f"tables without user_id: {missing}"


def test_every_feature_table_is_audited():
    missing = [
        mapper.class_.__tablename__
        for mapper in Base.registry.mappers
        if mapper.class_.__module__.startswith("src.features.")
        and not issubclass(mapper.class_, AuditMixin)
    ]

    assert missing == [], f"feature tables without AuditMixin: {missing}"
