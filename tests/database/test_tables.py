"""The SQLAlchemy mappings must describe exactly the schema the migrations build.

The migrations are the source of truth; this fails when a migration changes the schema and
tables.py isn't updated to match, or the other way round.
"""

from sqlalchemy import Engine, inspect

from fantasy_bot.database import tables as t


def test_mapped_tables_are_exactly_the_migrated_tables(engine: Engine) -> None:
    assert set(t.Base.metadata.tables) == set(inspect(engine).get_table_names())


def test_every_mapped_column_matches_name_nullability_and_primary_key(engine: Engine) -> None:
    database = inspect(engine)
    for name, table in t.Base.metadata.tables.items():
        migrated = {c["name"]: c for c in database.get_columns(name)}
        primary_key = set(database.get_pk_constraint(name)["constrained_columns"])
        assert [(c.name, c.nullable, c.primary_key) for c in table.columns] == [
            (c, migrated[c]["nullable"] and c not in primary_key, c in primary_key)
            for c in migrated
        ], name


def test_every_mapped_foreign_key_matches_the_migrated_one(engine: Engine) -> None:
    database = inspect(engine)
    for name, table in t.Base.metadata.tables.items():
        mapped = {
            (tuple(fk.column_keys), fk.referred_table.name) for fk in table.foreign_key_constraints
        }
        migrated = {
            (tuple(fk["constrained_columns"]), fk["referred_table"])
            for fk in database.get_foreign_keys(name)
        }
        assert mapped == migrated, name


def test_every_mapped_view_has_the_migrated_columns(engine: Engine) -> None:
    database = inspect(engine)
    assert set(t.views.tables) == set(database.get_view_names())
    for name, view in t.views.tables.items():
        assert [c.name for c in view.columns] == [c["name"] for c in database.get_columns(name)], (
            name
        )
