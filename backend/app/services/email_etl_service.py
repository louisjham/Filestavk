"""
Email ETL Parsing Service.

Parses RFC 822 MIME .eml files and applies deterministic domain rules
for Nueces County court dockets, Odyssey e-filings, and County Auditor warrants.
Generates structured proposals for mandatory Human Verification.
"""

import os
import re
import email
from email.header import decode_header
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Grounded Nueces County Courts mapping
NUECES_COURTS = [
    {"name": "105th District Court", "judge": "Hon. Jack W. Pulcher", "type": "DISTRICT"},
    {"name": "28th District Court", "judge": "Hon. Nanette Hasette", "type": "DISTRICT"},
    {"name": "94th District Court", "judge": "Hon. Bobby Galvan", "type": "DISTRICT"},
    {"name": "117th District Court", "judge": "Hon. Amanda Putman", "type": "DISTRICT"},
    {"name": "148th District Court", "judge": "Hon. Carlos Valdez", "type": "DISTRICT"},
    {"name": "214th District Court", "judge": "Hon. Inna Klein", "type": "DISTRICT"},
    {"name": "319th District Court", "judge": "Hon. David Stith", "type": "DISTRICT"},
    {"name": "347th District Court", "judge": "Hon. Missy Medary", "type": "DISTRICT"},
    {"name": "County Court at Law No. 1", "judge": "Hon. Robert J. Vargas", "type": "COUNTY_COURT_AT_LAW"},
    {"name": "County Court at Law No. 2", "judge": "Hon. Melissa Madrigal", "type": "COUNTY_COURT_AT_LAW"},
    {"name": "County Court at Law No. 3", "judge": "Hon. Deeanne Galvan", "type": "COUNTY_COURT_AT_LAW"},
    {"name": "County Court at Law No. 4", "judge": "Hon. Mark Skurka", "type": "COUNTY_COURT_AT_LAW"},
    {"name": "County Court at Law No. 5", "judge": "Hon. Timothy McCoy", "type": "COUNTY_COURT_AT_LAW"},
]


def _decode_header_str(header_val: Optional[str]) -> str:
    if not header_val:
        return ""
    try:
        parts = decode_header(header_val)
        res = []
        for p, enc in parts:
            if isinstance(p, bytes):
                res.append(p.decode(enc or "utf-8", errors="replace"))
            else:
                res.append(str(p))
        return "".join(res).strip()
    except Exception:
        return str(header_val).strip()


def parse_eml_file(file_path: str) -> Dict[str, Any]:
    """Parse raw .eml RFC 822 file into headers, body text, html, and attachments."""
    if not os.path.exists(file_path):
        return {"error": f"File not found: {file_path}"}

    with open(file_path, "rb") as f:
        msg = email.message_from_binary_file(f)

    subject = _decode_header_str(msg.get("Subject", "No Subject"))
    from_addr = _decode_header_str(msg.get("From", ""))
    to_addr = _decode_header_str(msg.get("To", ""))
    date_str = _decode_header_str(msg.get("Date", ""))
    message_id = _decode_header_str(msg.get("Message-ID", ""))

    plain_body = ""
    html_body = ""
    attachments = []

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition", ""))

            if "attachment" in content_disposition:
                filename = part.get_filename()
                if filename:
                    attachments.append({
                        "filename": _decode_header_str(filename),
                        "content_type": content_type,
                        "size_bytes": len(part.get_payload(decode=True) or b""),
                    })
            elif content_type == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    plain_body += payload.decode("utf-8", errors="replace") + "\n"
            elif content_type == "text/html":
                payload = part.get_payload(decode=True)
                if payload:
                    html_body += payload.decode("utf-8", errors="replace") + "\n"
    else:
        content_type = msg.get_content_type()
        payload = msg.get_payload(decode=True)
        if payload:
            decoded = payload.decode("utf-8", errors="replace")
            if content_type == "text/html":
                html_body = decoded
            else:
                plain_body = decoded

    # If html exists but plain text is empty, produce a stripped plain text version
    if html_body and not plain_body:
        clean_text = re.sub(r"<[^>]+>", " ", html_body)
        plain_body = re.sub(r"\s+", " ", clean_text).strip()

    # Run legal entity ETL extraction
    extracted = extract_legal_entities(subject, from_addr, plain_body, html_body)

    return {
        "subject": subject,
        "from": from_addr,
        "to": to_addr,
        "date": date_str,
        "message_id": message_id,
        "plain_body": plain_body.strip(),
        "html_body": html_body.strip(),
        "attachments": attachments,
        "extracted": extracted,
    }


