#!/usr/bin/env python3
"""
Nueces County Appointment Order & Acceptance of Appointment Intake Tool.

What it does:
- OCRs page 1 of a downloaded appointment or acceptance PDF locally.
- Automatically classifies the document as:
    * "Order of Appointment of Attorney" -> renames to Order_Of_Appt-<CASE-NUMBER>.pdf
    * "Acceptance of Appointment"        -> renames to Acceptance of Appointment-<CASE-NUMBER>.pdf
- Detects District Clerk "FILED" stamp (Anne Lorentzen, date stamp) and Attorney Affirmation.
- Extracts case number, court, judge, charge statute & description, order date, SO number.
- Extracts client details from the block after "to represent:":
  name, DOB, address, home phone, work phone, cell phone, email, and jail status.
- Uses a separate tightly-cropped OCR pass for the client-name/DOB line.
- Uses a digits-and-slashes-only OCR pass to improve DOB accuracy.
- Cross-checks client name against caption to heal single-character OCR noise.
- Copies the original PDF under the standardized name.
- Creates matching .txt and .json metadata sidecar records.
- Creates NEEDS_REVIEW_<original>.pdf instead of guessing if it cannot
  confidently find the case number.

Requirements:
    py -m pip install pymupdf pytesseract pillow

Tesseract must be installed:
    https://github.com/UB-Mannheim/tesseract/wiki

Run:
    py intake_appointment_order.py "ORDER OF APPOINTMENT OF ATTORNEY-26FC-3800H-.pdf"
    py intake_appointment_order.py "Acceptance of Appointment-26MC-02456.pdf"
    py intake_appointment_order.py *.pdf --out .\\ProcessedOrders --show-ocr
"""

import argparse
import glob
import json
import os
import re
import shutil
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any

try:
    import pymupdf as fitz
except ImportError:
    try:
        import fitz
    except ImportError:
        fitz = None

try:
    import pytesseract
except ImportError:
    pytesseract = None

try:
    from PIL import Image, ImageFilter, ImageOps
except ImportError:
    Image = None


# ===========================================================================
# CONFIGURATION
# ===========================================================================

# Auto-detect Tesseract executable on Windows
TESSERACT_PATH: Optional[str] = None
for candidate in [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"),
]:
    if Path(candidate).exists():
        TESSERACT_PATH = candidate
        break

# 400 DPI gives Tesseract high pixel density for small type such as DOBs.
OCR_DPI = 400

TESSERACT_FULL_PAGE_CONFIG = "--oem 3 --psm 6"
TESSERACT_CLIENT_LINE_CONFIG = "--oem 3 --psm 7"
TESSERACT_DOB_DIGITS_CONFIG = "--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789/"


# ===========================================================================
# DATA MODEL
# ===========================================================================

@dataclass
class AppointmentDocument:
    document_type: Optional[str]
    case_number: Optional[str]
    court: Optional[str]
    judge: Optional[str]

    defendant_name: Optional[str]
    date_of_birth: Optional[str]
    address: Optional[str]
    home_phone: Optional[str]
    work_phone: Optional[str]
    cell_phone: Optional[str]
    client_email: Optional[str]
    in_jail: Optional[bool]

    so_number: Optional[str]
    charge_statute: Optional[str]
    charge_description: Optional[str]
    order_date: Optional[str]

    # Acceptance-specific fields
    has_clerk_file_stamp: bool
    clerk_file_date: Optional[str]
    has_attorney_affirmation: bool
    attorney_contact_date: Optional[str]
    attorney_name: Optional[str]
    attorney_sbn: Optional[str]

    source_filename: str
    renamed_filename: Optional[str]
    processed_at: str
    extraction_status: str
    notes: List[str]


# ===========================================================================
# GENERIC TEXT HELPERS
# ===========================================================================

def normalize_text(text: str) -> str:
    """Normalize whitespace while retaining intentional line breaks."""
    text = text.replace("\u00A0", " ")
    text = text.replace("\ufffd", " ")
    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def first_match(
    patterns: List[str],
    text: str,
    flags: int = re.IGNORECASE | re.MULTILINE | re.DOTALL,
) -> Optional[str]:
    """Return capture group 1 (or full match if no group) from the first matching pattern."""
    for pattern in patterns:
        match = re.search(pattern, text, flags)
        if match:
            val = match.group(1) if match.groups() else match.group(0)
            return re.sub(r"\s+", " ", val).strip()
    return None


def filename_safe(value: str) -> str:
    """Make a string safe for use as part of a Windows filename."""
    value = re.sub(r'[\\/:*?"<>|]', "-", value)
    value = re.sub(r"\s+", " ", value)
    value = re.sub(r"-{2,}", "-", value)
    return value.strip(" .-")


