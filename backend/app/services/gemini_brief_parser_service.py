"""
Deterministic Parser for Kimbel Brandon's Gemini 10-Day Deep-Dive Brief.
Parses court dockets, critical deadlines, case updates, waivers of arraignment,
and appellate orders into structured database proposals.
"""

import re
from typing import Dict, Any, List, Optional
from datetime import datetime

class GeminiBriefParserService:
    """Parses raw markdown text from Kimbel's Gemini 10-Day Criminal Defense Gem."""

    def parse_brief(self, raw_text: str) -> Dict[str, Any]:
        """
        Parses the full markdown brief into categorized, structured proposals
        ready for the Human Verification Board.
        """
        raw_text = raw_text.strip()

        # Normalize concatenated headers where no newline exists between header and content
        raw_text = re.sub(r"(Section \d+:[^\n]*?\))\s*(\d{4}-\d{2}-\d{2}|\[|Client:|No )", r"\1\n\2", raw_text, flags=re.IGNORECASE)
        raw_text = re.sub(r"(Docket Conflict Note:[^\n]*?\.)\s*(\d{4}-\d{2}-\d{2}|\[|Client:|Section)", r"\1\n\2", raw_text, flags=re.IGNORECASE)
        raw_text = re.sub(r"(Overview[^\n]*?:)\s*(Cause #)", r"\1\n\2", raw_text, flags=re.IGNORECASE)
        raw_text = re.sub(r"(Work Completed[^\n]*?\))\s*(Detailed Summary:)", r"\1\n\2", raw_text, flags=re.IGNORECASE)

        # Split into main sections
        sections = self._split_sections(raw_text)

        hearings = self._parse_section_1(sections.get("section_1", ""))
        conflicts = self._parse_conflicts(sections.get("section_1", ""))
        critical_deadlines = self._parse_section_2(sections.get("section_2", ""))
        case_updates = self._parse_section_3(sections.get("section_3", ""))
        vouchers = self._parse_section_4(sections.get("section_4", ""))
        appellate_orders = self._parse_forwarded_section(sections.get("forwarded", ""))

        # Combine into unified proposal items for verification board
        proposals = []

        # 1. Hearings / Court settings
        for h in hearings:
            has_conflict = any(h["client_name"].lower() in c.lower() for c in conflicts)
            proposals.append({
                "category": "COURT_HEARING",
                "badge": "Court Hearing",
                "title": f"Hearing: {h['client_name']} ({h['purpose']})",
                "case_number": h["case_number"],
                "client_name": h["client_name"],
                "court": h["court"],
                "judge": self._infer_judge(h["court"]),
                "event_date": h["event_date"],
                "event_time": h["event_time"],
                "details": f"{h['purpose']} scheduled in {h['court']}. {h.get('conflict_note', '')}".strip(),
                "action_type": "SCHEDULE_EVENT",
                "source_link": h.get("source_link"),
                "has_conflict": has_conflict or bool(h.get("conflict_note")),
                "conflict_note": h.get("conflict_note") or (conflicts[0] if has_conflict else None),
                "confidence": 1.0 if h["case_number"] != "Cause # Not Provided" else 0.85,
                "source_snippet": h["raw_line"]
            })

        # 2. Critical deadlines / new appointments
        for d in critical_deadlines:
            proposals.append({
                "category": "CRITICAL_DEADLINE",
                "badge": "New Appt / In-Jail Clock" if d.get("in_custody") else "Critical Deadline",
                "title": d["title"],
                "case_number": d["case_number"],
                "client_name": d["client_name"],
                "court": d["court"],
                "judge": self._infer_judge(d["court"]),
                "charge": d.get("charge"),
                "in_custody": d.get("in_custody", False),
                "event_date": d.get("appointment_date") or datetime.now().strftime("%Y-%m-%d"),
                "details": d["details"],
                "proposed_action": d.get("proposed_action"),
                "statutory_basis": d.get("statutory_basis"),
                "action_type": "CREATE_OR_UPDATE_CASE",
                "stage": "APPOINTED" if "appointment" in d["title"].lower() else "DISCOVERY",
                "source_link": d.get("source_link"),
                "confidence": 0.98,
                "source_snippet": d["raw_block"]
            })

        # 3. Case updates & Waivers of Arraignment
        for u in case_updates:
            is_waiver = "waiver of arraignment" in u["details"].lower()
            is_appt = "order of appointment" in u["details"].lower()
            stage = "PRE_TRIAL" if is_waiver else ("APPOINTED" if is_appt else "DISCOVERY")

            proposals.append({
                "category": "CASE_UPDATE",
                "badge": "Waiver of Arraignment" if is_waiver else ("New Appointment" if is_appt else "Discovery Update"),
                "title": f"{'Waiver of Arraignment Filed' if is_waiver else 'Case Update'}: {u['client_name']}",
                "case_number": u["case_number"],
                "client_name": u["client_name"],
                "court": u["court"],
                "judge": self._infer_judge(u["court"]),
                "details": u["details"],
                "action_type": "RECORD_WAIVER" if is_waiver else "UPDATE_CASE",
                "stage": stage,
                "plea": "NOT_GUILTY" if is_waiver else None,
                "source_link": u.get("source_link"),
                "confidence": 0.99,
                "source_snippet": u["raw_block"]
            })

        # 4. Vouchers
        for v in vouchers:
            proposals.append({
                "category": "VOUCHER_STATUS",
                "badge": f"Voucher: {v['status']}",
                "title": f"Voucher Update: {v['client_name']} ({v['status']})",
                "case_number": v["case_number"],
                "client_name": v["client_name"],
                "court": v.get("court", "Nueces County Court"),
                "judge": self._infer_judge(v.get("court", "")),
                "amount": v.get("amount"),
                "warrant_number": v.get("warrant_number"),
                "details": f"Status: {v['status']} | Amount: ${v.get('amount', 0):.2f}",
                "action_type": "UPDATE_VOUCHER",
                "source_link": v.get("source_link"),
                "confidence": 0.95,
                "source_snippet": v["raw_line"]
            })

        # 5. Appellate Orders
        for a in appellate_orders:
            proposals.append({
                "category": "APPELLATE_ORDER",
                "badge": "13th Court of Appeals",
                "title": f"COA Order: {a['client_name']} ({a['coa_number'] or a['case_number']})",
                "case_number": a["case_number"],
                "client_name": a["client_name"],
                "court": "13th Court of Appeals",
                "judge": "Chief Justice Dori Contreras",
                "coa_number": a.get("coa_number"),
                "details": a["details"],
                "action_type": "LOG_APPELLATE_EVENT",
                "stage": "APPEAL",
                "source_link": a.get("source_link"),
                "confidence": 0.97,
                "source_snippet": a["raw_block"]
            })

        # Total counts by category
        summary_counts = {
            "total_items": len(proposals),
            "hearings": len(hearings),
            "critical_deadlines": len(critical_deadlines),
            "waivers_of_arraignment": sum(1 for p in proposals if p["badge"] == "Waiver of Arraignment"),
            "case_updates": len(case_updates),
            "appellate_orders": len(appellate_orders),
            "vouchers": len(vouchers),
            "conflicts_detected": len(conflicts),
        }

        return {
            "raw_text": raw_text,
            "parsed_at": datetime.now().isoformat(),
            "summary_counts": summary_counts,
            "conflicts": conflicts,
            "proposals": proposals,
        }

    def _split_sections(self, text: str) -> Dict[str, str]:
        """Splits the brief by its standard section headers."""
        sections = {}
        
        # Patterns for standard headers
        s1_idx = re.search(r"Section 1:\s*Upcoming 10-Day Court Schedule", text, re.IGNORECASE)
        s2_idx = re.search(r"Section 2:\s*High-Priority & Critical Deadlines", text, re.IGNORECASE)
        s3_idx = re.search(r"Section 3:\s*Deep-Dive Case Updates", text, re.IGNORECASE)
        s4_idx = re.search(r"Section 4:\s*Attorney Fee Vouchers", text, re.IGNORECASE)
        s5_idx = re.search(r"Section 5:\s*Active & Overdue Legal Tasks", text, re.IGNORECASE)
        fwd_idx = re.search(r"(?:Forwarded Communications & Attached Documents|Work Completed & Actions Taken)", text, re.IGNORECASE)

        indices = [
            ("section_1", s1_idx.start() if s1_idx else -1),
            ("section_2", s2_idx.start() if s2_idx else -1),
            ("section_3", s3_idx.start() if s3_idx else -1),
            ("section_4", s4_idx.start() if s4_idx else -1),
            ("section_5", s5_idx.start() if s5_idx else -1),
            ("forwarded", fwd_idx.start() if fwd_idx else -1),
        ]
        
        # Filter out missing sections and sort by position
        valid = sorted([item for item in indices if item[1] != -1], key=lambda x: x[1])

        for i, (name, start) in enumerate(valid):
            end = valid[i + 1][1] if i + 1 < len(valid) else len(text)
            sections[name] = text[start:end].strip()

        return sections

    def _parse_section_1(self, section_text: str) -> List[Dict[str, Any]]:
        """Parses Section 1 pipe-delimited calendar entries."""
        hearings = []
        if not section_text:
            return hearings

        lines = section_text.splitlines()
        # Format: 2026-09-14 | 8:30 AM CDT | County Court at Law No. 5 | Aubree Williams | Cause # 2025-FAM-61124-5 | Hearing — [View Event](url)
        entry_pattern = re.compile(
            r"^(\d{4}-\d{2}-\d{2})\s*\|\s*([^\|]+?)\s*\|\s*([^\|]+?)\s*\|\s*([^\|]+?)\s*\|\s*(?:Cause\s*#?\s*)?([^\|]+?)\s*\|\s*(.*?)(?:\s*[—–-]\s*\[View Event\]\(([^\)]+)\))?$",
            re.IGNORECASE
        )

        for line in lines:
            line_clean = line.strip()
            if not line_clean or line_clean.startswith("Section 1:") or line_clean.startswith("Docket Conflict"):
                continue

            m = entry_pattern.match(line_clean)
            if m:
                hearings.append({
                    "event_date": m.group(1).strip(),
                    "event_time": m.group(2).strip(),
                    "court": m.group(3).strip(),
                    "client_name": m.group(4).strip(),
                    "case_number": m.group(5).strip(),
                    "purpose": m.group(6).strip(),
                    "source_link": m.group(7).strip() if m.group(7) else None,
                    "raw_line": line_clean,
                })
            else:
                # Secondary looser pattern if pipe splitting was slightly different
                parts = [p.strip() for p in line_clean.split("|")]
                if len(parts) >= 5 and re.match(r"^\d{4}-\d{2}-\d{2}$", parts[0]):
                    # Link check on last part
                    link_match = re.search(r"\[View Event\]\(([^\)]+)\)", parts[-1])
                    purpose_clean = re.sub(r"[—–-]\s*\[View Event\].*", "", parts[-1]).strip()
                    cause_part = parts[4].replace("Cause #", "").replace("Cause", "").strip()

                    hearings.append({
                        "event_date": parts[0],
                        "event_time": parts[1],
                        "court": parts[2],
                        "client_name": parts[3],
                        "case_number": cause_part or "Cause # Not Provided",
                        "purpose": purpose_clean,
                        "source_link": link_match.group(1) if link_match else None,
                        "raw_line": line_clean,
                    })

        return hearings

    def _parse_conflicts(self, section_text: str) -> List[str]:
        """Detects explicitly noted docket conflicts."""
        conflicts = []
        for line in section_text.splitlines():
            if "Docket Conflict Note:" in line or "Conflicting start times" in line:
                cleaned = line.replace("Docket Conflict Note:", "").strip()
                if cleaned:
                    conflicts.append(cleaned)
        return conflicts

    def _parse_section_2(self, section_text: str) -> List[Dict[str, Any]]:
        """Parses Section 2 High-Priority & Critical Deadlines."""
        items = []
        if not section_text:
            return items

        # Split by '[15 Mins]' or similar bracketed urgency tags
        blocks = re.split(r"(?=\[\s*\d+\s*(?:Mins|Min|Hours|Days)?\s*\])", section_text)

        for block in blocks:
            b_clean = block.strip()
            if not b_clean or b_clean.startswith("Section 2:"):
                continue

            # Header tag: [15 Mins] [Header Title] — [View File](link) Details: ...
            header_match = re.search(
                r"^\[\s*([^\]]+?)\s*\]\s*\[\s*([^\]]+?)\s*\](?:\s*[—–-]\s*\[View File\]\(([^\)]+)\))?\s*Details:\s*(.*)",
                b_clean,
                re.DOTALL | re.IGNORECASE
            )

            if header_match:
                est_time = header_match.group(1).strip()
                title = header_match.group(2).strip()
                link = header_match.group(3).strip() if header_match.group(3) else None
                body_and_action = header_match.group(4).strip()

                # Check for Proposed Action/Draft
                prop_action = None
                action_match = re.search(r"Proposed Action/Draft:\s*[\"']?(.*?)[\"']?$", body_and_action, re.DOTALL | re.IGNORECASE)
                if action_match:
                    prop_action = action_match.group(1).strip()
                    details_text = body_and_action[:action_match.start()].strip()
                else:
                    details_text = body_and_action

                # Extract cause number
                cause_m = re.search(r"Cause\s*#?\s*([A-Za-z0-9\-]+)", details_text, re.IGNORECASE)
                case_number = cause_m.group(1).strip() if cause_m else "Cause # Not Provided"

                # Extract client name from title or details
                client_name = "Unknown Client"
                if "—" in title:
                    client_name = title.split("—")[-1].strip()
                elif "-" in title:
                    client_name = title.split("-")[-1].strip()
                else:
                    client_m = re.search(r"represent\s+([A-Za-z\s]+?)\s*\(", details_text, re.IGNORECASE)
                    if client_m:
                        client_name = client_m.group(1).strip()

                # Extract court
                court = self._extract_court_from_text(details_text)

                # Extract charge
                charge_m = re.search(r"(?:on|charge)\s+([A-Za-z0-9\s/<\-]+?)(?:\.\s*Client|\.\s*Must|$)", details_text, re.IGNORECASE)
                charge = charge_m.group(1).strip() if charge_m else None

                # In Custody flag
                in_custody = bool(re.search(r"\b(?:in\s+jail|in\s+custody)\b", details_text, re.IGNORECASE))

                # Statutory basis
                statutory_basis = None
                if "48 hours" in details_text.lower():
                    statutory_basis = "Tex. Code Crim. Proc. art. 26.04(j)(1)"
                elif "alr" in details_text.lower():
                    statutory_basis = "Tex. Transp. Code § 524.031 (ALR 15-Day)"

                items.append({
                    "est_time": est_time,
                    "title": title,
                    "client_name": client_name,
                    "case_number": case_number,
                    "court": court,
                    "charge": charge,
                    "in_custody": in_custody,
                    "statutory_basis": statutory_basis,
                    "details": details_text,
                    "proposed_action": prop_action,
                    "source_link": link,
                    "raw_block": b_clean
                })

        return items

    def _parse_section_3(self, section_text: str) -> List[Dict[str, Any]]:
        """Parses Section 3 Deep-Dive Case Updates & Discovery."""
        items = []
        if not section_text:
            return items

        # Split by 'Client:'
        blocks = re.split(r"(?=Client:\s*)", section_text)

        for block in blocks:
            b_clean = block.strip()
            if not b_clean or b_clean.startswith("Section 3:"):
                continue

            # Format: Client: [Name] | Cause: [Cause] | Venue: [Court] — [View File](url) Detailed Analysis: ...
            m = re.search(
                r"^Client:\s*([^\|]+?)\s*\|\s*Cause:\s*([^\|]+?)\s*\|\s*Venue:\s*([^—–\n]+?)(?:\s*[—–-]\s*\[View File\]\(([^\)]+)\))?\s*(?:Detailed Analysis:\s*(.*))?$",
                b_clean,
                re.DOTALL | re.IGNORECASE
            )

            if m:
                client_name = m.group(1).strip()
                case_number = m.group(2).strip()
                raw_court = m.group(3).strip()
                link = m.group(4).strip() if m.group(4) else None
                details = m.group(5).strip() if m.group(5) else ""

                court = self._normalize_court(raw_court)

                items.append({
                    "client_name": client_name,
                    "case_number": case_number,
                    "court": court,
                    "details": details,
                    "source_link": link,
                    "raw_block": b_clean
                })

        return items

    def _parse_section_4(self, section_text: str) -> List[Dict[str, Any]]:
        """Parses Section 4 Attorney Fee Vouchers."""
        items = []
        if not section_text or "No attorney fee voucher" in section_text:
            return items

        lines = section_text.splitlines()
        pattern = re.compile(
            r"^\[([^\|]+?)\s*\|\s*(?:Cause\s*#?\s*)?([^\]]+?)\]\s*\|\s*Status:\s*([A-Za-z]+)\s*\|\s*Amount:\s*\$?([\d,]+(?:\.\d{2})?)(?:\s*[—–-]\s*\[View Email\]\(([^\)]+)\))?",
            re.IGNORECASE
        )

        for line in lines:
            line_clean = line.strip()
            m = pattern.search(line_clean)
            if m:
                items.append({
                    "client_name": m.group(1).strip(),
                    "case_number": m.group(2).strip(),
                    "status": m.group(3).strip().upper(),
                    "amount": float(m.group(4).replace(",", "")),
                    "source_link": m.group(5).strip() if m.group(5) else None,
                    "raw_line": line_clean
                })

        return items

    def _parse_forwarded_section(self, section_text: str) -> List[Dict[str, Any]]:
        """Parses Forwarded Communications & Attached Documents Overview (Appellate Orders, etc.)."""
        items = []
        if not section_text:
            return items

        # Find entries matching: Cause # 24FC-4327B (State v. Jesus R. Salazar / COA # 13-25-00436-CR): ...
        blocks = re.findall(
            r"Cause\s*#\s*([A-Za-z0-9\-\s&]+?)\s*\((?:State v\.\s*)?([^\)]+?)\):\s*(.*?)(?=(?:Cause\s*#|Work Completed|$))",
            section_text,
            re.DOTALL | re.IGNORECASE
        )

        for cause_raw, client_and_coa, details in blocks:
            # Check for COA number inside parentheses
            coa_number = None
            client_name = client_and_coa.strip()
            if "/" in client_and_coa:
                parts = client_and_coa.split("/")
                client_name = parts[0].strip()
                coa_m = re.search(r"COA\s*#?\s*([A-Za-z0-9\-]+)", parts[1], re.IGNORECASE)
                if coa_m:
                    coa_number = coa_m.group(1).strip()

            cause_numbers = [c.strip() for c in re.split(r"[&,]", cause_raw) if c.strip()]
            primary_cause = cause_numbers[0] if cause_numbers else "Cause # Not Provided"

            items.append({
                "case_number": primary_cause,
                "all_causes": cause_numbers,
                "client_name": client_name,
                "coa_number": coa_number,
                "details": details.strip(),
                "raw_block": f"Cause # {cause_raw} ({client_and_coa}): {details.strip()}"
            })

        return items

    def _normalize_court(self, raw_court: str) -> str:
        """Standardizes court names to formal Nueces County venues."""
        c = raw_court.lower()
        if "347th" in c:
            return "347th District Court"
        if "105th" in c:
            return "105th District Court"
        if "117th" in c:
            return "117th District Court"
        if "214th" in c:
            return "214th District Court"
        if "94th" in c:
            return "94th District Court"
        if "28th" in c:
            return "28th District Court"
        if "148th" in c:
            return "148th District Court"
        if "319th" in c:
            return "319th District Court"
        if "county court at law no. 1" in c or "ccl #1" in c or "cc #1" in c:
            return "County Court at Law No. 1"
        if "county court at law no. 2" in c or "ccl #2" in c or "cc #2" in c:
            return "County Court at Law No. 2"
        if "county court at law no. 3" in c or "ccl #3" in c or "cc #3" in c:
            return "County Court at Law No. 3"
        if "county court at law no. 4" in c or "ccl #4" in c or "cc #4" in c:
            return "County Court at Law No. 4"
        if "county court at law no. 5" in c or "ccl #5" in c or "cc #5" in c:
            return "County Court at Law No. 5"
        if "13th" in c or "appeals" in c:
            return "13th Court of Appeals"
        if "district court" in c:
            return "Nueces County District Court"
        return raw_court.strip()

    def _extract_court_from_text(self, text: str) -> str:
        """Extracts court from unstructured sentence text."""
        if re.search(r"\b(?:13th|thirteenth|court\s+of\s+appeals|coa|supreme\s+judicial)\b", text, re.IGNORECASE):
            return "13th Court of Appeals (Corpus Christi - Edinburg)"
        m = re.search(r"(\d{1,3}(?:st|nd|rd|th)\s+District\s+Court|County\s+Court\s+at\s+Law\s+No\.?\s*\d+|13th\s+Court\s+of\s+Appeals|CC\s*#\s*\d+|CCL\s*#\s*\d+)", text, re.IGNORECASE)
        if m:
            return self._normalize_court(m.group(1))
        return "Nueces County Court"

    def _infer_judge(self, court_name: str) -> str:
        """Maps Nueces County court venues to presiding judges."""
        c = court_name.lower()
        if "28th" in c:
            return "Hon. Nanette Hasette"
        if "94th" in c:
            return "Hon. Bobby Galvan"
        if "105th" in c:
            return "Hon. Jack W. Pulcher"
        if "117th" in c:
            return "Hon. Sandra Watts"
        if "148th" in c:
            return "Hon. Carlos Valdez"
        if "214th" in c:
            return "Hon. Inna Klein"
        if "319th" in c:
            return "Hon. David Stith"
        if "347th" in c:
            return "Hon. Missy Medary"
        if "law no. 1" in c:
            return "Hon. Robert J. Vargas"
        if "law no. 2" in c:
            return "Hon. Melissa Madrigal"
        if "law no. 3" in c:
            return "Hon. Deeanne Galvan"
        if "law no. 4" in c:
            return "Hon. Mark Skurka"
        if "law no. 5" in c:
            return "Hon. Timothy McCoy"
        if "13th" in c or "appeal" in c:
            return "Kathy S. Mills, Clerk"
        return "Hon. Presiding Judge"


# Singleton instance
gemini_brief_parser_service = GeminiBriefParserService()
