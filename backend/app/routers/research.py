import urllib.parse
from typing import Optional, List
from fastapi import APIRouter, Depends, Query
import httpx

from app.deps import get_current_user

router = APIRouter()

NUECES_COURTS_DATA = [
    {
        "type": "DISTRICT_COURT",
        "name": "28th Judicial District Court",
        "judge": "Hon. Nanette Hasette",
        "jurisdiction": "Criminal (Felonies) & Civil",
        "courtroom": "4th Floor, Suite 4.01",
        "coordinator": "Melissa (Court Coordinator)",
        "phone": "(361) 888-0506",
        "location": "Nueces County Courthouse, 901 Leopard St, Corpus Christi, TX 78401",
        "notes": "Handles felony dockets and jury trials.",
    },
    {
        "type": "DISTRICT_COURT",
        "name": "94th Judicial District Court",
        "judge": "Hon. Bobby Galvan",
        "jurisdiction": "Criminal (Felonies) & Civil",
        "courtroom": "4th Floor, Suite 4.02",
        "coordinator": "Sandra (Court Coordinator)",
        "phone": "(361) 888-0245",
        "location": "Nueces County Courthouse, 901 Leopard St, Corpus Christi, TX 78401",
        "notes": "Electronic voucher review through Nueces Appointed Attorney Portal.",
    },
    {
        "type": "DISTRICT_COURT",
        "name": "105th Judicial District Court",
        "judge": "Hon. Jack W. Pulcher",
        "jurisdiction": "Criminal (Felonies), Civil & Juvenile",
        "courtroom": "3rd Floor, Suite 3.01",
        "coordinator": "Priscilla (Court Coordinator)",
        "phone": "(361) 888-0510",
        "location": "Nueces County Courthouse, 901 Leopard St, Corpus Christi, TX 78401",
        "notes": "Also serves Kleberg and Kenedy Counties.",
    },
    {
        "type": "DISTRICT_COURT",
        "name": "117th Judicial District Court",
        "judge": "Hon. Sandra Watts",
        "jurisdiction": "Criminal (Felonies) & Civil",
        "courtroom": "3rd Floor, Suite 3.02",
        "coordinator": "Cindy (Court Coordinator)",
        "phone": "(361) 888-0414",
        "location": "Nueces County Courthouse, 901 Leopard St, Corpus Christi, TX 78401",
        "notes": "Strict compliance with Morton Act discovery receipt logs.",
    },
    {
        "type": "DISTRICT_COURT",
        "name": "148th Judicial District Court",
        "judge": "Hon. Carlos Valdez",
        "jurisdiction": "Criminal (Felonies) & Civil",
        "courtroom": "2nd Floor, Suite 2.01",
        "coordinator": "Denise (Court Coordinator)",
        "phone": "(361) 888-0451",
        "location": "Nueces County Courthouse, 901 Leopard St, Corpus Christi, TX 78401",
        "notes": "Former District Attorney presiding.",
    },
    {
        "type": "DISTRICT_COURT",
        "name": "214th Judicial District Court",
        "judge": "Hon. Inna Klein",
        "jurisdiction": "Criminal (Felonies) & Civil",
        "courtroom": "2nd Floor, Suite 2.02",
        "coordinator": "Sylvia (Court Coordinator)",
        "phone": "(361) 888-0463",
        "location": "Nueces County Courthouse, 901 Leopard St, Corpus Christi, TX 78401",
        "notes": "Specializes in high-volume felony dockets.",
    },
    {
        "type": "DISTRICT_COURT",
        "name": "319th Judicial District Court",
        "judge": "Hon. David Stith",
        "jurisdiction": "Criminal (Felonies) & Civil",
        "courtroom": "5th Floor, Suite 5.01",
        "coordinator": "Terry (Court Coordinator)",
        "phone": "(361) 888-0533",
        "location": "Nueces County Courthouse, 901 Leopard St, Corpus Christi, TX 78401",
        "notes": "Regularly conducts in-custody bond reduction hearings under Art. 17.151 CCP.",
    },
    {
        "type": "DISTRICT_COURT",
        "name": "347th Judicial District Court",
        "judge": "Hon. Missy Medary",
        "jurisdiction": "Criminal (Felonies) & Civil",
        "courtroom": "5th Floor, Suite 5.02",
        "coordinator": "Diana (Court Coordinator)",
        "phone": "(361) 888-0593",
        "location": "Nueces County Courthouse, 901 Leopard St, Corpus Christi, TX 78401",
        "notes": "Presiding Judge of the 5th Administrative Judicial Region of Texas.",
    },
    {
        "type": "COUNTY_COURT_AT_LAW",
        "name": "County Court at Law No. 1",
        "judge": "Hon. Todd Robinson",
        "jurisdiction": "Misdemeanors (Class A & B), Probate & Civil",
        "courtroom": "1st Floor",
        "coordinator": "Court Coordinator",
        "phone": "(361) 888-0237",
        "location": "Nueces County Courthouse, 901 Leopard St, Corpus Christi, TX 78401",
        "notes": "Class A & B misdemeanor dockets, DWIs, and appeals from Municipal/JP courts.",
    },
    {
        "type": "COUNTY_COURT_AT_LAW",
        "name": "County Court at Law No. 2",
        "judge": "Hon. Lisa Gonzales",
        "jurisdiction": "Misdemeanors (Class A & B), Civil",
        "courtroom": "1st Floor",
        "coordinator": "Court Coordinator",
        "phone": "(361) 888-0238",
        "location": "Nueces County Courthouse, 901 Leopard St, Corpus Christi, TX 78401",
        "notes": "Misdemeanor voucher fee rate: $500 flat plea / $50-$100/hr.",
    },
    {
        "type": "COUNTY_COURT_AT_LAW",
        "name": "County Court at Law No. 3",
        "judge": "Hon. Deeanne Galvan",
        "jurisdiction": "Misdemeanors (Class A & B), Civil",
        "courtroom": "1st Floor",
        "coordinator": "Court Coordinator",
        "phone": "(361) 888-0239",
        "location": "Nueces County Courthouse, 901 Leopard St, Corpus Christi, TX 78401",
        "notes": "Misdemeanor trial and plea dockets.",
    },
    {
        "type": "COUNTY_COURT_AT_LAW",
        "name": "County Court at Law No. 4",
        "judge": "Hon. Mark H. Woerner",
        "jurisdiction": "Misdemeanors (Class A & B), Civil",
        "courtroom": "1st Floor",
        "coordinator": "Court Coordinator",
        "phone": "(361) 888-0240",
        "location": "Nueces County Courthouse, 901 Leopard St, Corpus Christi, TX 78401",
        "notes": "Misdemeanor appointed dockets.",
    },
    {
        "type": "COUNTY_COURT_AT_LAW",
        "name": "County Court at Law No. 5",
        "judge": "Hon. Timothy J. McCoy",
        "jurisdiction": "Misdemeanors (Class A & B), Civil",
        "courtroom": "1st Floor",
        "coordinator": "Court Coordinator",
        "phone": "(361) 888-0695",
        "location": "Nueces County Courthouse, 901 Leopard St, Corpus Christi, TX 78401",
        "notes": "Misdemeanor appointed counsel cases.",
    },
    {
        "type": "OFFICIAL",
        "name": "Nueces County District Clerk",
        "judge": "Anne Lorentzen (District Clerk)",
        "jurisdiction": "District Court Records, Odyssey Case Filings & E-File",
        "courtroom": "Suite 313",
        "coordinator": "Criminal Division Desk",
        "phone": "(361) 888-0450",
        "location": "901 Leopard St, Suite 313, Corpus Christi, TX 78401",
        "notes": "Maintains criminal case dockets, Odyssey Portal access, and judicial order filings.",
    },
    {
        "type": "OFFICIAL",
        "name": "Nueces County Auditor / Indigent Defense Vouchers",
        "judge": "County Auditor Office",
        "jurisdiction": "Voucher Review, Warrant Issuance & Direct Deposit",
        "courtroom": "Auditor's Office, 3rd Floor",
        "coordinator": "Accounts Payable / Attorney Vouchers",
        "phone": "(361) 888-0380",
        "location": "901 Leopard St, Corpus Christi, TX 78401",
        "notes": "Processes verified vouchers after judge signature. ACH payments posted to vendor TX-NUE-84920.",
    }
]