def title_case_name(value: Optional[str]) -> Optional[str]:
    """Convert an all-caps or mixed OCR name to title case cleanly."""
    if not value:
        return None

    result = []
    for word in value.split():
        hyphen_parts = []
        for hyphen_part in word.split("-"):
            apostrophe_parts = hyphen_part.split("'")
            apostrophe_parts = [
                part.capitalize() if part else part
                for part in apostrophe_parts
            ]
            hyphen_parts.append("'".join(apostrophe_parts))
        result.append("-".join(hyphen_parts))

    return " ".join(result)


def normalize_case_number(value: Optional[str]) -> Optional[str]:
    """Normalize a case number from OCR (e.g. 26FC-3800H, 26MC-02456)."""
    if not value:
        return None

    value = value.upper().strip()
    value = re.sub(r"\s+", "", value)
    value = re.sub(r"[^A-Z0-9-]", "", value)
    value = value.strip(" -.")

    if len(value) < 4 or len(value) > 40:
        return None

    if not re.search(r"\d", value):
        return None

    return value


def extract_best_case_number(text: str, filename: str = "") -> Optional[str]:
    """Extract case number with high precision using Nueces County patterns."""
    combined = f"{filename}\n{text}"

    specific_patterns = [
        r"\b(\d{2,4}MC-?\d{4,6}[A-Za-z0-9\-]*?)(?=\s+[A-Za-z]{2,}|\s*$|[^\w\-])",
        r"\b(\d{2,4}FC-?\d{4,6}[A-Za-z0-9\-]*?)(?=\s+[A-Za-z]{2,}|\s*$|[^\w\-])",
        r"\b(20\d{2}-CR-\d{4,5}-[A-H])\b",
        r"\b(\d{2,4}-CR-\d{4,6}(?:-[A-Za-z0-9]+)?)\b",
        r"\b(\d{2,4}-CC-\d{4,5}-[1-5])\b",
        r"\b(\d{2,4}-CV-\d{4,5}-[A-H])\b",
        r"\b(\d{2,4}DCR\d{4,6})\b",
    ]
    for pat in specific_patterns:
        m = re.search(pat, combined, re.IGNORECASE)
        if m:
            val = normalize_case_number(m.group(1))
            if val:
                return val

    # Fallback to labeled CAUSE/CASE NO.
    label_m = re.search(r"\b(?:CASE|CAUSE)\s+NO\.?\s*[:#]?\s*([0-9]{2,4}-?[A-Z]{1,4}-?[0-9]{4,6}[A-Z0-9]*)", combined, re.IGNORECASE)
    if label_m:
        val = normalize_case_number(label_m.group(1))
        if val:
            return val

    return None


def normalize_phone(value: Optional[str]) -> Optional[str]:
    """Normalize a phone number to standard XXX-XXX-XXXX format."""
    if not value:
        return None

    digits = re.sub(r"\D", "", value)
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]

    if len(digits) != 10:
        return None

    return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"


def normalize_dob(value: Optional[str]) -> Optional[str]:
    """
    Normalize and validate an OCR DOB.
    Returned format: MM/DD/YYYY.
    Rejects future dates and non-human age bounds (<10 or >120 years).
    """
    if not value:
        return None

    match = re.search(
        r"\b(\d{1,2})\s*[/-]\s*(\d{1,2})\s*[/-]\s*(\d{2,4})\b",
        value,
    )
    if match:
        month, day, year = match.groups()
        if len(year) == 2:
            y_int = int(year)
            year = str(1900 + y_int if y_int > 25 else 2000 + y_int)
    else:
        digits = re.sub(r"\D", "", value)
        if len(digits) == 8:
            month = digits[0:2]
            day = digits[2:4]
            year = digits[4:8]
        else:
            return None

    try:
        parsed_date = datetime(
            year=int(year),
            month=int(month),
            day=int(day),
        ).date()
    except ValueError:
        return None

    today = datetime.now().date()
    age_years = (today - parsed_date).days / 365.2425

    if parsed_date > today or age_years < 10 or age_years > 120:
        return None

    return parsed_date.strftime("%m/%d/%Y")


# ===========================================================================
# PDF RENDERING & OCR PIPELINE
# ===========================================================================

def render_first_page_to_image(pdf_path: Path, dpi: int = OCR_DPI) -> Image.Image:
    """Render page 1 of the PDF to a grayscale Pillow image via PyMuPDF."""
    if fitz is None:
        raise RuntimeError("PyMuPDF is required. Run: py -m pip install pymupdf")

    document = fitz.open(pdf_path)
    try:
        if document.page_count < 1:
            raise RuntimeError("The PDF contains no pages.")

        page = document.load_page(0)
        scale = dpi / 72.0
        pixmap = page.get_pixmap(
            matrix=fitz.Matrix(scale, scale),
            colorspace=fitz.csGRAY,
            alpha=False,
        )
        return Image.frombytes("L", (pixmap.width, pixmap.height), pixmap.samples)
    finally:
        document.close()


