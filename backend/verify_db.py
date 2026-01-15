#!/usr/bin/env python
"""Verify PostgreSQL database setup"""

from sqlalchemy import create_engine, text, inspect

# Connect to zcgl_db
engine = create_engine("postgresql+psycopg://postgres:asdf@localhost:5432/zcgl_db")

try:
    # Create inspector
    inspector = inspect(engine)

    # Get all table names
    tables = inspector.get_table_names()

    print("=" * 60)
    print("PostgreSQL Database Verification")
    print("=" * 60)
    print(f"Database: zcgl_db")
    print(f"Total tables: {len(tables)}")
    print("\nTables created:")
    for i, table in enumerate(tables, 1):
        print(f"  {i}. {table}")

    # Check for JSONB columns (PostgreSQL specific feature)
    print("\n" + "=" * 60)
    print("Checking for JSONB columns (PostgreSQL feature):")
    print("=" * 60)

    jsonb_columns = []
    for table in tables:
        columns = inspector.get_columns(table)
        for column in columns:
            if 'json' in str(column['type']).lower():
                jsonb_columns.append(f"  {table}.{column['name']} -> {column['type']}")

    if jsonb_columns:
        print("\nJSONB columns found:")
        for col in jsonb_columns:
            print(col)
    else:
        print("\nNo JSON columns detected (using generic JSON type)")

    print("\n" + "=" * 60)
    print("Verification complete!")
    print("=" * 60)

except Exception as e:
    print(f"Error: {e}")
    raise
finally:
    engine.dispose()
