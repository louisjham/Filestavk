"""
Unit test for Gemini 10-Day Deep-Dive Brief Parser Service.
Uses Kimbel Brandon's exact real-world Gem output.
"""

import sys
import os

# Add backend to sys.path
sys.path.insert(0, os.path.dirname(__file__))

from app.services.gemini_brief_parser_service import gemini_brief_parser_service

SAMPLE_GEMINI_BRIEF = """
Good morning, Counselor. Here is your 10-Day Nueces County Criminal Defense Deep-Dive Brief for today.
Section 1: Upcoming 10-Day Court Schedule & Docket (Google Calendar)2026-09-14 | 8:30 AM CDT | County Court at Law No. 5 | Aubree Williams | Cause # 2025-FAM-61124-5 | Hearing — [View Event](https://www.google.com/url?q=https://www.google.com/calendar/event?eid%3DNmlpanI5dTE1dmQ3aGI5a2E2NjIyNzQwY20gaGVscEBoZW1vY3lhbmlubGF3LmNvbQ&sa=E&source=workflows)
2026-09-14 | 1:30 PM CDT | County Court at Law No. 5 | Aubree Williams | Cause # 2025-FAM-61124-5 | Placement Hearing — [View Event](https://www.google.com/url?q=https://www.google.com/calendar/event?eid%3DaGdkN3ZwMnFqaWwwMzN0cmtzY2Ntc3MxMTggaGVscEBoZW1vY3lhbmlubGF3LmNvbQ&sa=E&source=workflows)
2026-09-14 | All Day | 13th Court of Appeals | Frank Allen Roberts | Cause # Not Provided | File Brief Extension Deadline — [View Event](https://www.google.com/url?q=https://www.google.com/calendar/event?eid%3DNHB0cGttc2k5OTg4bXBwcGduY3FiMXRpb2ggaGVscEBoZW1vY3lhbmlubGF3LmNvbQ&sa=E&source=workflows)
Docket Conflict Note: Conflicting start times recorded for Aubree Williams in CC #5 (8:30 AM vs 1:30 PM).
Section 2: High-Priority & Critical Deadlines (Top of Mind)[15 Mins] [Order of Appointment & Personal Contact Requirement — Lorraine Davila] — [View File](https://www.google.com/url?q=https://drive.google.com/a/hemocyaninlaw.com/open?id%3D1_ojn-JmUNLEhTnM7mGYbW9VZ3RfZ91Hg&sa=E&source=workflows)Details: Appointed September 11, 2026, to represent Lorraine Davila (Cause # 26FC-3800H, 347th District Court) on State Jail Felony POSS CS PG 1/1-B <1G. Client is in jail. Must make personal contact and file signed Acceptance of Appointment with District Clerk within 48 hours of contact.
[15 Mins] [Physical Media Discovery Procedure — Adam Suarez]Details: District Attorney's office confirmed September 14, 2026, that discovery for Cause # 25FC-6198B contains CD/DVD media. Requires filling out physical Discovery Request for CD/DVD form at DAO front desk and supplying blank CD/DVD or USB media.
Proposed Action/Draft: "I am preparing the physical CD/DVD discovery request form and blank media for submission to the Nueces County District Attorney's Office for Cause # 25FC-6198B (State v. Adam Suarez)."
Section 3: Deep-Dive Case Updates & Discovery (Art. 39.14 / State Filings)Client: Adam Suarez | Cause: 25FC-6198B | Venue: Nueces County District CourtDetailed Analysis: Requested Art. 39.14 discovery on September 11, 2026. DAO responded September 14, 2026, noting media is on CD/DVD. Provided digital copies of Indictment, Medical Records, Arrest Warrant, Incident Report, ADC, Intake Checklist, and DVD-CD Request Form.
Client: Lorraine Davila | Cause: 26FC-3800H | Venue: 347th District Court, Nueces County, Texas — [View File](https://www.google.com/url?q=https://drive.google.com/a/hemocyaninlaw.com/open?id%3D1_ojn-JmUNLEhTnM7mGYbW9VZ3RfZ91Hg&sa=E&source=workflows)Detailed Analysis: Received Order of Appointment signed September 11, 2026, for State Jail Felony possession charge.
Client: Robert Velasquez | Cause: 26MC-04204 | Venue: County Court at Law No. 3, Nueces County, Texas — [View File](https://www.google.com/url?q=https://drive.google.com/a/hemocyaninlaw.com/open?id%3D1HtBHWCegqxViQ99vbh5dh_Hq_QKolmrE&sa=E&source=workflows)Detailed Analysis: Waiver of Arraignment filed September 4, 2026; waives reading of information, enters plea of not guilty, and requests pre-trial and jury trial settings.
Client: Joseph Prude | Cause: 26MC-02715 | Venue: County Court at Law No. 3, Nueces County, Texas — [View File](https://www.google.com/url?q=https://drive.google.com/a/hemocyaninlaw.com/open?id%3D1HtBHWCegqxViQ99vbh5dh_Hq_QKolmrE&sa=E&source=workflows)Detailed Analysis: Waiver of Arraignment filed September 4, 2026; waives reading of information, enters plea of not guilty, and requests pre-trial and jury trial settings.
Client: Claudio Desidoro Torres | Cause: 26MC-03516 | Venue: County Court at Law No. 1, Nueces County, Texas — [View File](https://www.google.com/url?q=https://drive.google.com/a/hemocyaninlaw.com/open?id%3D1HtBHWCegqxViQ99vbh5dh_Hq_QKolmrE&sa=E&source=workflows)Detailed Analysis: Waiver of Arraignment filed September 4, 2026; waives reading of information, enters plea of not guilty, and requests pre-trial and jury trial settings.
Client: Daniel Isai Torres | Cause: 25MC-02877 | Venue: County Court at Law No. 1, Nueces County, Texas — [View File](https://www.google.com/url?q=https://drive.google.com/a/hemocyaninlaw.com/open?id%3D1HtBHWCegqxViQ99vbh5dh_Hq_QKolmrE&sa=E&source=workflows)Detailed Analysis: Waiver of Arraignment filed September 4, 2026; waives reading of information, enters plea of not guilty, and requests pre-trial and jury trial settings.
Client: Jessica Rubio | Cause: 25MC-02015 | Venue: County Court at Law No. 1, Nueces County, Texas — [View File](https://www.google.com/url?q=https://drive.google.com/a/hemocyaninlaw.com/open?id%3D1HtBHWCegqxViQ99vbh5dh_Hq_QKolmrE&sa=E&source=workflows)Detailed Analysis: Waiver of Arraignment filed September 4, 2026; waives reading of information, enters plea of not guilty, and requests pre-trial and jury trial settings.
Client: Mariana Vaughn | Cause: 25MC-06181 | Venue: County Court at Law No. 2, Nueces County, Texas — [View File](https://www.google.com/url?q=https://drive.google.com/a/hemocyaninlaw.com/open?id%3D1HtBHWCegqxViQ99vbh5dh_Hq_QKolmrE&sa=E&source=workflows)Detailed Analysis: Waiver of Arraignment filed September 4, 2026; waives reading of information, enters plea of not guilty, and requests pre-trial and jury trial settings.
Section 4: Attorney Fee Vouchers & Administrative Status (Past 10 Days)No attorney fee voucher notifications or status updates were received in the past 10 days.
Section 5: Active & Overdue Legal Tasks (Google Tasks)No active or overdue Google Tasks found.
Forwarded Communications & Attached Documents OverviewSelf-Forwarded Batch sent from kimbelfbrandon@gmail.com to help@hemocyaninlaw.com on September 13, 2026:Cause # 24FC-4327B (State v. Jesus R. Salazar / COA # 13-25-00436-CR): Acceptance of Appointment e-filing receipt, 13th Court of Appeals Opinion & Judgment dismissing appeal for lack of jurisdiction (untimely notice of appeal), and final Mandate issued.
Cause # 24FC-4260E & 25FC-2176E (Jose Felix Herrera / COA # 13-25-00262-CR & 13-25-00261-CR): Orders granting motion for copy of sealed record and reinstating appeals.
Work Completed & Actions Taken (Forwarded Work Track)Detailed Summary: Forwarded email records confirm processing appellate mandates and opinions, logging accepted e-filings, and archiving appellate orders.
Tasks Created in Past 10 Days: No Google Tasks were generated in the last 10 days.
Have a productive day!
"""

