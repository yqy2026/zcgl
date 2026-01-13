#!/usr/bin/env python3
"""
Test DeepSeek OCR via SiliconFlow
测试硅基流动 DeepSeek-OCR 合同提取

Usage:
    cd backend
    python scripts/test_deepseek_ocr.py
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

# Load .env
load_dotenv()


async def test_extraction():
    """Test DeepSeek OCR extraction"""
    
    # Check configuration
    api_key = os.getenv("DEEPSEEK_API_KEY")
    base_url = os.getenv("DEEPSEEK_BASE_URL")
    model = os.getenv("DEEPSEEK_VISION_MODEL")
    
    print("=" * 60)
    print("DeepSeek OCR Test (SiliconFlow)")
    print("=" * 60)
    print(f"API Key: {'*' * 20}...{api_key[-8:] if api_key else 'NOT SET'}")
    print(f"Base URL: {base_url or 'NOT SET'}")
    print(f"Model: {model or 'NOT SET'}")
    print("=" * 60)
    
    if not api_key:
        print("[ERROR] DEEPSEEK_API_KEY not set in .env")
        return
    
    # Find test PDF
    pdf_dir = Path("D:/code/zcgl/tools/pdf-samples")
    pdf_files = list(pdf_dir.glob("*.pdf"))
    
    if not pdf_files:
        print("[ERROR] No PDF files found in pdf-samples")
        return
    
    pdf_path = pdf_files[0]
    print(f"\n[INFO] Testing with: {pdf_path.name}")
    print(f"[INFO] File size: {pdf_path.stat().st_size / 1024 / 1024:.2f} MB")
    
    # Use DocumentExtractionManager
    try:
        from src.services.document.extraction_manager import (
            get_extraction_manager,
            DocumentType,
        )
        
        print("\n[INFO] Initializing extraction manager...")
        manager = get_extraction_manager()
        
        print("[INFO] Starting extraction (this may take 1-2 minutes)...")
        result = await manager.extract(str(pdf_path), doc_type=DocumentType.CONTRACT)
        
        print("\n" + "=" * 60)
        print("EXTRACTION RESULT")
        print("=" * 60)
        print(f"Success: {result.success}")
        print(f"Document Type: {result.document_type.value}")
        print(f"Confidence: {result.confidence_score:.2%}")
        print(f"Processing Time: {result.processing_time_ms:.0f}ms")
        print(f"Extraction Method: {result.extraction_method}")
        
        if result.warnings:
            print(f"\nWarnings: {result.warnings}")
        
        if result.error:
            print(f"\n[ERROR] {result.error}")
        
        if result.extracted_fields:
            print("\n" + "-" * 40)
            print("EXTRACTED FIELDS")
            print("-" * 40)
            print(json.dumps(result.extracted_fields, ensure_ascii=False, indent=2))
        
    except Exception as e:
        print(f"\n[ERROR] Extraction failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_extraction())
