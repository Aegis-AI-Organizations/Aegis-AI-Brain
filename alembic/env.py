from logging.config import fileConfig
import os

from alembic import context
from sqlalchemy import URL, engine_from_config, pool

from models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

password = os.getenv("POSTGRES_PASSWORD")
if not password:
    raise EnvironmentError("POSTGRES_PASSWORD must be set to run database migrations.")

db_host = os.getenv("POSTGRES_HOST")
db_port = os.getenv("POSTGRES_PORT")
if not db_host:
    db_host_env = os.getenv("DB_HOST", "localhost:5432")
    db_host, separator, configured_port = db_host_env.partition(":")
    if separator and not db_port:
        db_port = configured_port

database_url = URL.create(
    drivername="postgresql+psycopg",
    username=os.getenv("POSTGRES_USER", "aegis_admin"),
    password=password,
    host=db_host,
    port=int(db_port or "5432"),
    database=os.getenv("POSTGRES_DB", "aegis_db"),
)
config.set_main_option("sqlalchemy.url", database_url.render_as_string(hide_password=False))
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
