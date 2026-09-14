# Filestavk — AI Agent System & Operational Manual

> **CRITICAL INSTRUCTION FOR ALL INCOMING MODELS**:
> 1. At the very start of every turn or session, **read `HANDOFF.md`** at the repository root using `view_file` to understand the immediate state, active uncommitted changes, open branches, and current objectives.
> 2. Do **NOT** rewrite or alter solved pipelines or data transformations without reading the rationale documented here.
> 3. You operate under a strict **Zero-Hallucination Legal Integrity Directive**. Never hallucinate a statute, criminal procedure article, case law citation, or record fact.

---

## 1. Project Overview & Identity

**Filestavk** is an open-source, local-first, self-hosted case, discovery, and practice management system built specifically for a **solo criminal defense practitioner** based in **Corpus Christi, Nueces County, Texas**.

### The Core Problem Filestavk Solves:
A solo criminal defense attorney manages 100–250 active criminal cases with asymmetrical resources compared to the District Attorney's office.
- Criminal procedure follows a highly predictable chronological conveyor belt (governed by the Texas Code of Criminal Procedure).
- However, case outcomes are unpredictable because prosecutors bury the defense in hundreds of pages of messy, unindexed discovery (police offense reports, body cam videos, CAD dispatch logs, DPS lab reports).
- **The Core Value Proposition**: Cut through the noise, enforce statutory procedural clocks, and **"circle the important stuff in red ink"** (identify missing discovery, unrecorded custodial interrogations, warrantless searches, statutory element deficits, and automate court-appointed CJA voucher billing).

---

## 2. Technical Stack & Directory Layout

### Backend
- **Framework**: Python 3.12, FastAPI (async/await)
- **Database**: SQLite with WAL mode (`PRAGMA journal_mode=WAL; PRAGMA busy_timeout=5000;`) via SQLAlchemy (asyncio) + Alembic
- **Document & Extraction Pipeline**:
  - `PyMuPDF` (`fitz`) for native PDF text & page geometry.
  - `pytesseract` (Tesseract 5 OCR) + `Pillow` for image preprocessing, Otsu thresholding, tight-bounding-box cropping.
  - `python-docx`, `openpyxl`, and `csv` for Office/spreadsheet formats.
  - `scikit-learn` (Multinomial Naive Bayes + TF-IDF) for Bayesian document classification.
- **Port**: `8000` (API Docs: `http://localhost:8000/docs`)

### Frontend
- **Framework**: React 18, TypeScript, Vite, Tailwind CSS, Shadcn/ui
- **State & Data Fetching**: TanStack Query (React Query)
- **Network / LAN Access**: Exposed via `--host` on port `5173` for cross-device office/courtroom tablet use.

### Directory Structure
```
c:\antigravity\Filestavk\
├── AGENTS.md                  # This persistent constitution & operating manual
├── HANDOFF.md                 # Live session state, active tasks, uncommitted diffs
├── README.md                  # Human user overview & quick start
├── backend/
│   ├── app/
│   │   ├── config.py          # Pydantic BaseSettings (.env)
│   │   ├── database.py        # Async engine, WAL pragma, session factory
│   │   ├── models/            # SQLAlchemy models: Case, Client, Document, DocumentRule, Event, Voucher, TimeEntry
│   │   ├── routers/           # FastAPI endpoints: documents.py, cases.py, clients.py, ingestion.py, etc.
│   │   ├── schemas/           # Pydantic request/response schemas
│   │   └── services/          # document_extractor_service.py, document_rules_service.py, classifier.py
│   ├── data/                  # SQLite DB (filestavk.db), documents storage, classifier models
│   └── tests/                 # Unit & regression tests (test_document_extractor.py, test_acceptance_workflow.py)
├── frontend/                  # Vite + React client
├── skills/                    # Custom agent skills (portal-assist, gmail-ingestion)
└── scripts/                   # Standalone helper scripts (intake_appointment_order.py)
```

---

## 3. Texas & Nueces County Legal Domain Knowledge

You must understand the local legal environment to avoid making amateur legal design mistakes.

### A. The Nueces County Court System (Corpus Christi, TX)
- **District Courts (Felonies)**:
  - 28th District Court (Hon. Nanette Hasette)
  - 94th District Court (Hon. Bobby Galvan)
  - 105th District Court (Hon. Jack W. Pulcher)
  - 117th District Court (Hon. Sandra Watts)
  - 148th District Court (Hon. Carlos Valdez)
  - 214th District Court (Hon. Inna Klein)
  - 319th District Court (Hon. David Stith)
  - 347th District Court (Hon. Missy Medary)
- **County Courts at Law (Misdemeanors & Appeals)**:
  - County Court at Law No. 1 (Hon. Robert J. Vargas)
  - County Court at Law No. 2 (Hon. Melissa Madrigal)
  - County Court at Law No. 3 (Hon. Deeanne Galvan)
  - County Court at Law No. 4 (Hon. Mark Skurka)
  - County Court at Law No. 5 (Hon. Timothy McCoy)
- **Nueces County Magistrate Court**:
  - Presided over by Magistrate Judges (e.g., Judge Linda J. Rhodes-Schauer). Located at the Nueces County Courthouse / Jail (901 Leopard St, Corpus Christi, TX).
- **Public Portal**: Tyler Technologies Odyssey Public Portal (`portal-txnueces.tylertech.cloud/Portal/Home/Dashboard/29`).