def test_gemini_brief_parser():
    print("\n=== Testing Gemini 10-Day Deep-Dive Brief Parser ===")
    res = gemini_brief_parser_service.parse_brief(SAMPLE_GEMINI_BRIEF)
    counts = res["summary_counts"]

    print(f"  Total Proposals: {counts['total_items']}")
    print(f"  Hearings: {counts['hearings']}")
    print(f"  Critical Deadlines / Appointments: {counts['critical_deadlines']}")
    print(f"  Waivers of Arraignment: {counts['waivers_of_arraignment']}")
    print(f"  Appellate Orders: {counts['appellate_orders']}")
    print(f"  Conflicts Detected: {counts['conflicts_detected']}")

    # 1. Verify Hearings
    assert counts["hearings"] >= 3, f"Expected at least 3 hearings, got {counts['hearings']}"
    aubree_hearings = [p for p in res["proposals"] if "Aubree Williams" in p["client_name"]]
    assert len(aubree_hearings) == 2, f"Expected 2 hearings for Aubree Williams, got {len(aubree_hearings)}"
    assert any(p["has_conflict"] for p in aubree_hearings), "Expected conflict flag on Aubree Williams hearing"
    print("  [PASS] Section 1: Court hearings and docket conflict detected correctly.")

    # 2. Verify Critical Deadlines
    lorraine_items = [p for p in res["proposals"] if "Lorraine Davila" in p["client_name"] and p["category"] == "CRITICAL_DEADLINE"]
    assert len(lorraine_items) >= 1, "Expected Lorraine Davila deadline proposal"
    lorraine = lorraine_items[0]
    assert lorraine["case_number"] == "26FC-3800H", f"Unexpected cause: {lorraine['case_number']}"
    assert lorraine["court"] == "347th District Court", f"Unexpected court: {lorraine['court']}"
    assert lorraine["in_custody"] is True, "Expected in_custody=True for Lorraine Davila"
    assert "26.04" in (lorraine.get("statutory_basis") or ""), "Expected Art. 26.04 statutory basis"
    print("  [PASS] Section 2: Critical deadline and in-custody clock detected correctly.")

    # 3. Verify Waivers of Arraignment
    waivers = [p for p in res["proposals"] if p.get("badge") == "Waiver of Arraignment"]
    assert len(waivers) == 6, f"Expected 6 waivers of arraignment, got {len(waivers)}"
    waiver_causes = {w["case_number"] for w in waivers}
    expected_causes = {"26MC-04204", "26MC-02715", "26MC-03516", "25MC-02877", "25MC-02015", "25MC-06181"}
    assert expected_causes.issubset(waiver_causes), f"Missing expected waiver causes: {expected_causes - waiver_causes}"
    for w in waivers:
        assert w["stage"] == "PRE_TRIAL", f"Expected stage PRE_TRIAL for waiver, got {w['stage']}"
        assert w["plea"] == "NOT_GUILTY", f"Expected NOT_GUILTY plea, got {w['plea']}"
    print("  [PASS] Section 3: 6 Waivers of Arraignment detected with PRE_TRIAL stage and NOT_GUILTY plea.")

    # 4. Verify Appellate Orders
    appellate = [p for p in res["proposals"] if p["category"] == "APPELLATE_ORDER"]
    assert len(appellate) >= 2, f"Expected at least 2 appellate records, got {len(appellate)}"
    coa_numbers = {a.get("coa_number") for a in appellate}
    assert "13-25-00436-CR" in coa_numbers or any("13-25-00436-CR" in a["details"] for a in appellate)
    print("  [PASS] Forwarded Section: 13th Court of Appeals mandates and orders detected.")

    print("\n>>> ALL GEMINI BRIEF PARSER UNIT TESTS PASSED WITH 100% SUCCESS! <<<\n")


if __name__ == "__main__":
    test_gemini_brief_parser()
