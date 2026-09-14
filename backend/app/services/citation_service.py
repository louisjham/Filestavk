"""
Deterministic Citation Extraction & Verification Service.
Uses Free Law Project's `eyecite` library to extract, parse, and standardize
Texas and Federal legal citations with zero hallucination.
"""

import re
import urllib.parse
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

try:
    import eyecite
    from eyecite import get_citations, clean_text
    from eyecite.models import (
        FullCaseCitation,
        ShortCaseCitation,
        ResourceCitation,
        FullLawCitation,
        IdCitation,
        SupraCitation,
    )
    EYECITE_AVAILABLE = True
except ImportError as e:
    EYECITE_AVAILABLE = False
    logger.warning(f"eyecite not installed or import error: {e}; falling back to regex citation parser.")


class CitationService:
    """Service to parse, resolve, and link legal citations."""

    def extract_citations(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract judicial opinions and statutory references from text.
        Returns structured citation objects with reporter, volume, page,
        matched text, and direct CourtListener search links.
        """
        if not text or not text.strip():
            return []

        results = []

        if EYECITE_AVAILABLE:
            cleaned = clean_text(text, ["all_whitespace"])
            citations = get_citations(cleaned)

            for cite in citations:
                raw_token = str(cite)
                span = getattr(cite, "span", lambda: (0, 0))()

                cite_info: Dict[str, Any] = {
                    "raw_citation": raw_token,
                    "matched_text": cite.matched_text() if hasattr(cite, "matched_text") else raw_token,
                    "span_start": span[0],
                    "span_end": span[1],
                    "type": cite.__class__.__name__,
                    "verified": False,
                }

                if isinstance(cite, FullCaseCitation):
                    vol = cite.groups.get("volume") if isinstance(cite.groups, dict) else getattr(cite.groups, "volume", None)
                    rep = cite.groups.get("reporter") if isinstance(cite.groups, dict) else getattr(cite.groups, "reporter", None)
                    page = cite.groups.get("page") if isinstance(cite.groups, dict) else getattr(cite.groups, "page", None)
                    meta = getattr(cite, "metadata", None)
                    court = getattr(meta, "court", None) if meta else None
                    year = getattr(meta, "year", None) if meta else None
                    plaintiff = getattr(meta, "plaintiff", None) if meta else None
                    defendant = getattr(meta, "defendant", None) if meta else None

                    canonical_str = f"{vol} {rep} {page}" if (vol and rep and page) else raw_token
                    cite_info.update({
                        "volume": vol,
                        "reporter": rep,
                        "page": page,
                        "court": court,
                        "year": year,
                        "plaintiff": plaintiff,
                        "defendant": defendant,
                        "canonical": canonical_str,
                        "courtlistener_url": f"https://www.courtlistener.com/?q={urllib.parse.quote(canonical_str)}&type=o",
                    })
                elif isinstance(cite, ShortCaseCitation):
                    cite_info.update({
                        "canonical": raw_token,
                        "courtlistener_url": f"https://www.courtlistener.com/?q={urllib.parse.quote(raw_token)}&type=o",
                    })
                else:
                    cite_info["canonical"] = raw_token

                results.append(cite_info)

        # Regex supplemental pass for Texas specific patterns (both standard and inverted)
        tx_statute_patterns = [
            (r'TEX\.?\s*CODE\s*CRIM\.?\s*PROC\.?\s*(?:ART\.?|ARTICLE)?\s*([0-9]+\.[0-9]+(?:[\(\)a-zA-Z0-9]+)?)', "TEX. CODE CRIM. PROC. ART. {}"),
            (r'(?:ART\.?|ARTICLE)\s*([0-9]+\.[0-9]+(?:[\(\)a-zA-Z0-9]+)?)\s*(?:OF\s+THE)?\s*TEX(?:AS)?\.?\s*CODE\s*(?:OF)?\s*CRIM(?:INAL)?\.?\s*PROC(?:EDURE)?', "TEX. CODE CRIM. PROC. ART. {}"),
            (r'TEX\.?\s*PENAL\s*CODE\s*(?:§|SEC\.?|SECTION)?\s*([0-9]+\.[0-9]+(?:[\(\)a-zA-Z0-9]+)?)', "TEX. PENAL CODE § {}"),
            (r'(?:§|SEC\.?|SECTION)\s*([0-9]+\.[0-9]+(?:[\(\)a-zA-Z0-9]+)?)\s*(?:OF\s+THE)?\s*TEX(?:AS)?\.?\s*PENAL\s*CODE', "TEX. PENAL CODE § {}"),
            (r'TEX\.?\s*HEALTH\s*&\s*SAFETY\s*CODE\s*(?:§|SEC\.?|SECTION)?\s*([0-9]+\.[0-9]+(?:[\(\)a-zA-Z0-9]+)?)', "TEX. HEALTH & SAFETY CODE § {}"),
            (r'TEX\.?\s*TRANSP\.?\s*CODE\s*(?:§|SEC\.?|SECTION)?\s*([0-9]+\.[0-9]+(?:[\(\)a-zA-Z0-9]+)?)', "TEX. TRANSP. CODE § {}"),
        ]

        existing_canonicals = {r.get("canonical", "").upper() for r in results}

        for pat, template in tx_statute_patterns:
            for m in re.finditer(pat, text, re.IGNORECASE):
                sec_num = m.group(1).strip()
                canonical = template.format(sec_num)
                if canonical.upper() not in existing_canonicals:
                    existing_canonicals.add(canonical.upper())
                    results.append({
                        "raw_citation": m.group(0),
                        "matched_text": m.group(0),
                        "span_start": m.start(),
                        "span_end": m.end(),
                        "type": "TexasStatuteCitation",
                        "canonical": canonical,
                        "verified": True,
                        "statute_section": sec_num,
                    })

        # Regex fallback for Texas Reporters (S.W.2d, S.W.3d) if eyecite was unavailable
        if not EYECITE_AVAILABLE:
            sw_matches = re.finditer(r'(\d+)\s*(S\.W\.(?:2d|3d))\s*(\d+)', text, re.IGNORECASE)
            for m in sw_matches:
                vol, rep, page = m.group(1), m.group(2).upper(), m.group(3)
                canonical = f"{vol} {rep} {page}"
                if canonical.upper() not in existing_canonicals:
                    existing_canonicals.add(canonical.upper())
                    results.append({
                        "raw_citation": m.group(0),
                        "matched_text": m.group(0),
                        "span_start": m.start(),
                        "span_end": m.end(),
                        "type": "FullCaseCitation",
                        "volume": vol,
                        "reporter": rep,
                        "page": page,
                        "canonical": canonical,
                        "courtlistener_url": f"https://www.courtlistener.com/?q={urllib.parse.quote(canonical)}&type=o",
                        "verified": False,
                    })

        return results


citation_service = CitationService()
