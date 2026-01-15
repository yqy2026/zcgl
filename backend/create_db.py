#!/usr/bin/env python
"""Create PostgreSQL databases for the project"""

from sqlalchemy import create_engine, text

# Connect to PostgreSQL default database with autocommit
engine = create_engine(
    "postgresql+psycopg://postgres:asdf@localhost:5432/postgres",
    isolation_level="AUTOCOMMIT"
)

try:
    with engine.connect() as conn:
        # Create databases (DROP DATABASE cannot run in a transaction)
        try:
            conn.execute(text("DROP DATABASE IF EXISTS zcgl_db"))
        except Exception:
            pass  # Database might not exist

        conn.execute(text("CREATE DATABASE zcgl_db"))
        print("Created database: zcgl_db")

        try:
            conn.execute(text("DROP DATABASE IF EXISTS zcgl_test"))
        except Exception:
            pass  # Database might not exist

        conn.execute(text("CREATE DATABASE zcgl_test"))
        print("Created database: zcgl_test")

        print("\nAll databases created successfully!")

except Exception as e:
    print(f"Error creating database: {e}")
    raise
finally:
    engine.dispose()
