"""
Integration test for Gemini Briefing Workflow:
Paste Brief -> Parse Proposals -> Retrieve Latest -> Commit to Database.
"""

import sys
import os
import asyncio

sys.path.insert(0, os.path.dirname(__file__))

from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import async_session_maker
from app.models.case import Case
from app.models.client import Client
from app.models.event import Event
from sqlalchemy.future import select
from test_gemini_brief_parser import SAMPLE_GEMINI_BRIEF


async def run_test():
    print("\n=== Testing Gemini Briefing API & Database Commitment ===")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Login to get JWT
        login_res = await client.post("/auth/login", data={"username": "admin", "password": "changeme"})
        assert login_res.status_code == 200, f"Login failed: {login_res.text}"
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("  [PASS] Logged in as attorney.")

        # 2. POST /briefing/paste
        paste_res = await client.post("/briefing/paste", json={"raw_text": SAMPLE_GEMINI_BRIEF}, headers=headers)
        assert paste_res.status_code == 200, f"Paste failed: {paste_res.text}"
        paste_data = paste_res.json()
        assert paste_data["status"] == "success"
        proposals = paste_data["proposals"]
        print(f"  [PASS] POST /briefing/paste succeeded: {len(proposals)} proposals generated.")

        # 3. GET /briefing/latest
        latest_res = await client.get("/briefing/latest", headers=headers)
        assert latest_res.status_code == 200
        latest_data = latest_res.json()
        assert latest_data["has_brief"] is True
        assert len(latest_data["proposals"]) == len(proposals)
        print("  [PASS] GET /briefing/latest verified cached persistence on disk.")

        # 4. POST /briefing/commit
        commit_res = await client.post(
            "/briefing/commit",
            json={"proposals": proposals, "verified_by": "Kimbel Brandon, Esq."},
            headers=headers
        )
        assert commit_res.status_code == 200, f"Commit failed: {commit_res.text}"
        commit_data = commit_res.json()
        assert commit_data["status"] == "success"
        print(f"  [PASS] POST /briefing/commit: {commit_data['committed_total']} items committed.")
        print(f"         Created Cases: {len(commit_data['created_cases'])}")
        print(f"         Created Clients: {len(commit_data['created_clients'])}")
        print(f"         Created Events: {len(commit_data['created_events'])}")

        # 5. Verify database records
        async with async_session_maker() as session:
            # Check Lorraine Davila in-custody case
            lorraine_case = (await session.execute(select(Case).where(Case.case_number == "26FC-3800H"))).scalars().first()
            assert lorraine_case is not None, "Expected case 26FC-3800H to be created"
            assert lorraine_case.in_custody is True, "Expected in_custody=True for Lorraine Davila"
            assert lorraine_case.has_appointment_order is True
            assert lorraine_case.appointment_status == "AWAITING_ACCEPTANCE"
            print("  [PASS] Verified Lorraine Davila case: in_custody=True, AWAITING_ACCEPTANCE.")

            # Check Aubree Williams hearings
            aubree_events = (await session.execute(select(Event).where(Event.title.ilike("%Aubree Williams%")))).scalars().all()
            assert len(aubree_events) >= 1, "Expected scheduled events for Aubree Williams"
            print(f"  [PASS] Verified Aubree Williams docket events created ({len(aubree_events)}).")

            # Check Waiver cases
            velasquez_case = (await session.execute(select(Case).where(Case.case_number == "26MC-04204"))).scalars().first()
            assert velasquez_case is not None, "Expected case 26MC-04204 to be created"
            assert velasquez_case.stage == "PRE_TRIAL", f"Expected stage PRE_TRIAL, got {velasquez_case.stage}"
            print("  [PASS] Verified Robert Velasquez case: stage=PRE_TRIAL.")

    print("\n>>> ALL GEMINI BRIEFING WORKFLOW TESTS PASSED WITH 100% SUCCESS! <<<\n")


if __name__ == "__main__":
    asyncio.run(run_test())
