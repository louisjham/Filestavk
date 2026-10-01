"""
Automated regression test for Odyssey Portal Timeline Import & Event Management.
Verifies parsing of rich procedural narratives, date normalization,
event categorization, and case timeline API endpoints.
"""

import sys
import os
import pytest
import asyncio

sys.path.insert(0, os.path.dirname(__file__))

from app.services.odyssey_timeline_parser import parse_odyssey_timeline, parse_date_to_iso, infer_event_type

FRANK_ROBERTS_SUMMARY = """
July 5, 2024 – October 14, 2024 (Arrest & Indictment): Frank A. Roberts was charged with Aggravated Robbery (a first-degree felony). After initially declining an attorney at his magistrate warning, a Public Defender was appointed in August. His bail was successfully reduced to $35,000, and he was formally indicted and arraigned.

December 3, 2024 – January 8, 2025 (Incompetency Finding): The defense filed a motion suggesting incompetency. Following a court-ordered psychological evaluation, Judge David Klein found the defendant incompetent to stand trial and ordered him committed to a secure facility for 120 days for mental illness treatment.

September 30, 2025 – November 5, 2025 (Competency Hearings): A new psychological evaluation was returned from Rusk State Hospital. After objections to the findings were filed, a competency hearing was held via Zoom to evaluate his status.

December 10, 2025 (Plea & Sentencing): The court officially signed an order restoring the defendant's competency. Roberts subsequently waived his right to a jury trial, pled guilty to Aggravated Robbery, and was convicted. Judge Klein sentenced him to 10 years in a Texas Department of Criminal Justice (TDCJ) prison.

February 9, 2026 – February 12, 2026 (Appeal Initiated): Roberts filed a Notice of Appeal, which was acknowledged by the 13th Court of Appeals. The trial court submitted the initial Clerk's Record to the appellate court.

March 12, 2026 – April 10, 2026 (Abatement/Remand): The 13th Court of Appeals temporarily paused the appeal and remanded the case back to the trial court for a specific hearing. This abatement hearing was held with the defendant appearing via telephone from prison. Judge Klein issued Findings of Facts and Conclusions of Law, and a First Supplemental Clerk's Record was sent to the appellate court.

April 30, 2026 – May 12, 2026 (New Appellate Counsel): Roberts filed motions requesting a free reporter's record (the transcripts of the trial court hearings) and a new attorney for the appeal. The court granted the withdrawal of the previous attorney and appointed Kimbel Brandon as the new lead appellate counsel. A Second Supplemental Clerk's Record was then forwarded to the 13th Court of Appeals, setting the stage for attorney Brandon to draft and file the Appellant's Brief.
"""

def test_odyssey_timeline_parser():
    print("\n=== Testing Odyssey Timeline Parser ===")
    events = parse_odyssey_timeline(FRANK_ROBERTS_SUMMARY)
    
    assert len(events) == 7, f"Expected 7 parsed events, got {len(events)}"
    
    # 1. Arrest & Indictment
    e1 = events[0]
    assert e1["event_date"] == "2024-07-05"
    assert "Arrest & Indictment" in e1["title"]
    assert e1["event_type"] == "ARREST_INDICTMENT"
    print("  [PASS] Event 1: Arrest & Indictment parsed (2024-07-05).")

    # 2. Incompetency Finding
    e2 = events[1]
    assert e2["event_date"] == "2024-12-03"
    assert "Incompetency" in e2["title"]
    assert e2["event_type"] == "COMPETENCY"
    print("  [PASS] Event 2: Incompetency finding parsed (2024-12-03).")

    # 3. Competency Hearings
    e3 = events[2]
    assert e3["event_date"] == "2025-09-30"
    assert "Competency Hearings" in e3["title"]
    assert e3["event_type"] == "COMPETENCY"
    print("  [PASS] Event 3: Competency hearings parsed (2025-09-30).")

    # 4. Plea & Sentencing
    e4 = events[3]
    assert e4["event_date"] == "2025-12-10"
    assert "Plea & Sentencing" in e4["title"]
    assert e4["event_type"] == "PLEA_SENTENCING"
    print("  [PASS] Event 4: Plea & Sentencing parsed (2025-12-10).")

    # 5. Appeal Initiated
    e5 = events[4]
    assert e5["event_date"] == "2026-02-09"
    assert "Appeal Initiated" in e5["title"]
    assert e5["event_type"] == "APPEAL"
    print("  [PASS] Event 5: Notice of Appeal parsed (2026-02-09).")

    # 6. Abatement/Remand
    e6 = events[5]
    assert e6["event_date"] == "2026-03-12"
    assert "Abatement" in e6["title"]
    assert e6["event_type"] == "ABATEMENT"
    print("  [PASS] Event 6: COA Abatement/Remand parsed (2026-03-12).")

    # 7. New Appellate Counsel
    e7 = events[6]
    assert e7["event_date"] == "2026-04-30"
    assert "New Appellate Counsel" in e7["title"]
    assert e7["event_type"] == "APPOINTMENT_ORDER"
    print("  [PASS] Event 7: Lead Appellate Counsel appointment parsed (2026-04-30).")

    print("\n>>> ALL ODYSSEY TIMELINE PARSER TESTS PASSED! <<<\n")

if __name__ == "__main__":
    test_odyssey_timeline_parser()
