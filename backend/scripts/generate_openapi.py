import json
import os
import sys
from pathlib import Path

# Add project root to python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Set environment to testing to avoid startup checks/db connections
os.environ["ENVIRONMENT"] = "testing"
os.environ["SECRET_KEY"] = (
    "mock-secret-key-for-openapi-generation-only-do-not-use-in-production"
)
os.environ["DATA_ENCRYPTION_KEY"] = (
    "mock-data-encryption-key-for-openapi-generation-only"
)

try:
    from fastapi.openapi.utils import get_openapi

    from src.main import app
except ImportError as e:
    print(f"Error importing app: {e}")
    sys.exit(1)


def generate_openapi_spec():
    print("Generating OpenAPI schema...")

    # Generate schema
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        openapi_version=app.openapi_version,
        description=app.description,
        routes=app.routes,
    )

    # Save to root directory
    output_path = project_root / "openapi.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(openapi_schema, f, ensure_ascii=False, indent=2)

    print(f"✅ OpenAPI spec generated successfully at: {output_path}")


if __name__ == "__main__":
    generate_openapi_spec()
