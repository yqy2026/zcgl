import asyncio
import json
import os
import sys

# Setup Path
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../src"))
sys.path.append(src_path)

# Load .env variables manually because we are running a script directly
# (Usually FastAPI/Uvicorn loads them, or python-dotenv)
# We will check if OS env vars are set, if not try to load from backend/.env
try:
    from dotenv import load_dotenv
    env_path = os.path.join(os.path.dirname(__file__), "../.env")
    print(f"Loading env from {env_path}")
    load_dotenv(env_path)
except ImportError:
    print("python-dotenv not installed, assuming env vars are set by shell")

from services.document.llm_contract_extractor import LLMContractExtractor


async def verify_real_connection():
    print("Initializing LLMContractExtractor with REAL configuration...")

    api_key = os.getenv("LLM_API_KEY")
    base_url = os.getenv("LLM_BASE_URL")
    model = os.getenv("LLM_MODEL")

    print("Configuration detected:")
    print(f"  API Key: {'*' * 8 if api_key else 'MISSING'}")
    print(f"  Base URL: {base_url}")
    print(f"  Model: {model}")

    if not api_key:
        print("ERROR: LLM_API_KEY is not set.")
        return

    extractor = LLMContractExtractor()

    # Sample tiny markdown contract
    sample_text = """
    # 房屋租赁合同

    合同编号：HT-TEST-REAL-001

    出租方（甲方）：测试真实地产有限公司
    联系电话：010-88888888

    承租方（乙方）：测试科技公司
    联系电话：13900000000

    一、租赁标的
    房屋坐落：北京市朝阳区科技园A栋101
    建筑面积：200平方米

    二、租赁期限
    租赁期为2年，自2024年3月1日起至2026年3月1日止。

    三、租金及支付
    每月租金为人民币 15000 元。
    押金为人民币 30000 元。
    """

    print("\nSending request to LLM... (This may take a few seconds)")
    try:
        result = await extractor.extract(sample_text)

        if result['success']:
            print("\n✅ Extraction SUCCESS!")
            print("Extracted Data:")
            print(json.dumps(result['extracted_fields'], indent=2, ensure_ascii=False))
            print(f"\nConfidence: {result.get('confidence')}")
        else:
            print("\n❌ Extraction FAILED.")
            print(f"Error: {result.get('error')}")

    except Exception as e:
        print(f"\n❌ Exception during execution: {e}")

if __name__ == "__main__":
    asyncio.run(verify_real_connection())
