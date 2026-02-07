import importlib
import inspect
import os
import sys
from pathlib import Path

os.environ["SECRET_KEY"] = "test_secret_key_for_verification_only_123456789"
os.environ.pop("DATA_ENCRYPTION_KEY", None)

backend_path = Path(__file__).resolve().parents[1] / "backend"
sys.path.append(str(backend_path))


def check_rent_contract_import() -> bool:
    print("Checking rent_contract import...", end=" ")
    try:
        from src.models import rent_contract  # noqa: F401

        print("[OK]")
        return True
    except Exception as error:
        print(f"[FAIL] {error}")
        return False


def check_security_service_removed() -> bool:
    print("Checking SecurityService removal...", end=" ")
    try:
        importlib.import_module("src.services.core.security_service")
    except ModuleNotFoundError:
        print("[OK] module removed")
        return True
    except Exception as error:
        print(f"[FAIL] unexpected error: {error}")
        return False
    else:
        print("[FAIL] module still importable")
        return False


def check_pdf_service_async() -> bool:
    print("Checking PDFProcessingService async...", end=" ")
    try:
        from src.services.document.pdf_processing_service import PDFProcessingService

        source = inspect.getsource(PDFProcessingService.extract_text_from_pdf)
        if "anyio.to_thread.run_sync" in source or "run_in_executor" in source:
            print("[OK]")
            return True
        print("[FAIL] async execution wrapper not found")
        return False
    except Exception as error:
        print(f"[FAIL] {error}")
        return False


if __name__ == "__main__":
    print("=== Verification Report ===")
    result_rent = check_rent_contract_import()
    result_security = check_security_service_removed()
    result_pdf = check_pdf_service_async()

    if result_rent and result_security and result_pdf:
        print("\nAll critical fixes verified successfully.")
        sys.exit(0)

    print("\nSome verifications failed.")
    sys.exit(1)
