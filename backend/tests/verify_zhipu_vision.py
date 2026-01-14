"""
Verify Zhipu Vision Service Connection
验证智谱AI视觉服务连接

Tests the multimodal extraction with a real PDF contract.
使用真实PDF合同测试多模态提取功能。
"""
import asyncio
import json
import os
import sys
from pathlib import Path

# Setup Path
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../src"))
sys.path.insert(0, src_path)

# Load environment variables
try:
    from dotenv import load_dotenv
    env_path = os.path.join(os.path.dirname(__file__), "../.env")
    if os.path.exists(env_path):
        print(f"Loading env from {env_path}")
        load_dotenv(env_path)
    else:
        # Try config directory
        env_path = os.path.join(os.path.dirname(__file__), "../config/backend.env.secure")
        if os.path.exists(env_path):
            print(f"Loading env from {env_path}")
            load_dotenv(env_path)
except ImportError:
    print("python-dotenv not installed, assuming env vars are set by shell")


async def verify_vision_service():
    """Test the vision service configuration"""
    print("=" * 60)
    print("Zhipu Vision Service Verification")
    print("=" * 60)

    api_key = os.getenv("ZHIPU_API_KEY")
    model = os.getenv("ZHIPU_VISION_MODEL", "glm-4v-flash")

    print("\nConfiguration:")
    print(f"  API Key: {'*' * 8 + api_key[-4:] if api_key else '❌ MISSING'}")
    print(f"  Model: {model}")

    if not api_key:
        print("\n❌ ERROR: ZHIPU_API_KEY is not set.")
        print("Please set it in your environment or .env file:")
        print("  export ZHIPU_API_KEY=your_key_here")
        return False

    from services.core.zhipu_vision_service import get_zhipu_vision_service

    service = get_zhipu_vision_service()
    print(f"\n  Service Available: {'✅ Yes' if service.is_available else '❌ No'}")

    return service.is_available


async def test_pdf_extraction(pdf_path: str):
    """Test extraction with a real PDF file"""
    print("\n" + "=" * 60)
    print("PDF Contract Extraction Test")
    print("=" * 60)

    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        print(f"❌ PDF file not found: {pdf_path}")
        return

    print(f"\nPDF File: {pdf_path.name}")
    print(f"Size: {pdf_path.stat().st_size / 1024:.1f} KB")

    from services.document.llm_contract_extractor import LLMContractExtractor

    extractor = LLMContractExtractor()

    print("\n⏳ Starting vision extraction (this may take 30-60 seconds)...")

    try:
        result = await extractor.extract_from_pdf_vision(str(pdf_path))

        if result["success"]:
            print("\n✅ Extraction SUCCESS!")
            print(f"   Method: {result.get('extraction_method')}")
            print(f"   Pages Processed: {result.get('pages_processed')}")
            print(f"   Confidence: {result.get('confidence')}")

            print("\n📋 Extracted Fields:")
            print("-" * 40)
            fields = result.get("extracted_fields", {})
            for key, value in fields.items():
                if value is not None:
                    print(f"  {key}: {value}")

            print("\n📊 Token Usage:")
            usage = result.get("usage", {})
            print(f"  Prompt Tokens: {usage.get('prompt_tokens', 'N/A')}")
            print(f"  Completion Tokens: {usage.get('completion_tokens', 'N/A')}")
            print(f"  Total Tokens: {usage.get('total_tokens', 'N/A')}")

            # Save full result to file
            output_file = pdf_path.with_suffix(".extraction_result.json")
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"\n💾 Full result saved to: {output_file}")

        else:
            print("\n❌ Extraction FAILED")
            print(f"   Error: {result.get('error')}")
            print(f"   Method: {result.get('extraction_method')}")

    except Exception as e:
        print(f"\n❌ Exception during extraction: {e}")
        import traceback
        traceback.print_exc()


async def main():
    # Step 1: Verify configuration
    is_configured = await verify_vision_service()

    if not is_configured:
        print("\n⚠️  Please configure ZHIPU_API_KEY before running extraction test.")
        return

    # Step 2: Find and test with sample PDF
    sample_dir = Path(__file__).parent.parent.parent / "tools" / "pdf-samples"

    pdf_files = list(sample_dir.glob("*.pdf")) if sample_dir.exists() else []

    if not pdf_files:
        print(f"\n⚠️  No PDF files found in {sample_dir}")
        print("Please provide a sample PDF for testing.")
        return

    print(f"\nFound {len(pdf_files)} PDF file(s) in samples directory")

    # Test with first PDF
    await test_pdf_extraction(str(pdf_files[0]))


if __name__ == "__main__":
    asyncio.run(main())
