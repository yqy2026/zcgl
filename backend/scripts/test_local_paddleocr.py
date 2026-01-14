#!/usr/bin/env python3
"""
Local PaddleOCR Test Script
Compare with Nvidia Cloud OCR results

Usage:
    python scripts/test_local_paddleocr.py path/to/your.pdf
"""

import os
import sys

# Add backend/src to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(backend_dir, "src"))

# Load .env file
from dotenv import load_dotenv

env_path = os.path.join(backend_dir, ".env")
if os.path.exists(env_path):
    load_dotenv(env_path)
    print(f"[OK] Loaded .env from: {env_path}")


def test_local_paddleocr(pdf_path: str) -> None:
    """Test local PaddleOCR with a PDF file."""

    # Check file exists
    if not os.path.exists(pdf_path):
        print(f"[ERROR] File not found: {pdf_path}")
        return

    print(f"[FILE] Test file: {pdf_path}")
    print(f"   File size: {os.path.getsize(pdf_path) / 1024:.1f} KB")

    # Import service
    try:
        from services.document.paddleocr_service import (
            PaddleOCRService,
            get_paddleocr_service,
        )
    except ImportError as e:
        print(f"[ERROR] Import error: {e}")
        print("   Please run this script from the backend directory")
        return

    # Initialize service
    print("\n[INIT] Initializing Local PaddleOCR service...")
    service = get_paddleocr_service()

    if not service.is_available:
        print("[ERROR] Service not available")
        print(
            "   PaddleOCR may not be installed. Run: pip install paddleocr paddlex[ocr]"
        )
        return

    print("[OK] Service initialized successfully")

    # Process PDF
    print("\n[RUN] Processing PDF with local PaddleOCR...")
    print("   (This may take 1-3 minutes for large files)")

    try:
        # Use to_markdown method for full extraction
        result = service.to_markdown(pdf_path)

        print("\n" + "=" * 60)
        print("[RESULT] Processing Result")
        print("=" * 60)

        if result.get("success"):
            print("[OK] Status: Success")

            # Show extracted text preview
            markdown_content = result.get("markdown", "")
            if markdown_content:
                preview = (
                    markdown_content[:1000] + "..."
                    if len(markdown_content) > 1000
                    else markdown_content
                )
                print("\n[TEXT] Extracted Markdown preview:")
                print("-" * 40)
                print(preview)
                print("-" * 40)
                print(f"\n[STATS] Total characters: {len(markdown_content)}")
            else:
                print("[WARN] No text extracted")

        else:
            print("[FAIL] Status: Failed")
            print(f"   Error: {result.get('error', 'Unknown error')}")

    except Exception as e:
        print(f"\n[ERROR] Processing exception: {e}")
        import traceback

        traceback.print_exc()


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/test_local_paddleocr.py <pdf_path>")
        print("\nExample:")
        print(
            "  python scripts/test_local_paddleocr.py ../tools/pdf-samples/contract.pdf"
        )
        sys.exit(1)

    pdf_path = sys.argv[1]
    test_local_paddleocr(pdf_path)


if __name__ == "__main__":
    main()