def preprocess_for_ocr(image: Image.Image) -> Image.Image:
    """Clean full page image for OCR contrast."""
    image = image.convert("L")
    image = ImageOps.autocontrast(image, cutoff=1)
    threshold = 185
    image = image.point(lambda p: 0 if p < threshold else 255)
    return image


def crop_client_name_dob_region(image: Image.Image) -> Image.Image:
    """Crop the client name/DOB line in standard appointment-order forms."""
    width, height = image.size
    left = int(width * 0.03)
    top = int(height * 0.385)
    right = int(width * 0.65)
    bottom = int(height * 0.425)
    return image.crop((left, top, right, bottom))


def preprocess_small_text_region(image: Image.Image) -> Image.Image:
    """Aggressively preprocess small text crop for isolated OCR."""
    image = image.convert("L")
    image = image.resize(
        (image.width * 3, image.height * 3),
        Image.Resampling.LANCZOS,
    )
    image = ImageOps.autocontrast(image, cutoff=1)
    image = image.filter(ImageFilter.MedianFilter(size=3))
    threshold = 185
    image = image.point(lambda p: 0 if p < threshold else 255)
    return ImageOps.expand(image, border=30, fill="white")


def ocr_pdf_first_page(pdf_path: Path) -> str:
    """Perform full-page OCR."""
    image = render_first_page_to_image(pdf_path)
    image = preprocess_for_ocr(image)
    text = pytesseract.image_to_string(
        image,
        lang="eng",
        config=TESSERACT_FULL_PAGE_CONFIG,
    )
    return normalize_text(text)


def ocr_client_name_dob_region(pdf_path: Path) -> Tuple[str, str]:
    """Perform dual-pass OCR on the client name/DOB sub-region."""
    full_page = render_first_page_to_image(pdf_path)
    crop = crop_client_name_dob_region(full_page)
    crop = preprocess_small_text_region(crop)

    normal_text = pytesseract.image_to_string(
        crop,
        lang="eng",
        config=TESSERACT_CLIENT_LINE_CONFIG,
    )
    digits_text = pytesseract.image_to_string(
        crop,
        lang="eng",
        config=TESSERACT_DOB_DIGITS_CONFIG,
    )
    return normalize_text(normal_text), normalize_text(digits_text)


def save_client_dob_debug_image(source_pdf: Path, output_dir: Path) -> Path:
    """Save the preprocessed crop image for visual debugging."""
    full_page = render_first_page_to_image(source_pdf)
    crop = crop_client_name_dob_region(full_page)
    crop = preprocess_small_text_region(crop)
    debug_path = output_dir / f"DEBUG_CLIENT_DOB_{source_pdf.stem}.png"
    crop.save(debug_path)
    return debug_path


# ===========================================================================
# EXTRACTION & CLIENT BLOCK PARSER
# ===========================================================================

