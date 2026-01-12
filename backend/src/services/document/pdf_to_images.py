"""
PDF to Image Converter using PyMuPDF
PDF转图片转换器

Converts PDF pages to PNG images for multimodal LLM processing
将PDF页面转换为PNG图片，用于多模态LLM处理
"""
import logging
import tempfile
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

# PyMuPDF import with graceful fallback
try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    logger.warning("PyMuPDF not installed. Run: pip install pymupdf")
    fitz = None
    PYMUPDF_AVAILABLE = False


def pdf_to_images(
    pdf_path: str,
    output_dir: Optional[str] = None,
    dpi: int = 200,
    max_pages: int = 10,
    image_format: str = "png"
) -> List[str]:
    """
    Convert PDF pages to PNG images.
    将PDF页面转换为PNG图片
    
    Args:
        pdf_path: Path to PDF file / PDF文件路径
        output_dir: Output directory (uses temp if None) / 输出目录
        dpi: Resolution (200 recommended for OCR/Vision) / 分辨率
        max_pages: Maximum pages to convert / 最大转换页数
        image_format: Output format (png/jpg) / 输出格式
    
    Returns:
        List of image file paths / 图片文件路径列表
        
    Raises:
        ImportError: If PyMuPDF not installed
        FileNotFoundError: If PDF file not found
    """
    if not PYMUPDF_AVAILABLE:
        raise ImportError("PyMuPDF is required. Install with: pip install pymupdf")
    
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    
    # Create output directory
    if output_dir is None:
        output_dir = tempfile.mkdtemp(prefix="pdf_images_")
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    image_paths: List[str] = []
    
    # Calculate zoom factor (72 is default PDF resolution)
    zoom = dpi / 72.0
    matrix = fitz.Matrix(zoom, zoom)
    
    try:
        doc = fitz.open(str(pdf_path))
        page_count = min(len(doc), max_pages)
        
        logger.info(f"Converting {page_count} pages from {pdf_path.name} at {dpi} DPI")
        
        for page_num in range(page_count):
            page = doc[page_num]
            
            # Render page to pixmap
            pix = page.get_pixmap(matrix=matrix)
            
            # Determine output filename
            ext = "png" if image_format.lower() == "png" else "jpg"
            output_path = output_dir / f"page_{page_num + 1:03d}.{ext}"
            
            # Save image
            pix.save(str(output_path))
            image_paths.append(str(output_path))
            
            logger.debug(f"Converted page {page_num + 1}/{page_count}: {output_path}")
        
        doc.close()
        logger.info(f"PDF conversion complete: {len(image_paths)} images created")
        
    except Exception as e:
        logger.error(f"PDF conversion failed: {e}")
        raise
    
    return image_paths


def get_pdf_page_count(pdf_path: str) -> int:
    """
    Get the number of pages in a PDF file.
    获取PDF文件的页数
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        Number of pages
    """
    if not PYMUPDF_AVAILABLE:
        raise ImportError("PyMuPDF is required. Install with: pip install pymupdf")
    
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    
    try:
        doc = fitz.open(str(pdf_path))
        count = len(doc)
        doc.close()
        return count
    except Exception as e:
        logger.error(f"Failed to get page count: {e}")
        raise


def cleanup_temp_images(image_paths: List[str]) -> None:
    """
    Delete temporary image files.
    删除临时图片文件
    
    Args:
        image_paths: List of image file paths to delete
    """
    for path in image_paths:
        try:
            Path(path).unlink(missing_ok=True)
        except Exception as e:
            logger.warning(f"Failed to delete {path}: {e}")