def extract_legal_entities(
    subject: str,
    from_addr: str,
    body_text: str,
    body_html: str
) -> Dict[str, Any]:
    """Extract structured Nueces County legal entities from email content."""
    combined_text = f"{subject}\n{from_addr}\n{body_text}\n{body_html}"

    # 1. Extract Nueces County Case / Cause Numbers
    cases_found = []
    cause_match = re.search(r'(?:CAUSE|CASE)\s*(?:NO\.?|#)?[:\s]*([0-9]{2,4}-?[A-Za-z]{1,4}-?[0-9]{4,6}(?:-[A-Za-z0-9]+)?)', combined_text, re.IGNORECASE)
    if cause_match:
        cases_found.append(cause_match.group(1).upper().strip())

    case_patterns = [
        r'\b(\d{2,4}MC-?\d{4,6}[A-Za-z0-9\-]*)\b',       # Nueces Misdemeanors (e.g. 26MC-02715)
        r'\b(20\d{2}-CR-\d{4,5}-[A-H])\b',              # Nueces Felony format (e.g. 2024-CR-1042-D)
        r'\b(\d{2,4}-CR-\d{4,6}(?:-[A-Za-z0-9]+)?)\b',  # General CR format
        r'\b(\d{2,4}-CC-\d{4,5}-[1-5])\b',              # County Court at Law cause format
        r'\b(\d{2,4}-CV-\d{4,5}-[A-H])\b',              # Civil format
        r'\b(\d{2,4}DCR\d{4,6})\b',                     # Tyler / Odyssey portal DCR format
    ]
    for pat in case_patterns:
        matches = re.findall(pat, combined_text, re.IGNORECASE)
        cases_found.extend([m.upper().strip() for m in matches])

    unique_cases = []
    for c in cases_found:
        if c not in unique_cases and len(c) >= 5:
            unique_cases.append(c)
    primary_case = unique_cases[0] if unique_cases else None

    # 2. Extract Court & Presiding Judge
    matched_court = None
    matched_judge = None
    combined_lower = combined_text.lower()

    # Disambiguate County Courts at Law (No. 1 to 5)
    ccl_match = re.search(r'(?:county\s+court[\s\S]{0,60}?at\s+law|court\s+at\s+law|at\s+law\s+no|ccl)\s*(?:no\.?|#)?\s*([1-5])', combined_lower)
    if ccl_match:
        ccl_num = ccl_match.group(1)
        ccl_map = {
            "1": ("County Court at Law No. 1", "Hon. Robert J. Vargas"),
            "2": ("County Court at Law No. 2", "Hon. Melissa Madrigal"),
            "3": ("County Court at Law No. 3", "Hon. Deeanne Galvan"),
            "4": ("County Court at Law No. 4", "Hon. Mark Skurka"),
            "5": ("County Court at Law No. 5", "Hon. Timothy McCoy"),
        }
        if ccl_num in ccl_map:
            matched_court, matched_judge = ccl_map[ccl_num]

    if not matched_court:
        for court_info in NUECES_COURTS:
            if court_info["type"] == "DISTRICT":
                dist_num = court_info["name"].split()[0].lower()
                if dist_num in combined_lower:
                    matched_court = court_info["name"]
                    matched_judge = court_info["judge"]
                    break

    # 3. Extract Defendant Name
    defendant_name = None
    def_match_a = re.search(r'NOW\s+COMES\s+([A-Z][a-zA-Z\s,\.]+?),\s*(?:Defendant|the\s+Defendant)', combined_text, re.IGNORECASE)
    def_match_b = re.search(r'I,\s*([A-Z][a-zA-Z\s,\.]+?),\s*(?:Defendant|the\s+Defendant)', combined_text, re.IGNORECASE)
    def_match_c = re.search(r'VS\.?\s*(?:§|\n|\s)+\s*([A-Z][A-Za-z\s,\.]+?)\s*(?:§|\n|NUECES|DEFENDANT)', combined_text)
    def_match_d = re.search(r'(?:State\s+v\.?|State\s+of\s+Texas\s+vs?\.?)\s+([A-Z][a-zA-Z\s,\.]+?)(?:\s*-\s*|\s*\(|\s*\n|$)', combined_text, re.IGNORECASE)
    def_match_e = re.search(r'Defendant:\s*([A-Z][a-zA-Z\s,\.]+?)(?:\s*\(|\s*\n|<|$)', combined_text, re.IGNORECASE)

    for cand_match in [def_match_a, def_match_b, def_match_c, def_match_d, def_match_e]:
        if cand_match:
            candidate = cand_match.group(1).strip().rstrip(",.-§ \t\n")
            candidate = re.sub(r'\s+', ' ', candidate)
            if 2 < len(candidate) < 50 and candidate.lower() not in ("the state of texas", "state of texas", "said court", "nueces county"):
                if candidate.isupper():
                    candidate = candidate.title()
                defendant_name = candidate
                break

    # 4. Extract Category & Specialized Domain Fields
    category = "UNCATEGORIZED"
    specialized_fields: Dict[str, Any] = {}
    proposed_actions: List[Dict[str, Any]] = []

    if any(k in combined_lower for k in ["waiver of arraignment", "waive arraignment", "waives arraignment"]):
        category = "WAIVER_OF_ARRAIGNMENT"
        specialized_fields["plea_entered"] = "Not Guilty"
        specialized_fields["requested_settings"] = ["Pre-Trial", "Jury Trial"]
        specialized_fields["purpose"] = "Waive formal reading of information, enter appearance, plead not guilty, and request pre-trial and jury trial docket settings."
        proposed_actions.append({
            "action": "RECORD_WAIVER_ARRAIGNMENT",
            "description": f"Record Waiver of Arraignment (Plea: Not Guilty) for Case #{primary_case or 'New'}",
        })

    elif any(k in combined_lower for k in ["warrant", "disbursement", "auditor", "direct deposit", "remittance advice"]):
        category = "COUNTY_AUDITOR_WARRANT"
        w_match = re.search(r'(?:Warrant|Check)\s*(?:Number|#)?[:\s]*([A-Z0-9\-]+)', combined_text, re.IGNORECASE)
        amt_match = re.search(r'\$\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?)', combined_text)
        voucher_ref_match = re.search(r'\b(VCH-[0-9]{4}-[0-9]{3,5}[A-Z\-]*)\b', combined_text, re.IGNORECASE)

        specialized_fields["warrant_number"] = w_match.group(1).strip() if w_match else None
        specialized_fields["amount_paid"] = float(amt_match.group(1).replace(",", "")) if amt_match else None
        specialized_fields["voucher_number"] = voucher_ref_match.group(1).upper() if voucher_ref_match else None

        proposed_actions.append({
            "action": "UPDATE_VOUCHER_PAID",
            "description": f"Update Voucher status to PAID (Warrant #{specialized_fields.get('warrant_number') or 'Auto'}, ${specialized_fields.get('amount_paid') or '0.00'})",
        })


    elif any(k in combined_lower for k in ["order appointing counsel", "order appointing", "appointment of counsel"]):
        category = "APPOINTMENT_ORDER"
        proposed_actions.append({
            "action": "VERIFY_APPOINTMENT_ORDER",
            "description": f"Mark Case #{primary_case or 'New'} Appointment Order as VERIFIED_ON_DOCKET (Qualifies for statutory voucher submission)",
        })

    elif any(k in combined_lower for k in ["hearing notice", "docket call", "arraignment", "plea", "order to appear"]):
        category = "HEARING_NOTICE"
        # Date and Time extraction
        date_match = re.search(r'(?:Date\s*&?\s*Time|Hearing\s*Date|On|for)[:\s]*([A-Za-z]+ \d{1,2}, \d{4}(?:\s+at\s+\d{1,2}:\d{2}\s*(?:AM|PM))?)', combined_text, re.IGNORECASE)
        specialized_fields["hearing_datetime"] = date_match.group(1).strip() if date_match else None

        proposed_actions.append({
            "action": "CREATE_HEARING_EVENT",
            "description": f"Create Court Hearing Event on Docket for {specialized_fields.get('hearing_datetime') or 'Scheduled Date'}",
        })

    elif any(k in combined_lower for k in ["e-filing", "efiling", "accepted", "efiletexas"]):
        category = "ODYSSEY_EFILING"
        env_match = re.search(r'(?:Envelope|Filing)\s*(?:ID|#)[:\s]*([0-9]+)', combined_text, re.IGNORECASE)
        specialized_fields["envelope_id"] = env_match.group(1) if env_match else None
        proposed_actions.append({
            "action": "RECORD_EFILING_RECEIPT",
            "description": f"Attach Odyssey E-Filing Acceptance Receipt to Case #{primary_case or 'Docket'}",
        })

    elif any(k in combined_lower for k in ["discovery", "39.14", "michael morton", "offense report"]):
        category = "DA_DISCOVERY"
        proposed_actions.append({
            "action": "UPDATE_MORTON_DISCOVERY",
            "description": f"Update Michael Morton Act discovery compliance checklist for Case #{primary_case or 'Active'}",
        })

    # Confidence calculation
    confidence = 0.3
    if primary_case:
        confidence += 0.35
    if matched_court:
        confidence += 0.20
    if category != "UNCATEGORIZED":
        confidence += 0.15

    return {
        "primary_case_number": primary_case,
        "all_case_numbers": list(dict.fromkeys(cases_found)),
        "court": matched_court,
        "judge": matched_judge,
        "defendant_name": defendant_name,
        "category": category,
        "specialized_fields": specialized_fields,
        "proposed_actions": proposed_actions,
        "confidence": round(min(confidence, 1.0), 2),
        "requires_human_verification": True,  # Non-negotiable domain rule
    }
