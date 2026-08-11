from alembic.autogenerate import compare_metadata
from alembic.runtime.migration import MigrationContext

from database.connection import Base, engine


def test_metadata_matches_latest_migration():
    with engine.connect() as connection:
        context = MigrationContext.configure(connection)
        diff = compare_metadata(context, Base.metadata)
    assert not diff, f"迁移与模型不一致: {diff}"
