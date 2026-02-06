
import sys
import os
from pathlib import Path

# 1. Set environment variables BEFORE importing any backend modules
os.environ["SECRET_KEY"] = "test_secret_key_for_verification_only_123456789"
os.environ["DATA_ENCRYPTION_KEY"] = "test_encryption_key_1234567890123456789012="  # 32 chars + padding if needed

# Add backend to path
backend_path = Path("d:/work/zcgl/backend")
sys.path.append(str(backend_path))

def check_rent_contract_import():
    print("Checking rent_contract import...", end=" ")
    try:
        # This will trigger the config loading
        from src.models import rent_contract
        print("✅ Success")
        return True
    except ImportError as e:
        print(f"❌ Failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def check_security_service_stub():
    print("Checking SecurityService stub...", end=" ")
    try:
        from src.services.core.security_service import SecurityService
        svc = SecurityService()
        try:
            svc.hash_password("test")
            print("❌ Failed: hash_password should raise error but didn't")
            return False
        except Exception as e:
            if "deprecated and unsafe" in str(e):
                print("✅ Success (Raised expected error)")
                return True
            else:
                print(f"❌ Failed: Raised unexpected error: {e}")
                return False
    except Exception as e:
        print(f"❌ Error importing/instantiating: {e}")
        return False

def check_pdf_service_async():
    print("Checking PDFProcessingService async...", end=" ")
    try:
        from src.services.document.pdf_processing_service import PDFProcessingService
        import inspect
        
        src = inspect.getsource(PDFProcessingService.extract_text_from_pdf)
        
        # Check for anyio.to_thread.run_sync OR loop.run_in_executor
        if "anyio.to_thread.run_sync" in src or "run_in_executor" in src:
            print("✅ Success (Found async execution wrapper)")
            return True
        else:
            print("❌ Failed: Async execution wrapper not found in source code")
            print(f"Source snippet: {src[:200]}...")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("=== Verification Report ===")
    r1 = check_rent_contract_import()
    r2 = check_security_service_stub()
    r3 = check_pdf_service_async()
    
    if r1 and r2 and r3:
        print("\nAll critical fixes verified successfully.")
        sys.exit(0)
    else:
        print("\nSome verifications failed.")
        sys.exit(1)