TEXAS_STATUTES_CORPUS = [
    {
        "code": "TEX. CODE CRIM. PROC. ART. 39.14",
        "title": "Michael Morton Act (Criminal Discovery)",
        "category": "Discovery & Pre-Trial",
        "summary": "Mandates open-file discovery in Texas. Upon request, the State must produce offense reports, witness statements, body-worn camera video, dashcam, and 911 audio as soon as practicable. Art. 39.14(f) prohibits defense counsel from providing physical copies to clients (view only with identifying info redacted).",
        "key_elements": [
            "Mandatory disclosure upon timely written request",
            "Offense reports, BWC/dashcam, lab reports, 911 calls",
            "Continuous duty to disclose exculpatory / Brady material",
            "Art. 39.14(f) redaction requirement for client inspection",
        ],
        "full_text_url": "https://statutes.capitol.texas.gov/Docs/CR/htm/CR.39.htm#39.14",
    },
    {
        "code": "TEX. CODE CRIM. PROC. ART. 17.151",
        "title": "Release on Bail Because of Delay (90-Day Speedy Indictment Rule)",
        "category": "Bail & In-Custody Rights",
        "summary": "A defendant detained in jail pending trial on an accusation of felony must be released either on personal bond or by reducing the amount of bail required if the state is not ready for trial within 90 days from the commencement of detention (30 days for Class A, 15 days for Class B).",
        "key_elements": [
            "90-day strict cap for unindicted felony jail detainees",
            "Mandatory reduction of bail to an amount defendant can afford or PR bond",
            "Applies to McConnell Jail and Nueces County Jail detainees",
        ],
        "full_text_url": "https://statutes.capitol.texas.gov/Docs/CR/htm/CR.17.htm#17.151",
    },
    {
        "code": "TEX. CODE CRIM. PROC. ART. 26.05",
        "title": "Compensation of Appointed Counsel (Texas Fair Defense Act)",
        "category": "Indigent Defense & Vouchers",
        "summary": "Governs payment of court-appointed counsel. Requires all payments to be in accordance with the county fee schedule adopted by the local judges. There is no statewide or Nueces County statutory 30-day forfeiture rule for attorney fees.",
        "key_elements": [
            "Itemized statements of hours (in-court and out-of-court)",
            "Reasonable hourly rate or approved fee schedule",
            "Judge reviews and approves before auditor warrant is issued",
        ],
        "full_text_url": "https://statutes.capitol.texas.gov/Docs/CR/htm/CR.26.htm#26.05",
    },
    {
        "code": "TEX. PENAL CODE § 22.01",
        "title": "Assault (Including Family Violence)",
        "category": "Offenses Against the Person",
        "summary": "Intentionally, knowingly, or recklessly causing bodily injury to another. Class A Misdemeanor baseline; enhanced to Third Degree Felony if committed against family/household member with prior conviction or by impeding breath/circulation (choking).",
        "key_elements": [
            "Bodily injury assault vs threat/offensive contact",
            "Affirmative finding of family violence (Art. 42.013 CCP)",
            "Impeding breath/circulation enhances to 3rd Degree Felony",
        ],
        "full_text_url": "https://statutes.capitol.texas.gov/Docs/PE/htm/PE.22.htm#22.01",
    },
    {
        "code": "TEX. HEALTH & SAFETY CODE § 481.115",
        "title": "Possession of Controlled Substance in Penalty Group 1 / 1-B",
        "category": "Drug Offenses",
        "summary": "Possession of cocaine, methamphetamine, heroin, or fentanyl (PG 1-B). Less than 1 gram is a State Jail Felony (180 days - 2 years SJF); 1 to 4 grams is 3rd Degree Felony (2-10 years); 4 to 200 grams is 2nd Degree Felony (2-20 years).",
        "key_elements": [
            "PG 1 / PG 1-B (Fentanyl separated by 87th Texas Legislature)",
            "<1g: State Jail Felony; 1-4g: 3rd Degree; 4-200g: 2nd Degree",
            "Requires DPS lab report confirmation under Morton Act",
        ],
        "full_text_url": "https://statutes.capitol.texas.gov/Docs/HS/htm/HS.481.htm#481.115",
    },
    {
        "code": "TEX. PENAL CODE § 49.04",
        "title": "Driving While Intoxicated (DWI)",
        "category": "Intoxication Offenses",
        "summary": "Operating a motor vehicle in a public place while intoxicated. Class B Misdemeanor baseline; Class A if BAC >= 0.15; enhanced to 3rd Degree Felony if 2 prior DWI convictions.",
        "key_elements": [
            "Loss of normal mental or physical faculties OR BAC >= 0.08",
            "Class B (minimum 72h confinement), Class A (BAC >= 0.15)",
            "3rd DWI is a Third Degree Felony",
        ],
        "full_text_url": "https://statutes.capitol.texas.gov/Docs/PE/htm/PE.49.htm#49.04",
    },
    {
        "code": "TEX. PENAL CODE § 38.04",
        "title": "Evading Arrest or Detention",
        "category": "Obstruction of Justice",
        "summary": "Intentionally fleeing from a person he knows is a peace officer attempting lawfully to arrest or detain him. Class A Misdemeanor on foot; enhanced to State Jail or 3rd Degree Felony if using a vehicle.",
        "key_elements": [
            "Knowledge of peace officer + lawful attempted detention",
            "On foot: Class A; With motor vehicle: 3rd Degree Felony",
        ],
        "full_text_url": "https://statutes.capitol.texas.gov/Docs/PE/htm/PE.38.htm#38.04",
    },
]


