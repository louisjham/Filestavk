"""
Michael Morton Act (Art. 39.14 CCP) "Red Ink" Discovery Gap Auditor.

Scans offense reports, narrative supplements, and probable cause affidavits for
referenced evidence (BWCs, dashcams, CAD logs, 911 calls, DPS lab reports, witness statements)
and cross-references against the State's cataloged production to identify missing items and
constitutional/statutory suppression triggers.
"""

import re
import json
from datetime import datetime, timezone, date
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.case import Case
from app.models.client import Client
from app.models.document import Document
from app.services.citation_service import citation_service


class DiscoveryAuditService:
    """Automated Discovery Gap & Procedural Compliance Engine for Texas Criminal Defense."""

    async def audit_case_discovery(self, db: AsyncSession, case_id: int) -> Dict[str, Any]:
        """
        Executes a deep evidentiary audit across all ingested documents for a case.
        Detects missing items under Art. 39.14 CCP and suppression triggers under Arts. 38.22 & 38.23 CCP.
        """
        # 1. Fetch Case & Client
        case_res = await db.execute(select(Case).where(Case.id == case_id))
        case = case_res.scalars().first()
        if not case:
            return {"error": f"Case ID {case_id} not found", "success": False}

        client_name = "Defendant"
        if case.client_id:
            cl_res = await db.execute(select(Client).where(Client.id == case.client_id))
            client = cl_res.scalars().first()
            if client and client.name:
                client_name = client.name

        # 2. Fetch all case documents
        docs_res = await db.execute(select(Document).where(Document.case_id == case_id))
        documents = docs_res.scalars().all()

        # Segregate offense narrative texts vs. cataloged discovery productions
        narrative_texts = []
        narrative_texts = []
        production_filenames = []
        production_text = ""

        for doc in documents:
            filename = doc.filename or ""
            fn_lower = filename.lower()
            text = doc.content_text or ""
            label = (doc.classification_label or "").lower()
            dtype = (doc.doc_type or "").lower()

            is_narrative = (
                any(k in label for k in ["police_report", "offense_narrative", "incident", "affidavit"]) or
                any(k in fn_lower for k in ["offense", "narrative", "incident", "arrest", "pc_affidavit", "report"])
            )

            if is_narrative:
                narrative_texts.append({"filename": filename, "text": text})
            else:
                production_filenames.append(fn_lower)
                production_text += f"\n{filename}\n{text}"

        # Also inspect existing morton_discovery_json if present
        existing_inventory = []
        if case.morton_discovery_json:
            try:
                parsed_inv = json.loads(case.morton_discovery_json)
                if isinstance(parsed_inv, list):
                    existing_inventory = parsed_inv
                elif isinstance(parsed_inv, dict):
                    existing_inventory = parsed_inv.get("inventory", [])
            except Exception:
                pass

        # 3. Evidence Extraction from Narratives
        mentioned_items: List[Dict[str, Any]] = []
        suppression_flags: List[Dict[str, Any]] = []

        combined_narrative = "\n".join([n["text"] for n in narrative_texts])

        # If no dedicated narrative file was categorized, inspect all available case text
        if not combined_narrative.strip():
            combined_narrative = produced_full_text

        # --- A. Body-Worn Camera (BWC) Scans ---
        bwc_matches = re.finditer(
            r'(?:BWC|body[-\s]?worn\s*camera|body\s*cam(?:era)?|Axon|camera)\s*(?:#|no\.?|num\.?|unit)?\s*([A-Za-z0-9\-_]{1,15})?',
            combined_narrative,
            re.IGNORECASE
        )
        for m in bwc_matches:
            tag = m.group(0).strip()
            num = m.group(1).strip() if m.group(1) else ""
            item_title = f"Body-Worn Camera Footage ({tag})"
            snippet = self._extract_snippet(combined_narrative, m.start(), m.end())
            self._record_item(mentioned_items, "BWC_FOOTAGE", item_title, snippet, "Art. 39.14(a) CCP")

        # --- B. In-Car / Dashcam Scans ---
        dash_matches = re.finditer(
            r'(?:in[-\s]?car\s*(?:video|camera)|dash[-\s]?cam|patrol\s*car\s*camera|unit\s*\d+\s*video)',
            combined_narrative,
            re.IGNORECASE
        )
        for m in dash_matches:
            snippet = self._extract_snippet(combined_narrative, m.start(), m.end())
            self._record_item(mentioned_items, "DASHCAM_VIDEO", f"In-Car Dashcam Video ({m.group(0)})", snippet, "Art. 39.14(a) CCP")

        # --- C. 911 Calls & CAD Dispatch Audio ---
        cad_matches = re.finditer(
            r'(?:911\s*call(?:er|ing)?|CAD\s*(?:log|dispatch|call)|radio\s*(?:traffic|transmission)|dispatch\s*recording)',
            combined_narrative,
            re.IGNORECASE
        )
        for m in cad_matches:
            snippet = self._extract_snippet(combined_narrative, m.start(), m.end())
            self._record_item(mentioned_items, "CAD_911_AUDIO", f"911 Audio & CAD Dispatch Records ({m.group(0)})", snippet, "Art. 39.14(a) CCP")

        # --- D. DPS Crime Lab & Toxicology ---
        lab_matches = re.finditer(
            r'(?:DPS\s*(?:lab|crime\s*lab(?:oratory)?)|toxicology\s*report|blood\s*(?:draw|specimen|vial)|chemical\s*analysis|intoxilyzer\s*(?:9000|5000)?|ballistics\s*report|controlled\s*substance\s*analysis)',
            combined_narrative,
            re.IGNORECASE
        )
        for m in lab_matches:
            snippet = self._extract_snippet(combined_narrative, m.start(), m.end())
            self._record_item(mentioned_items, "FORENSIC_LAB_REPORT", f"DPS Forensic Crime Lab Report ({m.group(0)})", snippet, "Art. 39.14(a) & Brady v. Maryland")

        # --- E. Witness Statements ---
        stmt_matches = re.finditer(
            r'(?:witness\s*(?:statement|interview)|victim\s*(?:statement|interview)|voluntary\s*statement\s*form|written\s*statement)',
            combined_narrative,
            re.IGNORECASE
        )
        for m in stmt_matches:
            snippet = self._extract_snippet(combined_narrative, m.start(), m.end())
            self._record_item(mentioned_items, "WITNESS_STATEMENT", f"Written/Recorded Witness Statement ({m.group(0)})", snippet, "Art. 39.14(a) CCP")

        # --- F. Suppression Trigger Scans ---
        # 1. Art. 38.22 Custodial Interrogation Check
        custody_q_match = re.search(
            r'(?:handcuffed|placed\s+in\s+the\s+back|seated\s+in\s+patrol|transported\s+to\s+jail|under\s+arrest)[\s\S]{0,200}?(?:admitted|confessed|stated|asked\s+him|interrogated|questioned)',
            combined_narrative,
            re.IGNORECASE
        )
        if custody_q_match:
            snippet = self._extract_snippet(combined_narrative, custody_q_match.start(), custody_q_match.end())
            has_recorded_statement = any("audio" in f or "video" in f or "interview" in f for f in production_filenames)
            if not has_recorded_statement:
                suppression_flags.append({
                    "id": "suppress_38_22",
                    "basis": "Tex. Code Crim. Proc. art. 38.22 § 3",
                    "title": "Unrecorded Custodial Statement (Art. 38.22 CCP)",
                    "severity": "CRITICAL",
                    "description": "Narrative indicates defendant made statements while in custody/handcuffs, but no electronic audio-visual recording is cataloged in discovery.",
                    "snippet": snippet,
                    "recommended_motion": "Motion to Suppress Custodial Oral Statements under Art. 38.22 § 3 CCP",
                })

        # 2. Art. 38.23 Warrantless Search Check
        warrantless_match = re.search(
            r'(?:searched\s+the\s+vehicle|searched\s+the\s+trunk|searched\s+the\s+residence|conducted\s+a\s+search)[\s\S]{0,150}?(?:located|found|seized|discovered)',
            combined_narrative,
            re.IGNORECASE
        )
        if warrantless_match:
            snippet = self._extract_snippet(combined_narrative, warrantless_match.start(), warrantless_match.end())
            has_warrant = "search warrant" in combined_narrative.lower() or "consent to search" in combined_narrative.lower()
            if not has_warrant:
                suppression_flags.append({
                    "id": "suppress_38_23",
                    "basis": "Tex. Code Crim. Proc. art. 38.23 & 4th Amend.",
                    "title": "Warrantless Search Lacking Documented Exception",
                    "severity": "HIGH",
                    "description": "Narrative documents a search and seizure of evidence without citing a search warrant or documented written/recorded consent.",
                    "snippet": snippet,
                    "recommended_motion": "Motion to Suppress Evidence Seized Without Warrant under Art. 38.23 CCP",
                })

        # 3. Art. 17.151 Speedy Indictment Clock
        clock_status = None
        if case.in_custody and case.jail_booking_date:
            try:
                booking_dt = datetime.strptime(case.jail_booking_date[:10], "%Y-%m-%d").date()
                days_in_jail = (date.today() - booking_dt).days
                is_felony = "felony" in (case.charge_description or "").lower() or "cr" in (case.case_number or "").lower()
                statutory_cap = 90 if is_felony else 30

                days_remaining = statutory_cap - days_in_jail
                clock_status = {
                    "days_in_custody": days_in_jail,
                    "statutory_cap_days": statutory_cap,
                    "days_remaining": days_remaining,
                    "is_past_deadline": days_remaining <= 0,
                    "statutory_basis": "Tex. Code Crim. Proc. art. 17.151",
                }

                if days_remaining <= 15:
                    suppression_flags.append({
                        "id": "art_17_151_clock",
                        "basis": "Tex. Code Crim. Proc. art. 17.151",
                        "title": f"Art. 17.151 In-Custody Speedy Release Clock ({days_in_jail}/{statutory_cap} Days)",
                        "severity": "CRITICAL" if days_remaining <= 0 else "WARNING",
                        "description": f"Client has been incarcerated in Nueces County Jail for {days_in_jail} days. Under Art. 17.151 CCP, state unreadiness mandates personal bond or bail reduction.",
                        "snippet": f"Booked: {case.jail_booking_date}. Incarcerated: {days_in_jail} days. Cap: {statutory_cap} days.",
                        "recommended_motion": "Application for Writ of Habeas Corpus / Motion for Release on Personal Bond Under Art. 17.151 CCP",
                    })
            except Exception:
                pass

        # 4. Cross-Reference: Produced vs. Missing Discovery
        missing_items: List[Dict[str, Any]] = []
        produced_items: List[Dict[str, Any]] = []

        prod_text_lower = production_text.lower()

        for item in mentioned_items:
            cat = item["category"]
            name = item["name"].lower()

            # Check if matching media or document exists in produced files or inventory
            is_found = False
            for pf in production_filenames:
                if cat == "BWC_FOOTAGE" and any(k in pf for k in ["bwc", "body_cam", "bodycam", "axon", ".mp4", ".mov", ".avi"]):
                    is_found = True
                    break
                elif cat == "DASHCAM_VIDEO" and any(k in pf for k in ["dash", "in-car", "incar", ".mp4", ".mov", ".avi"]):
                    is_found = True
                    break
                elif cat == "CAD_911_AUDIO" and any(k in pf for k in ["911", "cad", "audio", ".wav", ".mp3"]):
                    is_found = True
                    break
                elif cat == "FORENSIC_LAB_REPORT" and any(k in pf for k in ["lab", "tox", "dps", "analysis", "chemist", "ballistics"]):
                    is_found = True
                    break
                elif cat == "WITNESS_STATEMENT" and any(k in pf for k in ["witness", "statement", "interview"]):
                    is_found = True
                    break

            # If not in filenames, check if state's written discovery receipt / inventory explicitly lists it
            if not is_found and prod_text_lower:
                if cat == "BWC_FOOTAGE" and any(k in prod_text_lower for k in ["bwc produced", "body camera produced", "axon video provided"]):
                    is_found = True
                elif cat == "DASHCAM_VIDEO" and any(k in prod_text_lower for k in ["dashcam produced", "in-car video provided"]):
                    is_found = True
                elif cat == "CAD_911_AUDIO" and any(k in prod_text_lower for k in ["911 audio produced", "cad log provided"]):
                    is_found = True
                elif cat == "FORENSIC_LAB_REPORT" and any(k in prod_text_lower for k in ["dps lab report attached", "toxicology results provided"]):
                    is_found = True

            # Also check existing inventory list
            if not is_found:
                for inv_item in existing_inventory:
                    if isinstance(inv_item, str) and (name in inv_item.lower() or cat.lower() in inv_item.lower()):
                        is_found = True
                        break
                    elif isinstance(inv_item, dict) and inv_item.get("status") == "PRODUCED":
                        if cat.lower() in str(inv_item).lower():
                            is_found = True
                            break

            if is_found:
                item["status"] = "PRODUCED"
                produced_items.append(item)
            else:
                item["status"] = "MISSING_FROM_DISCOVERY"
                item["severity"] = "CRITICAL"
                item["recommended_action"] = "Include in Art. 39.14 Motion to Compel Open-File Discovery"
                missing_items.append(item)

        # 5. Build Audit Report Payload
        audit_report = {
            "case_id": case.id,
            "case_number": case.case_number,
            "court": case.court or "Nueces County District Court",
            "judge": case.judge or "Presiding Judge",
            "defendant_name": client_name,
            "charge": case.charge_description or "Criminal Offense",
            "audit_timestamp": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "total_items_mentioned": len(mentioned_items),
                "produced_count": len(produced_items),
                "missing_count": len(missing_items),
                "suppression_flags_count": len(suppression_flags),
                "compliance_status": "DEFICIENT" if missing_items else "SATISFACTORY",
            },
            "missing_evidence": missing_items,
            "produced_evidence": produced_items,
            "suppression_flags": suppression_flags,
            "statutory_clock": clock_status,
        }

        # Save audit report back to Case model
        case.morton_discovery_json = json.dumps(audit_report, ensure_ascii=False)
        await db.commit()

        return audit_report

    def generate_motion_to_compel(self, audit_report: Dict[str, Any]) -> str:
        """
        Generates a formal, file-ready Texas legal motion:
        'DEFENDANT'S NOTICE OF DISCOVERY DEFICIT & MOTION TO COMPEL PRODUCTION UNDER ART. 39.14 CCP'
        """
        case_num = audit_report.get("case_number", "[CAUSE NO.]")
        court = audit_report.get("court", "DISTRICT COURT OF NUECES COUNTY, TEXAS")
        def_name = audit_report.get("defendant_name", "DEFENDANT")
        charge = audit_report.get("charge", "CRIMINAL OFFENSE")
        missing = audit_report.get("missing_evidence", [])
        suppression = audit_report.get("suppression_flags", [])

        items_formatted = ""
        for idx, it in enumerate(missing, 1):
            items_formatted += f"    {idx}. {it.get('name')}\n"
            items_formatted += f"       Statutory Basis: {it.get('statutory_basis')}\n"
            items_formatted += f"       Reference in Offense Narrative: \"{it.get('snippet', '').strip()}\"\n\n"

        suppress_formatted = ""
        if suppression:
            suppress_formatted += "\nIII. PROCEDURAL & STATUTORY SUPPRESSION GROUNDS\n"
            for s in suppression:
                suppress_formatted += f"- {s.get('title')} ({s.get('basis')}):\n"
                suppress_formatted += f"  {s.get('description')}\n"
                suppress_formatted += f"  Factual Snippet: \"{s.get('snippet', '').strip()}\"\n\n"

        pleading_text = f"""CAUSE NO. {case_num}

THE STATE OF TEXAS                    §    IN THE {court.upper()}
VS.                                   §
{def_name.upper()}                    §    NUECES COUNTY, TEXAS

DEFENDANT'S NOTICE OF DISCOVERY DEFICIT AND MOTION TO COMPEL OPEN-FILE
PRODUCTION UNDER ARTICLE 39.14, TEXAS CODE OF CRIMINAL PROCEDURE

TO THE HONORABLE JUDGE OF SAID COURT:

COMES NOW the Defendant, {def_name}, by and through appointed defense counsel,
Kimbel Brandon, Attorney at Law, and respectfully files this Notice of Discovery Deficit
and Motion to Compel Production pursuant to Article 39.14 of the Texas Code of Criminal
Procedure and the Sixth and Fourteenth Amendments to the United States Constitution,
and in support thereof would show the Court the following:

                               I. STATUTORY BASIS
1. Under Article 39.14(a) of the Texas Code of Criminal Procedure (The Michael Morton Act),
   as soon as practicable after receiving a timely request from the defendant, the State
   SHALL produce and permit the inspection, electronic duplication, copying, and photographing
   of any offense reports, books, accounts, letters, photographs, electronic recordings,
   witness statements, and tangible items in the possession, custody, or control of the State.

2. In Watkins v. State, 619 S.W.3d 265 (Tex. Crim. App. 2021), the Texas Court of Criminal
   Appeals affirmed that Article 39.14 creates an affirmative, continuous statutory duty upon
   the prosecution to produce open-file discovery and exculpatory evidence without requiring
   the defense to demonstrate good cause.

                      II. SPECIFIC DISCOVERY DEFICITS
3. A comprehensive audit of the State's production and law enforcement narratives reveals
   that the following material items are explicitly referenced in police narratives or
   chain of custody records, yet REMAIN UNPRODUCED by the State:

{items_formatted if items_formatted else "    (No specific missing digital items identified)\n"}
{suppress_formatted}
                                 IV. PRAYER
WHEREFORE, PREMISES CONSIDERED, Defendant respectfully prays that this Court enter an Order
directing the State to immediately disclose and produce all unproduced items enumerated above,
and upon failure to do so, to prohibit the State from introducing any testimony or evidence
derived therefrom pursuant to Article 39.14 and Article 38.23 of the Texas Code of Criminal Procedure.

                                        Respectfully submitted,

                                        /s/ Kimbel Brandon
                                        KIMBEL BRANDON
                                        State Bar No. 24079543
                                        HEMOCYANIN LAW
                                        Corpus Christi, Nueces County, Texas
                                        Attorney for Defendant

                           CERTIFICATE OF SERVICE
I hereby certify that a true and correct copy of the above and foregoing Motion has been served
upon the Nueces County District Attorney's Office via electronic filing / Tyler Technologies E-File
service on this {date.today().strftime('%B %d, %Y')}.

                                        /s/ Kimbel Brandon
                                        Kimbel Brandon
"""
        return pleading_text

    def _record_item(self, target_list: List[Dict[str, Any]], category: str, name: str, snippet: str, basis: str):
        """Helper to deduplicate and record extracted evidence items."""
        for existing in target_list:
            if existing["category"] == category and existing["name"] == name:
                return
        target_list.append({
            "category": category,
            "name": name,
            "snippet": snippet,
            "statutory_basis": basis,
        })

    def _extract_snippet(self, text: str, start: int, end: int, window: int = 80) -> str:
        """Extracts a readable surrounding sentence/context window."""
        left = max(0, start - window)
        right = min(len(text), end + window)
        snippet = text[left:right].replace("\n", " ").strip()
        return f"...{snippet}..."


# Singleton service instance
discovery_audit_service = DiscoveryAuditService()
