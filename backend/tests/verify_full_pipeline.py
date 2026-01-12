import asyncio
import sys
import os
import json
from pathlib import Path

# Setup Path
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../src"))
sys.path.append(src_path)

import logging
logging.basicConfig(level=logging.INFO)

# Load env
try:
    from dotenv import load_dotenv
    env_path = os.path.join(os.path.dirname(__file__), "../.env")
    load_dotenv(env_path)
except ImportError:
    pass

from services.document.paddleocr_service import get_paddleocr_service
from services.document.llm_contract_extractor import LLMContractExtractor

async def verify_full_pipeline(pdf_path_str: str):
    pdf_path = Path(pdf_path_str)
    if not pdf_path.exists():
        print(f"ERROR: File not found at {pdf_path}")
        return

    print(f"=== Starting Full Pipeline Verification ===")
    print(f"Target File: {pdf_path.name}")
    print(f"File Size: {pdf_path.stat().st_size / 1024 / 1024:.2f} MB")
    
    # 1. OCR Stage
    print("\n--- Stage 1: PaddleOCR (Layout Analysis) ---")
    print("Initializing PaddleOCR (this takes time to load models)...")
    paddle_service = get_paddleocr_service()
    
    # Check if we have GPU
    print(f"PaddleOCR GPU Enabled: {paddle_service.use_gpu}")
    
    print("converting to Markdown...")
    try:
        # Run synchronous code in thread pool if needed, but for script is fine
        ocr_result = paddle_service.to_markdown(str(pdf_path))
        
        if not ocr_result['success']:
            print(f"[ERROR] OCR Stage Failed: {ocr_result.get('error')}")
            return
            
        markdown_content = ocr_result['markdown']
        print(f"[SUCCESS] OCR Success! Generated {len(markdown_content)} characters of Markdown.")
        # Preview
        print(f"Preview:\n{markdown_content[:300]}...\n")
        
    except Exception as e:
        print(f"[ERROR] OCR Exception: {e}")
        import traceback
        traceback.print_exc()
        return

    # 2. LLM Extraction Stage
    print("\n--- Stage 2: LLM Extraction ---")
    print(f"Model: {os.getenv('LLM_MODEL', 'unknown')}")
    extractor = LLMContractExtractor()
    
    try:
        llm_result = await extractor.extract(markdown_content)
        
        if llm_result['success']:
            print("[SUCCESS] LLM Extraction Success!")
            print("\n>>> Extracted Data <<<")
            print(json.dumps(llm_result['extracted_fields'], indent=2, ensure_ascii=False))
            print("------------------------")
            print(f"Confidence: {llm_result.get('confidence')}")
        else:
            print(f"[ERROR] LLM Extraction Failed: {llm_result.get('error')}")
            
    except Exception as e:
        print(f"[ERROR] LLM Exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python verify_full_pipeline.py <path_to_pdf>")
        # Default for convenience in dev environment
        default_file = r"d:/ccode/zcgl/tools/pdf-samples/【包装合字（2025）第022号】租赁合同-番禺区洛浦南浦环岛西路29号1号商业楼14号铺-王军20250401-20280331.pdf"
        if os.path.exists(default_file):
            asyncio.run(verify_full_pipeline(default_file))
        else:
            print(f"Default file not found: {default_file}")
    else:
        asyncio.run(verify_full_pipeline(sys.argv[1]))