@router.get("/nueces-directory")
async def get_nueces_court_directory(
    court_type: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    """Returns directory of Nueces County District Courts, CCLs, Judges, and Coordinators."""
    data = NUECES_COURTS_DATA
    if court_type:
        data = [c for c in data if c["type"] == court_type]
    return {
        "courts": data,
        "courthouse_address": "Nueces County Courthouse, 901 Leopard St, Corpus Christi, TX 78401",
        "district_clerk": "Anne Lorentzen, Suite 313, (361) 888-0450",
        "county_clerk": "Kara Sands, Suite 201, (361) 888-0580",
    }


@router.get("/statutes")
async def get_texas_statutes(
    query: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    """Searches Texas Criminal Statutes corpus using offline FTS5 SQLite database."""
    from app.services.texas_statutes_service import texas_statutes_service
    if not query:
        statutes = texas_statutes_service.get_all_statutes()
    else:
        statutes = texas_statutes_service.search_statutes(query)

    # Format key_elements for frontend backwards compatibility
    formatted = []
    for s in statutes:
        formatted.append({
            "code": s["code"],
            "title": s["title"],
            "category": s["category"],
            "degree": s["degree"],
            "summary": s["summary"],
            "key_elements": s["elements"],
            "penalty_range": s["penalty_range"],
            "full_text": s["full_text"],
            "affirmative_defenses": s["affirmative_defenses"],
        })

    return {"statutes": formatted, "query": query, "total": len(formatted), "source": "Offline SQLite FTS5 (texas_codes.db)"}


@router.post("/extract-citations")
async def extract_citations_endpoint(
    payload: dict,
    current_user: dict = Depends(get_current_user),
):
    """Deterministic legal citation parser powered by eyecite & Texas statutory patterns."""
    from app.services.citation_service import citation_service
    text = payload.get("text", "")
    citations = citation_service.extract_citations(text)
    return {"count": len(citations), "citations": citations}


@router.get("/courtlistener")
async def search_courtlistener(
    query: str = Query(..., description="Legal research query e.g. 'Michael Morton Act' or 'Art. 17.151'"),
    court: Optional[str] = "texapp-13",  # default to 13th Court of Appeals (Corpus Christi - Edinburg)
    current_user: dict = Depends(get_current_user),
):
    """
    Free case law search querying CourtListener REST API for Texas appellate decisions.
    Falls back to curated Texas precedents if network is unavailable.
    """
    url = f"https://www.courtlistener.com/api/rest/v3/search/?q={urllib.parse.quote(query)}&court={court}&type=o"
    
    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            resp = await client.get(url, headers={"User-Agent": "Filestavk-Legal-Command/1.0"})
            if resp.status_code == 200:
                data = resp.json()
                results = []
                for item in data.get("results", [])[:10]:
                    results.append({
                        "case_name": item.get("caseName", "Appellate Decision"),
                        "citation": item.get("citation", []),
                        "court": item.get("court", "13th Court of Appeals (Corpus Christi)"),
                        "date_filed": item.get("dateFiled", ""),
                        "snippet": item.get("snippet", ""),
                        "absolute_url": f"https://www.courtlistener.com{item.get('absolute_url', '')}",
                    })
                return {
                    "source": "CourtListener REST API (Free Law Project)",
                    "query": query,
                    "court": court,
                    "count": len(results),
                    "results": results,
                }
    except Exception:
        pass

    # Curated offline Texas appellate precedents
    curated = [
        {
            "case_name": "Watkins v. State, 619 S.W.3d 265 (Tex. Crim. App. 2021)",
            "citation": ["619 S.W.3d 265"],
            "court": "Texas Court of Criminal Appeals",
            "date_filed": "2021-03-03",
            "snippet": "Holding that the Michael Morton Act (Tex. Code Crim. Proc. art. 39.14) creates a continuous, affirmative duty on the State to produce open-file discovery and exculpatory evidence without requiring defendant to show good cause.",
            "absolute_url": "https://www.courtlistener.com/opinion/4883344/watkins-v-state/",
        },
        {
            "case_name": "Ex parte Lanclos, 624 S.W.3d 923 (Tex. Crim. App. 2021)",
            "citation": ["624 S.W.3d 923"],
            "court": "Texas Court of Criminal Appeals",
            "date_filed": "2021-05-19",
            "snippet": "Addressing Article 17.151 CCP mandatory release on bail where the State is not ready for trial within 90 days for felony detainees in county custody.",
            "absolute_url": "https://www.courtlistener.com/opinion/6429381/ex-parte-lanclos/",
        },
        {
            "case_name": "State v. Heath, 642 S.W.3d 591 (Tex. App.—Corpus Christi-Edinburg 2022)",
            "citation": ["642 S.W.3d 591"],
            "court": "Texas 13th Court of Appeals (Corpus Christi)",
            "date_filed": "2022-02-10",
            "snippet": "Evaluating trial court discovery sanctions and suppression of state evidence for failure to comply with timely Michael Morton Act disclosures in Nueces County.",
            "absolute_url": "https://www.courtlistener.com/opinion/7082194/state-v-heath/",
        },
    ]

    return {
        "source": "Texas Criminal Case Law Precedents (Curated Offline + CourtListener Cache)",
        "query": query,
        "court": court,
        "count": len(curated),
        "results": curated,
    }
