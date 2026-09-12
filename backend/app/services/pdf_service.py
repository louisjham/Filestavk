"""
PDF text extraction service.

Primary path: pdfplumber (fast, text-based PDFs).
Fallback:     pdf2image + pytesseract (OCR for scanned/image PDFs).
"""
import os
import logging
from typing import TypedDict

import pdfplumber

logger = logging.getLogger(__name__)


class PdfResult(TypedDict):
    text: str
    page_count: int
    extraction_method: str  # "pdfplumber" | "tesseract" | "none"


def process_pdf(filepath: str) -> PdfResult:
    """
    Extract text from a PDF file.

    Tries pdfplumber first. If no text is extracted (scanned/image PDF),
    falls back to OCR via pdf2image + pytesseract.
    """
    if not os.path.exists(filepath):
        return {"text": "", "page_count": 0, "extraction_method": "none"}

    text = ""
    page_count = 0

    # --- Primary: pdfplumber ---
    try:
        with pdfplumber.open(filepath) as pdf:
            page_count = len(pdf.pages)
            parts = []
            for page in pdf.pages:
                extracted = page.extract_text()
                if extracted:
                    parts.append(extracted)
            text = "\n".join(parts)
    except Exception as e:
        logger.warning("pdfplumber failed for %s: %s", filepath, e)

    if text.strip():
        return {"text": text.strip(), "page_count": page_count, "extraction_method": "pdfplumber"}

    # --- Fallback: OCR ---
    try:
        import pytesseract
        from pdf2image import convert_from_path  # requires poppler

        logger.info("pdfplumber found no text, attempting OCR on %s", filepath)
        images = convert_from_path(filepath, dpi=200)
        page_count = page_count or len(images)
        ocr_parts = []
        for img in images:
            ocr_text = pytesseract.image_to_string(img, lang="eng")
            if ocr_text.strip():
                ocr_parts.append(ocr_text.strip())
        text = "\n".join(ocr_parts)
        return {"text": text.strip(), "page_count": page_count, "extraction_method": "tesseract"}

    except ImportError:
        logger.warning(
            "pdf2image not installed — OCR unavailable. "
            "Run: pip install pdf2image  (also requires poppler in PATH)"
        )
    except Exception as e:
        logger.warning("OCR failed for %s: %s", filepath, e)

    return {"text": "", "page_count": page_count, "extraction_method": "none"}

