import os
import sys
from logging.config import fileConfig

# Load environment variables from .env file
from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool

from alembic import context

load_dotenv()

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# 错误处理包装 - 捕获模型导入错误
try:
    from src.database import Base

    logger = None

    # Import all models so Alembic can detect them
    # noqa: F401 - Models are imported for side effects (Alembic metadata)
    from src.models import (
        asset,
        auth,
        collection,
        contact,
        dynamic_permission,
        enum_field,
        notification,
        operation_log,
        organization,
        pdf_import_session,
        rbac,
        rent_contract,
        task,
    )

except ImportError as e:
    print(f"\n{'=' * 60}")
    print("CRITICAL: 无法导入模型进行数据库迁移")
    print(f"错误: {e}")
    print("\n可能的解决方案:")
    print("1. 运行: uv pip install -e .")
    print("2. 检查src/models/目录是否存在所有模型文件")
    print("3. 检查数据库依赖是否已安装 (psycopg2等)")
    print("4. 查看 docs/POSTGRESQL_MIGRATION.md 获取帮助")
    print(f"{'=' * 60}\n")
    sys.exit(1)

except Exception as e:
    print(f"\n{'=' * 60}")
    print(f"Alembic初始化失败: {e}")
    print(f"{'=' * 60}\n")
    sys.exit(1)

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Get DATABASE_URL from environment variable and override alembic.ini
database_url = os.getenv("DATABASE_URL")
if not database_url:
    raise ValueError(
        "DATABASE_URL environment variable is not set!\n"
        "Please configure DATABASE_URL in your .env file.\n"
        "Example: DATABASE_URL=postgresql+psycopg://user:password@host:port/database"
    )

# Override sqlalchemy.url from alembic.ini with environment variable
config.set_main_option("sqlalchemy.url", database_url)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
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
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
