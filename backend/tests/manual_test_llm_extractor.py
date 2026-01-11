import asyncio
import sys
import os
from unittest.mock import MagicMock, AsyncMock

# Add 'src' to path so we can import directly from services
# d:/ccode/zcgl/backend/tests/manual_test_llm_extractor.py -> ../src
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../src"))
sys.path.append(src_path)

print(f"Added to path: {src_path}")

# Mock environment variables
os.environ["LLM_API_KEY"] = "test-key"

# Import directly from src... 
# Assuming backend/src is the root of the source code when running from backend/
from services.document.llm_contract_extractor import LLMContractExtractor
from services.core.llm_service import LLMResponse

async def test_extraction():
    print("Testing LLMContractExtractor...")
    
    # 1. Setup Extractor with Mocked LLM Service
    extractor = LLMContractExtractor()
    
    # Mock return data from "LLM"
    mock_json_content = """
    {
        "contract_number": "HT-2024-888",
        "sign_date": "2024-01-01",
        "landlord": {
            "name": "Guangzhou Property Co",
            "legal_rep": "Mr. Zhang",
            "phone": "020-12345678",
            "address": "Tianhe District"
        },
        "tenant": {
            "name": "Tech Startup Ltd",
            "id_number": "91440000XXX",
            "phone": "13800138000",
            "address": "Room 101"
        },
        "property": {
            "address": "Building A, Room 888",
            "area": 100.5,
            "usage": "Office"
        },
        "rent_info": {
            "monthly_rent": 5000.0,
            "deposit": 10000.0,
            "payment_cycle": "Month",
            "rent_free_period_days": 15
        },
        "terms": {
            "start_date": "2024-01-01",
            "end_date": "2025-01-01",
            "duration_years": 1
        }
    }
    """
    
    # Mock the chat_completion method
    extractor.llm_service.chat_completion = AsyncMock(return_value=LLMResponse(
        content=mock_json_content,
        raw_response={},
        usage={}
    ))
    
    # 2. Run Extraction on "Markdown"
    fake_markdown = "# Contract 2024..."
    result = await extractor.extract(fake_markdown)
    
    # 3. Verify Results
    print(f"Success: {result['success']}")
    print(f"Extraction Method: {result['extraction_method']}")
    
    fields = result['extracted_fields']
    print(f"Contract Number: {fields['contract_number']}")
    print(f"Monthly Rent: {fields['monthly_rent']}")
    
    assert fields['contract_number'] == "HT-2024-888"
    assert fields['monthly_rent'] == 5000.0
    assert fields['landlord_name'] == "Guangzhou Property Co"
    
    print("Verification Passed!")

if __name__ == "__main__":
    asyncio.run(test_extraction())
