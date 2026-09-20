"""Alembic environment.

Loads the database URL from app settings (DATABASE_URL env var) rather than
the alembic.ini file so ops don't need to duplicate config between the app
and the migration tool. Same reason target_metadata pulls from
app.database.Base — anything in the SQLAlchemy models is what alembic can
autogenerate against.
"""

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool

from alembic import context

# Make sure `import app.*` works when alembic runs from backend/.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings  # noqa: E402
from app.database import Base  # noqa: E402

# Import every model module so Base.metadata is fully populated. Missing an
# import here means autogenerate wouldn't see the model and would try to drop
# whatever it doesn't recognise. Keep this list exhaustive.
import app.models.teacher  # noqa: E402,F401
import app.models.duty  # noqa: E402,F401
import app.models.lesson  # noqa: E402,F401
import app.models.substitution  # noqa: E402,F401
import app.models.alert  # noqa: E402,F401
import app.models.attendance  # noqa: E402,F401

config = context.config

# Route Alembic through the same DATABASE_URL the app uses. Overriding here
# means the URL literal never has to appear in alembic.ini.
config.set_main_option("sqlalchemy.url", settings.database_url_fixed)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode — emits SQL rather than executing it."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live database connection."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # Include COMMENT ON, CHECK, etc. differences.
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
