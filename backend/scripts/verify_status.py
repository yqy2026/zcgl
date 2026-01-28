import sys
import os

# Setup path to import src
# script is in backend/scripts/
script_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(script_dir)  # backend/
sys.path.append(backend_dir)

db_url = os.getenv("DATABASE_URL") or os.getenv("TEST_DATABASE_URL")
if not db_url:
    print("DATABASE_URL is required for this script")
    sys.exit(1)

if db_url.startswith("sqlite"):
    print("SQLite 已移除，请使用 PostgreSQL 数据库")
    sys.exit(1)

# Set Env Vars BEFORE importing src.database
os.environ["SECRET_KEY"] = "temporary_secret_key_for_script_execution_12345"
os.environ["DATABASE_URL"] = db_url
os.environ["ENVIRONMENT"] = "development"

try:
    from src.database import get_session_factory
    from src.models.rent_contract import RentContract
    from sqlalchemy import select

    def main():
        print(f"Connecting to {db_url}...")
        try:
            SessionLocal = get_session_factory()
            db = SessionLocal()

            print("Querying distinct contract_status...")
            stmt = select(RentContract.contract_status).distinct()
            results = db.execute(stmt).scalars().all()

            print("
Distinct Contract Statuses:")
            if not results:
                print("(No statuses found)")
            for status in results:
                print(f"- '{status}'")

            db.close()

        except Exception as e:
            print(f"Error: {e}")
            import traceback

            traceback.print_exc()

    if __name__ == "__main__":
        main()

except Exception as e:
    print(f"Import/Setup Error: {e}")
    import traceback

    traceback.print_exc()
