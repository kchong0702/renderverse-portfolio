# Coding guidelines

These rules apply to all code in ops-api.

## Migrations

- Generate every migration with `alembic revision --autogenerate`. Keep the file as Alembic writes it, its comments included.
- `env.py` and `script.py.mako` come from `alembic init -t async`. Leave `script.py.mako` as Alembic's template. Change `env.py` only where the app needs it, such as its database URL, engine, metadata, autogenerate plugins and renderers.
- When autogenerate misses something, fix the model so that it generates it. Don't edit the migration.
- If a migration needs a line autogenerate can't write, list each such line in the PR and say why. For example, a foreign key between two tables that reference each other (`use_alter=True`) must be added with `op.create_foreign_key` after both tables exist.
