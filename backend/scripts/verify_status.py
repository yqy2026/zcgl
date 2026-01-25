import sys
import os

# Setup path to import src
# script is in backend/scripts/
script_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(script_dir) # backend/
sys.path.append(backend_dir)

# Locate database
db_path = os.path.join(backend_dir, "data", "land_property.db")
if not os.path.exists(db_path):
    print(f"DB not found at {db_path}, checking root...")
    db_path = os.path.join(backend_dir, "land_property.db")

print(f"Target DB Path: {db_path}")

# Construct SQLAlchemy URL for SQLite
# On Windows, abspath starts with drive letter (e.g., D:\...)
# SQLite URL for absolute path on Windows: sqlite:///D:\path\to\file
db_url = f"sqlite:///{db_path}"

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
            
            print("\nDistinct Contract Statuses:")
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
