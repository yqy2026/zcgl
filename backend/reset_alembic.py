#!/usr/bin/env python
"""Reset Alembic migration state"""

from sqlalchemy import create_engine, text

# Connect to zcgl_db
engine = create_engine(
    "postgresql+psycopg://postgres:asdf@localhost:5432/zcgl_db",
    isolation_level="AUTOCOMMIT"
)

try:
    with engine.connect() as conn:
        # Drop alembic_version table
        conn.execute(text("DROP TABLE IF EXISTS alembic_version"))
        print("Reset Alembic migration state")

except Exception as e:
    print(f"Error: {e}")
    raise
finally:
    engine.dispose()
