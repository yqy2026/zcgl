"""
PDF Analyzer - Detect if PDF is scanned/image-based or digital/text-based
PDF分析器 - 检测PDF是扫描件还是数字版

Used for smart routing between text and vision extraction methods.
用于智能路由选择文本或视觉提取方式。
"""
import logging
from pathlib import Path
from typing import Tuple

logger = logging.getLogger(__name__)

# PyMuPDF import with graceful fallback
try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    logger.warning("PyMuPDF not installed. Run: pip install pymupdf")
    fitz = None
    PYMUPDF_AVAILABLE = False


def analyze_pdf(pdf_path: str) -> dict:
    """
    Analyze PDF to determine its type and characteristics.
    分析PDF以确定其类型和特征。
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        dict with analysis results:
        - is_scanned: True if PDF appears to be scanned/image-based
        - text_ratio: Ratio of text content to page area
        - page_count: Number of pages
        - has_images: Whether PDF contains images
        - recommendation: "vision" or "text" extraction method
    """
    if not PYMUPDF_AVAILABLE:
        logger.warning("PyMuPDF not available, defaulting to vision extraction")
        return {
            "is_scanned": True,
            "text_ratio": 0,
            "page_count": 0,
            "has_images": True,
            "recommendation": "vision"
        }
    
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    
    try:
        doc = fitz.open(str(pdf_path))
        page_count = len(doc)
        
        total_text_chars = 0
        total_images = 0
        pages_with_text = 0
        
        # Analyze first few pages (max 5)
        pages_to_check = min(page_count, 5)
        
        for page_idx in range(pages_to_check):
            page = doc[page_idx]
            
            # Extract text
            text = page.get_text("text")
            text_chars = len(text.strip())
            total_text_chars += text_chars
            
            if text_chars > 50:  # More than 50 chars = has meaningful text
                pages_with_text += 1
            
            # Count images
            images = page.get_images()
            total_images += len(images)
        
        doc.close()
        
        # Decision logic:
        # - If more than 50% of pages have extractable text (>50 chars) → likely digital
        # - If very few text chars but has images → likely scanned
        text_ratio = pages_with_text / pages_to_check if pages_to_check > 0 else 0
        avg_chars_per_page = total_text_chars / pages_to_check if pages_to_check > 0 else 0
        
        # Scanned PDF typically has very little extractable text
        # Digital PDF typically has >100 chars per page
        is_scanned = avg_chars_per_page < 100 and total_images > 0
        
        # Recommendation
        if is_scanned or avg_chars_per_page < 200:
            recommendation = "vision"
        else:
            recommendation = "text"
        
        result = {
            "is_scanned": is_scanned,
            "text_ratio": round(text_ratio, 2),
            "avg_chars_per_page": round(avg_chars_per_page, 1),
            "page_count": page_count,
            "has_images": total_images > 0,
            "total_images": total_images,
            "recommendation": recommendation
        }
        
        logger.info(f"PDF analysis: {result}")
        return result
        
    except Exception as e:
        logger.error(f"PDF analysis failed: {e}")
        # Default to vision on error (safer choice for Chinese contracts)
        return {
            "is_scanned": True,
            "text_ratio": 0,
            "page_count": 0,
            "has_images": True,
            "recommendation": "vision",
            "error": str(e)
        }


def is_scanned_pdf(pdf_path: str) -> bool:
    """
    Quick check if PDF is scanned/image-based.
    快速检查PDF是否为扫描件。
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        True if PDF appears to be scanned, False if digital
    """
    result = analyze_pdf(pdf_path)
    return result.get("is_scanned", True)


def get_extraction_recommendation(pdf_path: str) -> str:
    """
    Get recommended extraction method for the PDF.
    获取PDF的推荐提取方式。
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        "vision" or "text"
    """
    result = analyze_pdf(pdf_path)
    return result.get("recommendation", "vision")