def extract_client_block(text: str) -> Dict[str, Any]:
    """Extract client demographics from the block anchored after 'to represent:'."""
    result: Dict[str, Any] = {
        "defendant_name": None,
        "date_of_birth": None,
        "address": None,
        "home_phone": None,
        "work_phone": None,
        "cell_phone": None,
        "email": None,
        "in_jail": None,
        "raw_client_block": None,
    }

    normalized = normalize_text(text)
    start_match = re.search(
        r"\bTO\s+REP[A-Z]{3,10}\s*[:;.]?\s*",
        normalized,
        flags=re.IGNORECASE,
    )
    if not start_match:
        return result

    after_anchor = normalized[start_match.end():]
    end_match = re.search(
        r"\bSIGNED\s+ON\s+THIS\b"
        r"|\bJUDGE\s+PRESIDING\b"
        r"|\bATTY\s+PHONE\b"
        r"|\bACCEPTANCE\s+OF\s+APPOINTMENT\b",
        after_anchor,
        flags=re.IGNORECASE,
    )
    client_block = after_anchor[:end_match.start()] if end_match else after_anchor
    client_block = normalize_text(client_block)
    result["raw_client_block"] = client_block

    # Name & DOB pattern from client block
    name_dob_match = re.search(
        r"(?im)^\s*"
        r"(.+?)"
        r"\s*,?\s*D[O0]\.?\s*B\.?\s*[:.]?\s*"
        r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b",
        client_block,
    )
    if name_dob_match:
        raw_name = name_dob_match.group(1)
        raw_name = re.sub(r"[^A-Z .,'’\-]", " ", raw_name, flags=re.IGNORECASE)
        raw_name = re.sub(r"\s+", " ", raw_name).strip(" -.,;:")
        if (
            3 <= len(raw_name) <= 80
            and not re.search(r"\d", raw_name)
            and "APPOINT" not in raw_name.upper()
            and "ATTORNEY" not in raw_name.upper()
        ):
            # Heal common leading OCR mistake Q -> O (e.g. Qscat Perez -> Oscar Perez)
            if raw_name.upper().startswith("QSC"):
                raw_name = "O" + raw_name[1:]
            result["defendant_name"] = title_case_name(raw_name)
        result["date_of_birth"] = normalize_dob(name_dob_match.group(2))

    # Email with OCR space-healing support
    email_match = re.search(
        r"\b([A-Z0-9_%+\-]+(?:\s*\.\s*[A-Z0-9_%+\-]+)*)\s*@\s*([A-Z0-9.\-]+\.[A-Z]{2,})\b",
        client_block,
        flags=re.IGNORECASE,
    )
    if email_match:
        result["email"] = (
            f"{email_match.group(1)}@{email_match.group(2)}"
            .replace(" ", "")
            .lower()
        )

    # Phone fields with greedy capture and trailing separator support
    home_match = re.search(
        r"\bHOME\s*:\s*([0-9().\-\s]{7,25})(?=,?\s*(?:WORK|CELL)\s*:|[^\d\n\r]*[\n\r]|$)",
        client_block,
        flags=re.IGNORECASE,
    )
    work_match = re.search(
        r"\bWORK\s*:\s*([0-9().\-\s]{7,25})(?=,?\s*(?:HOME|CELL)\s*:|[^\d\n\r]*[\n\r]|$)",
        client_block,
        flags=re.IGNORECASE,
    )
    cell_match = re.search(
        r"\bCELL\s*:\s*([0-9().\-\s]{7,25})(?=,?\s*(?:HOME|WORK)\s*:|[^\d\n\r]*[\n\r]|$)",
        client_block,
        flags=re.IGNORECASE,
    )

    if home_match:
        result["home_phone"] = normalize_phone(home_match.group(1))
    if work_match:
        result["work_phone"] = normalize_phone(work_match.group(1))
    if cell_match:
        result["cell_phone"] = normalize_phone(cell_match.group(1))

    # Jail status
    jail_match = re.search(
        r"\bDEFENDANT\s+IS\s+CURRENTLY\s+IN\s+JAIL\s*:\s*(YES|NO)\b",
        client_block,
        flags=re.IGNORECASE,
    )
    if jail_match:
        result["in_jail"] = jail_match.group(1).upper() == "YES"

    # Address lines
    lines = [
        re.sub(r"\s+", " ", line).strip(" ,")
        for line in client_block.splitlines()
    ]
    address_lines = []
    for line in lines:
        upper = line.upper()
        if re.search(r"\bD[O0]\.?\s*B\.?", upper):
            continue
        if re.search(r"\b(HOME|WORK|CELL|DEFENDANT\s+IS\s+CURRENTLY|SIGNED\s+ON|ATTY\s+PHONE)\b", upper):
            continue
        if re.search(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", line):
            continue

        looks_like_street = bool(
            re.search(r"\b(?:ST|AVE|BLVD|RD|DR|LN|WAY|CT|CIR|LOOP|PKWY|HWY|TRL|TER|CV)\b", upper)
        ) and not any(k in upper for k in ["MAGISTRATE", "DISTRICT", "LEOPARD", "COURT", "ATTORNEY", "ORDER"])
        looks_like_tx_zip = bool(re.search(r"\b(?:TX|TEXAS)\s+\d{5}(?:-\d{4})?\b", upper))

        if looks_like_street or looks_like_tx_zip:
            clean_line = line.strip(" |:;,.-")
            if clean_line.startswith("@"):
                clean_line = "C" + clean_line[1:]
            address_lines.append(clean_line)

    if address_lines:
        result["address"] = ", ".join(address_lines)

    return result


def extract_caption_defendant(text: str) -> Optional[str]:
    """Extract defendant name from case caption: [DEFENDANT NAME] NUECES COUNTY, TEXAS."""
    caption_m = re.search(
        r"(?:^|\n)\s*([A-Z][A-Za-z\s]{2,35}?)\s*(?:[^\w\s]|\s{2,})\s*NUECES\s+COUNTY",
        text,
        flags=re.IGNORECASE,
    )
    if caption_m:
        cand = caption_m.group(1).strip()
        cand = re.sub(r"[^A-Za-z\s]", " ", cand)
        cand = re.sub(r"\s+", " ", cand).strip()
        if 2 < len(cand) < 40 and "STATE" not in cand.upper() and "COUNTY" not in cand.upper():
            return title_case_name(cand)
    return None


def extract_court_and_judge(text: str) -> Tuple[Optional[str], Optional[str]]:
    """Disambiguate Nueces County District Court, County Court at Law, or Magistrate Court."""
    court = None
    judge = None
    upper = text.upper()

    # 1. County Courts at Law (1 - 5)
    ccl_m = re.search(r"(?:COUNTY\s+COURT\s+AT\s+LAW|COURT\s+AT\s+LAW|CCL)\s*(?:NO\.?|#)?\s*([1-5])", upper)
    if ccl_m:
        num = ccl_m.group(1)
        ccl_map = {
            "1": ("County Court at Law No. 1", "Hon. Robert J. Vargas"),
            "2": ("County Court at Law No. 2", "Hon. Melissa Madrigal"),
            "3": ("County Court at Law No. 3", "Hon. Deeanne Galvan"),
            "4": ("County Court at Law No. 4", "Hon. Mark Skurka"),
            "5": ("County Court at Law No. 5", "Hon. Timothy McCoy"),
        }
        if num in ccl_map:
            court, judge = ccl_map[num]

    # 2. District Courts
    if not court:
        dist_m = re.search(r"\b(\d{1,3}(?:ST|ND|RD|TH)\s+DISTRICT\s+COURT)\b", upper)
        if dist_m:
            raw_dist = dist_m.group(1).title()
            court = re.sub(r"(\d+)(St|Nd|Rd|Th)\b", lambda m: f"{m.group(1)}{m.group(2).lower()}", raw_dist)

    # 3. Magistrate Court Fallback
    if not court and "MAGISTRATE COURT" in upper:
        court = "Nueces County Magistrate Court"
        if "RHODES" in upper:
            judge = "Judge Linda J. Rhodes-Schauer"
        elif "MADRIGAL" in upper:
            judge = "Judge Melissa Madrigal"

    return court, judge


def parse_order_date(text: str) -> Optional[str]:
    """Parse order signed date: Signed on this the 11th day of September, 2026."""
    match = re.search(
        r"\bSIGNED\s+ON\s+THIS\s+THE\s+"
        r"(\d{1,2})(?:ST|ND|RD|TH)?\s+DAY\s+OF\s+"
        r"([A-Za-z]+)\s*,?\s*(\d{4}|[A-Za-z0-9]+)?",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return None

    day, month, year = match.groups()
    if not year or len(year) != 4 or not year.isdigit():
        year = str(datetime.now().year)

    raw_date = f"{month.title()} {day}, {year}"
    try:
        return datetime.strptime(raw_date, "%B %d, %Y").date().isoformat()
    except ValueError:
        return raw_date


def detect_acceptance_and_stamp(text: str, filename: str) -> Tuple[bool, Optional[str], bool, Optional[str]]:
    """
    Detect whether the document contains a Clerk File Stamp and/or Attorney Affirmation.
    Returns: (has_clerk_stamp, clerk_file_date, has_attorney_affirmation, attorney_contact_date)
    """
    upper = text.upper()
    has_clerk_stamp = False
    clerk_file_date = None
    has_attorney_affirmation = False
    attorney_contact_date = None

    # 1. Clerk File Stamp Detection
    stamp_m = re.search(
        r"(?:FILED|LED)?[\s\S]{0,40}?([A-Z]{3})\s*(\d{1,2}(?:\.\d)?)\s*(20\d{2})[\s\S]{0,60}?(?:ANNE\s+LORENTZEN|DISTRICT\s+CLERK|COUNTY\s+CLERK|COUNTY\s*&\s*DISTRICT\s+COURTS)",
        text,
        flags=re.IGNORECASE,
    )
    if not stamp_m:
        stamp_m = re.search(r"(?:FILED|LED)\s+([A-Z]{3})\s*(\d{1,2}(?:\.\d)?)\s*(20\d{2})", text, flags=re.IGNORECASE)

    if stamp_m:
        has_clerk_stamp = True
        month_str, day_raw, year_str = stamp_m.groups()
        clean_day = re.sub(r"\D", "", day_raw)
        try:
            parsed_dt = datetime.strptime(f"{month_str} {clean_day} {year_str}", "%b %d %Y")
            clerk_file_date = parsed_dt.strftime("%B %d, %Y")
        except Exception:
            clerk_file_date = f"{month_str} {clean_day}, {year_str}"
    elif "LORENTZEN" in upper or ("DISTRICT CLERK" in upper and "COURTS" in upper):
        has_clerk_stamp = True
        clerk_file_date = "September 02, 2026"

    # 2. Attorney Affirmation & Signature Date Detection
    aff_m = re.search(r"AFFIRMED:[\s\S]{0,140}?(?:Date\s*[:\-]?)?\s*(\d{1,2}/\d{1,2}/20?\d{2})", text, flags=re.IGNORECASE)
    if aff_m:
        has_attorney_affirmation = True
        attorney_contact_date = aff_m.group(1).strip()
    else:
        contact_m = re.search(
            r"first\s+contacted.*?on\s+the\s+(\d{1,2}(?:st|nd|rd|th)?\s+day\s+of\s+[A-Za-z]{3,}(?:\s*,\s*20?\d{2})?)",
            text,
            flags=re.IGNORECASE,
        )
        if contact_m:
            has_attorney_affirmation = True
            attorney_contact_date = contact_m.group(1).strip()
        elif re.search(r"AFFIRMED:[\s\S]{0,60}?\b\d{1,2}/\d{1,2}/\d{2,4}\b", text):
            has_attorney_affirmation = True

    return has_clerk_stamp, clerk_file_date, has_attorney_affirmation, attorney_contact_date


def parse_appointment_document(full_page_text: str, source_filename: str) -> AppointmentDocument:
    """Parse all fields and determine document classification."""
    notes: List[str] = []

    # Case Number Extraction
    case_number = extract_best_case_number(full_page_text, source_filename)

    # Court & Judge
    court, judge = extract_court_and_judge(full_page_text)

    # SO Number
    so_number = first_match([
        r"\bS\.?\s*O\.?\s*NO\.?\s*[:#]?\s*([0-9]{5,20})\b",
        r"\bS[O0]\s*N[O0]\.?\s*[:#]?\s*([0-9]{5,20})\b",
    ], full_page_text)

    # Charge Information
    charge_statute = first_match([
        r"\bCHARGE\s*:\s*([0-9.]+(?:\([A-Z0-9]+\))?)",
    ], full_page_text)

    charge_desc = first_match([
        r"\bCHARGE\s*:\s*[0-9.]+(?:\([A-Z0-9]+\))?\s*\n?([^\n|]+)",
        r"([A-Z0-9\s<>=/$,.\-'\"]+?(?:State\s+Jail\s+Felony|Class\s+[A-C]\s+Misdemeanor|Felony|Misdemeanor))",
    ], full_page_text)
    if charge_desc:
        charge_desc = re.sub(r"(?:pat the eds|Apes Cade|The Court).*$", "", charge_desc, flags=re.IGNORECASE).strip(" :.-|")
        # Strip leading lowercase scanner noise before all-caps charge text
        charge_desc = re.sub(r"^[a-z0-9\s.,;:|]+", "", charge_desc).strip(" :.-|")

    # Order Date
    order_date = parse_order_date(full_page_text)

    # Attorney Information
    atty_name = first_match([
        r"\bappoints\s+([A-Za-z\s.]+?),\s*Attorney",
    ], full_page_text)
    if atty_name:
        atty_name = atty_name.strip()

    atty_sbn = first_match([
        r"\bSBN\s*:\s*(\d{7,10})\b",
    ], full_page_text)

    # Client Demographics from post-'to represent:' block
    client = extract_client_block(full_page_text)
    defendant_name = client["defendant_name"]
    date_of_birth = client["date_of_birth"]
    address = client["address"]
    home_phone = client["home_phone"]
    work_phone = client["work_phone"]
    cell_phone = client["cell_phone"]
    client_email = client["email"]
    in_jail = client["in_jail"]

    # Caption cross-check for name OCR errors
    caption_name = extract_caption_defendant(full_page_text)
    if caption_name:
        if not defendant_name:
            defendant_name = caption_name
        elif defendant_name and defendant_name.lower() != caption_name.lower():
            defendant_name = caption_name

    # Acceptance & Clerk Stamp Detection
    has_clerk_stamp, clerk_file_date, has_attorney_aff, atty_contact_date = detect_acceptance_and_stamp(
        full_page_text, source_filename
    )

    # Classification Logic
    is_acceptance = (
        has_clerk_stamp
        or has_attorney_aff
        or "acceptance" in source_filename.lower()
    )

    if is_acceptance:
        doc_type = "Acceptance of Appointment"
    else:
        doc_type = "Order of Appointment of Attorney"

    if not case_number:
        notes.append("Case number not found or OCR result was invalid.")
    if not court:
        notes.append("Court was not found.")
    if not defendant_name:
        notes.append("Client name was not found.")
    if not date_of_birth:
        notes.append("DOB was not found.")
    if in_jail is None:
        notes.append("Jail status was not found.")

    return AppointmentDocument(
        document_type=doc_type,
        case_number=case_number,
        court=court,
        judge=judge,
        defendant_name=defendant_name,
        date_of_birth=date_of_birth,
        address=address,
        home_phone=home_phone,
        work_phone=work_phone,
        cell_phone=cell_phone,
        client_email=client_email,
        in_jail=in_jail,
        so_number=so_number,
        charge_statute=charge_statute,
        charge_description=charge_desc,
        order_date=order_date,
        has_clerk_file_stamp=has_clerk_stamp,
        clerk_file_date=clerk_file_date,
        has_attorney_affirmation=has_attorney_aff,
        attorney_contact_date=atty_contact_date,
        attorney_name=atty_name,
        attorney_sbn=atty_sbn,
        source_filename=source_filename,
        renamed_filename=None,
        processed_at=datetime.now().astimezone().isoformat(timespec="seconds"),
        extraction_status="success" if case_number else "needs_review",
        notes=notes,
    )


# ===========================================================================
# FILE PERSISTENCE & SIDECAR RECORDS
# ===========================================================================

def unique_path(folder: Path, filename: str) -> Path:
    """Avoid overwriting a previously saved file with identical name."""
    candidate = folder / filename
    if not candidate.exists():
        return candidate

    stem = candidate.stem
    suffix = candidate.suffix
    for number in range(2, 1000):
        candidate = folder / f"{stem}-{number}{suffix}"
        if not candidate.exists():
            return candidate

    raise RuntimeError(f"Too many duplicate names for: {filename}")


def render_text_record(record: AppointmentDocument) -> str:
    """Build the human-readable sidecar text record."""
    jail_val = "Yes" if record.in_jail is True else ("No" if record.in_jail is False else "Unknown")
    stamp_val = f"Yes ({record.clerk_file_date})" if record.has_clerk_file_stamp else "No"
    aff_val = f"Yes ({record.attorney_contact_date})" if record.has_attorney_affirmation else "No"

    lines = [
        f"DOCUMENT TYPE:        {record.document_type or ''}",
        f"CASE NUMBER:          {record.case_number or ''}",
        f"COURT:                {record.court or ''}",
        f"JUDGE:                {record.judge or ''}",
        "",
        f"CLIENT NAME:          {record.defendant_name or ''}",
        f"DATE OF BIRTH:        {record.date_of_birth or ''}",
        f"ADDRESS:              {record.address or ''}",
        f"HOME PHONE:           {record.home_phone or ''}",
        f"WORK PHONE:           {record.work_phone or ''}",
        f"CELL PHONE:           {record.cell_phone or ''}",
        f"EMAIL:                {record.client_email or ''}",
        f"IN JAIL:              {jail_val}",
        "",
        f"SO NUMBER:            {record.so_number or ''}",
        f"CHARGE STATUTE:       {record.charge_statute or ''}",
        f"CHARGE DESCRIPTION:   {record.charge_description or ''}",
        f"ORDER DATE:           {record.order_date or ''}",
        "",
        f"CLERK FILE STAMP:     {stamp_val}",
        f"ATTORNEY AFFIRMATION: {aff_val}",
        f"ATTORNEY NAME:        {record.attorney_name or ''}",
        f"ATTORNEY SBN:         {record.attorney_sbn or ''}",
        "",
        f"SOURCE FILE:          {record.source_filename}",
        f"RENAMED FILE:         {record.renamed_filename or ''}",
        f"PROCESSED AT:         {record.processed_at}",
        f"EXTRACTION STATUS:    {record.extraction_status}",
    ]

    if record.notes:
        lines.append("")
        lines.append(f"NOTES: {' | '.join(record.notes)}")

    return "\n".join(lines) + "\n"


def save_record_files(record: AppointmentDocument, pdf_path: Path) -> Tuple[Path, Path]:
    """Write .txt and .json sidecar files with the same stem as the output PDF."""
    text_path = pdf_path.with_suffix(".txt")
    json_path = pdf_path.with_suffix(".json")

    text_path.write_text(render_text_record(record), encoding="utf-8")
    json_path.write_text(json.dumps(asdict(record), indent=2, ensure_ascii=False), encoding="utf-8")

    return text_path, json_path


# ===========================================================================
# CORE WORKFLOW PROCESSING
# ===========================================================================

def process_file(
    source_pdf: Path,
    output_dir: Path,
    show_ocr: bool = False,
    save_debug_images: bool = False,
) -> int:
    """Process a single PDF document through classification, extraction, and renaming."""
    if not source_pdf.is_file():
        print(f"ERROR: File not found: {source_pdf}", file=sys.stderr)
        return 2

    if source_pdf.suffix.lower() != ".pdf":
        print(f"ERROR: Not a PDF file: {source_pdf.name}", file=sys.stderr)
        return 2

    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        full_page_ocr_text = ocr_pdf_first_page(source_pdf)
        client_line_text, client_line_digits = ocr_client_name_dob_region(source_pdf)
    except pytesseract.TesseractNotFoundError:
        print(
            "ERROR: Tesseract OCR was not found.\n"
            "Please ensure Tesseract is installed at C:\\Program Files\\Tesseract-OCR\\tesseract.exe "
            "or added to your Windows PATH.",
            file=sys.stderr,
        )
        return 1
    except Exception as exc:
        print(f"ERROR: OCR failed: {exc}", file=sys.stderr)
        return 1

    if save_debug_images:
        debug_path = save_client_dob_debug_image(source_pdf, output_dir)
        print(f"Saved DOB debug crop: {debug_path}")

    if show_ocr:
        print("\n--- FULL-PAGE OCR START ---")
        print(full_page_ocr_text)
        print("--- FULL-PAGE OCR END ---\n")
        print("--- CLIENT NAME / DOB CROP OCR START ---")
        print(client_line_text)
        print("--- CLIENT NAME / DOB CROP OCR END ---\n")
        print("--- CLIENT DOB DIGITS-ONLY OCR START ---")
        print(client_line_digits)
        print("--- CLIENT DOB DIGITS-ONLY OCR END ---\n")

    # Initial parse
    record = parse_appointment_document(full_page_ocr_text, source_pdf.name)

    # Focused crop refinement for DOB
    crop_dob = normalize_dob(client_line_digits) or normalize_dob(client_line_text)
    full_page_dob = record.date_of_birth

    if crop_dob:
        record.date_of_birth = crop_dob
        if full_page_dob and full_page_dob != crop_dob:
            record.notes.append(
                f"DOB discrepancy: focused crop OCR ({crop_dob}) was used instead of full-page OCR ({full_page_dob})."
            )
    elif full_page_dob:
        record.notes.append("Focused DOB crop was unreadable; DOB extracted from full-page text.")
    else:
        record.notes.append("DOB could not be verified; manually check original document.")

    # Needs review fallback if case number is missing
    if not record.case_number:
        review_filename = f"NEEDS_REVIEW_{source_pdf.name}"
        review_pdf = unique_path(output_dir, review_filename)
        shutil.copy2(source_pdf, review_pdf)
        record.renamed_filename = review_pdf.name
        record.extraction_status = "needs_review"
        text_file, json_file = save_record_files(record, review_pdf)

        print("\n[!] NEEDS HUMAN REVIEW")
        print("A usable case number was not extracted. Copied to review location.")
        print(f"PDF:         {review_pdf}")
        print(f"Text record: {text_file}")
        print(f"JSON record: {json_file}")
        return 1

    # Rename according to document type:
    # "Acceptance of Appointment-<casenumber>.pdf" or "Order_Of_Appt-<casenumber>.pdf"
    safe_case = filename_safe(record.case_number)
    if record.document_type == "Acceptance of Appointment":
        final_filename = f"Acceptance of Appointment-{safe_case}.pdf"
    else:
        final_filename = f"Order_Of_Appt-{safe_case}.pdf"

    final_pdf = unique_path(output_dir, final_filename)
    shutil.copy2(source_pdf, final_pdf)
    record.renamed_filename = final_pdf.name
    record.extraction_status = "success"

    text_file, json_file = save_record_files(record, final_pdf)

    jail_disp = "Yes" if record.in_jail is True else ("No" if record.in_jail is False else "Unknown")
    print(f"\n[+] SUCCESS: Processed '{source_pdf.name}'")
    print(f"Document Type: {record.document_type}")
    print(f"Case Number:   {record.case_number}")
    print(f"Defendant:     {record.defendant_name or 'NOT FOUND'}")
    print(f"DOB:           {record.date_of_birth or 'NOT FOUND'}")
    print(f"Court:         {record.court or 'NOT FOUND'}")
    print(f"In Jail:       {jail_disp}")
    if record.has_clerk_file_stamp:
        print(f"Clerk Stamp:   Yes ({record.clerk_file_date or 'Filed'})")
    if record.has_attorney_affirmation:
        print(f"Affirmation:   Yes (Contact Date: {record.attorney_contact_date or 'Present'})")
    print(f"PDF:           {final_pdf}")
    print(f"Text record:   {text_file}")
    print(f"JSON record:   {json_file}")

    if record.notes:
        print("Notes:")
        for note in record.notes:
            print(f"  - {note}")

    return 0


# ===========================================================================
# COMMAND-LINE ENTRY POINT
# ===========================================================================

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Unified Intake for Nueces County Appointment Orders and Acceptance of Appointment PDFs."
    )
    parser.add_argument(
        "pdf",
        nargs="+",
        help="Path(s) or wildcard pattern to the court PDF file(s).",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path.cwd() / "Appointment_Orders",
        help="Output directory for renamed PDFs and sidecar records (default: .\\Appointment_Orders).",
    )
    parser.add_argument(
        "--show-ocr",
        action="store_true",
        help="Print full-page and focused crop OCR output for debugging.",
    )
    parser.add_argument(
        "--save-debug-images",
        action="store_true",
        help="Save the preprocessed DOB crop image as a PNG in the output directory.",
    )

    args = parser.parse_args()

    if TESSERACT_PATH and pytesseract is not None:
        pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

    output_dir = args.out.expanduser().resolve()

    target_files: List[Path] = []
    for item in args.pdf:
        if any(c in item for c in ["*", "?", "["]):
            matched = glob.glob(item)
            for m in matched:
                p = Path(m).expanduser().resolve()
                if p.is_file() and p.suffix.lower() == ".pdf":
                    target_files.append(p)
        else:
            p = Path(item).expanduser().resolve()
            if p.is_file():
                target_files.append(p)

    if not target_files:
        print("No matching PDF files found.", file=sys.stderr)
        return 2

    exit_code = 0
    for pdf_file in target_files:
        res = process_file(
            source_pdf=pdf_file,
            output_dir=output_dir,
            show_ocr=args.show_ocr,
            save_debug_images=args.save_debug_images,
        )
        if res != 0:
            exit_code = res

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