### B. The Predictable Criminal Procedure Lifecycle (Texas Code of Criminal Procedure)
1. **Arrest & Magistration (Art. 15.17 CCP)**: Defendant brought before magistrate within 24–48 hours; statutory Miranda-style warnings read; bail set.
2. **Speedy Release Clock (Art. 17.151 CCP)**:
   - If the State is not ready for trial, defendant in custody MUST be released on personal bond or bail reduced:
     - Felony: **90 days**.
     - Class A Misdemeanor: **30 days**.
     - Class B Misdemeanor: **15 days**.
3. **Appointment of Counsel & 48-Hour Contact (Art. 26.04(j)(1) CCP)**:
   - Court signs **Order of Appointment**.
   - Appointed attorney MUST make every reasonable effort to contact the defendant not later than the end of the **first working day** after appointment and interview the defendant as soon as practicable.
   - Attorney files signed **Acceptance of Appointment** with District/County Clerk.
4. **Voucher Qualification (Art. 26.05 CCP)**:
   - County Auditor will NOT approve payment vouchers without verified file-stamped Order of Appointment and Acceptance of Appointment on record.
5. **Charging Instrument & Arraignment (Art. 27.18 / 27.19 CCP)**:
   - Grand Jury Indictment (felony) or Information (misdemeanor).
   - Attorney files formal **Waiver of Arraignment** entering Not Guilty plea and requesting Pre-Trial / Jury settings.
6. **The Michael Morton Act Discovery Engine (Art. 39.14 CCP)**:
   - The cornerstone of Texas criminal discovery. The State has an affirmative, continuous statutory duty to disclose and produce offense reports, witness statements, body camera/dashcam footage, electronic recordings, and all exculpatory/mitigating (*Brady v. Maryland*) evidence.
   - Requires defense written request and State itemized compliance inventory.
7. **Omnibus Pre-Trial & Suppression (Art. 28.01 CCP)**:
   - 10-day pre-trial motion deadline.
   - Motions to suppress evidence under **Art. 38.23 CCP** (Texas Statutory Exclusionary Rule — broader than federal 4th Amendment) and **Art. 38.22 CCP** (strict recording requirements for custodial statements).

---

## 4. Solved Data Transformation Problems (DO NOT RE-INVENT)

The team has already resolved several brittle parsing issues. Preserve and leverage these battle-tested routines in `backend/app/services/document_extractor_service.py`:

1. **Dual-Pass Tightly-Cropped OCR for Client Identification**:
   - Generic full-page OCR frequently misreads client names, DOBs, and SO numbers on degraded court scans.
   - **Solution**: The extractor locates the anchor text `"to represent:"` and executes a localized sub-region crop (`focused_crop`) with targeted preprocessing (grayscale, contrast boost, thresholding), plus a digits-and-slashes-only whitelist pass for the Date of Birth.
2. **Client Block Parsing & Separation**:
   - The block under `"to represent:"` contains: `Name`, `DOB`, `Address`, `Home Phone`, `Work Phone`, `Cell Phone`, `Email`, and `In Jail: Yes/No`.
   - Separate fields are parsed into explicit dictionary keys so that secondary phones do not overwrite the primary contact, and attorney email domains (`hemocyaninlaw.com`, `nuecesco.com`, etc.) are strictly excluded.
3. **Standardized Renaming & Sidecar JSON**:
   - PDFs are automatically cataloged under `backend/data/documents/{case_id}/`.
   - Naming convention:
     - `Order_Of_Appt-{case_number}.pdf` for initial appointment orders.
     - `Order_Of_Acceptance-{case_number}.pdf` for filed acceptance forms.
     - `NEEDS_REVIEW_{original_filename}` if case number cannot be reliably identified.
   - Every file receives a matching sidecar `.json` metadata file containing health status, detected entities, extraction timestamp, and legal classification.
4. **Document Rules Engine Execution**:
   - `DocumentRule` objects in `backend/app/models/document_rule.py` trigger automated case status updates, docket events, statutory deadline calculations, and voucher transitions upon document ingestion.

---

## 5. Strict Zero-Hallucination Legal Integrity Directive

In legal applications, a hallucinated citation, invented deadline, or fictitious statute is a malpractice catastrophe. All models must abide by these non-negotiable rules:

1. **Always Ground in Verbatim Record Text**:
   - When extracting names, dates, charges, or factual statements from a case document, always record the exact text snippet and page number.
   - Never extrapolate or infer an unstated charge or judicial finding.
2. **Strict Verification Against Authoritative Legal Repositories**:
   - Do not invent Texas case law or statutory citations.
   - Verify all citations against the **Free Law Project / CourtListener API** (or the offline Texas Statutory SQLite database).
   - If a citation cannot be verified, explicitly flag it as `UNVERIFIED_CITATION`.
3. **Explicit Distinctions Between Facts, Allegations, and Rulings**:
   - An allegation in a police narrative (CCPD/NCSO offense report) is NOT an established fact. The system must label them strictly as: `STATE_ALLEGATION`, `OFFICER_OBSERVATION`, `WITNESS_STATEMENT`, or `JUDICIAL_FINDING`.

---

## 6. Model Handoff Protocol (Between Sessions)

Whenever you end a work session or complete a set of tasks:
1. Run git status and diff checks to verify what files were touched.
2. Run automated test suites:
   `$env:PYTHONPATH="backend"; .\backend\.venv\Scripts\python backend\test_document_extractor.py`
3. Update `HANDOFF.md` with:
   - Current commit hash and branch.
   - Summary of changes completed in the session.
   - Status of tests.
   - Immediate next steps and architectural decisions pending.
