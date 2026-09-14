"""
Offline Texas Statutory Corpus Database & Full-Text Search Service.
Maintains a local SQLite database (texas_codes.db) with FTS5 search
for zero-latency, zero-hallucination Texas statutory element lookups.
"""

import os
import json
import sqlite3
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "texas_codes.db")

# Seed Corpus for Texas Penal Code, Code of Criminal Procedure, and Health & Safety Code
INITIAL_TEXAS_STATUTES = [
    # --- Texas Code of Criminal Procedure ---
    {
        "code": "TEX. CODE CRIM. PROC. ART. 39.14",
        "chapter": "Chapter 39",
        "section": "39.14",
        "title": "Discovery (The Michael Morton Act)",
        "category": "Criminal Procedure - Discovery",
        "degree": "Procedural Mandate",
        "penalty_range": "Exclusion of evidence, mistrial, contempt, dismissal",
        "elements": [
            "Mandatory disclosure upon timely written defense request",
            "State must produce offense reports, witness statements, books, accounts, letters, photographs, tangible objects",
            "State must produce electronic recordings including body-worn camera (BWC) and dashcam footage",
            "State must produce 911 audio recordings and CAD dispatch call logs",
            "Affirmative continuous duty to disclose exculpatory, impeachment, or mitigating evidence (Brady material)",
            "Mandatory itemized written compliance inventory provided to defense counsel",
            "Defense prohibited under Art. 39.14(f) from providing physical unredacted copies to defendant (inspection only)"
        ],
        "summary": "Mandates open-file discovery in Texas criminal cases. The prosecution has an affirmative, continuing statutory duty to produce all offense reports, recorded statements, BWC/dashcam videos, and exculpatory evidence as soon as practicable upon request.",
        "full_text": "Article 39.14. DISCOVERY. (a) Subject to the restrictions provided by Section 264.408, Family Code, and Article 39.15 of this code, as soon as practicable after receiving a timely request from the defendant the state shall produce and permit the inspection and the electronic duplication, copying, and photographing, by or on behalf of the defendant, of any offense reports, any designated documents, papers, written or recorded statements of the defendant or a witness, including witness statements of law enforcement officers but not including the work product of counsel for the state in the case and their investigators and their notes or report, books, accounts, letters, photographs, or objects or other tangible things not privileged that constitute or contain evidence material to any matter involved in the action and that are in the possession, custody, or control of the state or any person under contract with the state.",
        "affirmative_defenses": ["Privileged work product of state counsel (strictly excludes police offense narratives)"]
    },
    {
        "code": "TEX. CODE CRIM. PROC. ART. 17.151",
        "chapter": "Chapter 17",
        "section": "17.151",
        "title": "Release on Bail Because of Delay",
        "category": "Bail & In-Custody Rights",
        "degree": "Mandatory Statutory Release",
        "penalty_range": "Mandatory release on personal bond or reduction of bail",
        "elements": [
            "Accused is detained in jail pending trial on an accusation of felony or misdemeanor",
            "State is not ready for trial within specified time limit from commencement of detention",
            "Time limits: 90 days for felony; 30 days for Class A misdemeanor; 15 days for Class B misdemeanor; 5 days for Class C misdemeanor",
            "State readiness requires a valid charging instrument (indictment or information) capable of supporting a trial"
        ],
        "summary": "A defendant detained in jail pending trial on a felony accusation must be released on personal bond or bail reduced to an amount they can afford if the State is not ready for trial within 90 days of arrest (30 days for Class A, 15 days for Class B).",
        "full_text": "Article 17.151. RELEASE ON BAIL BECAUSE OF DELAY. Sec. 1. A defendant who is detained in jail pending trial on an accusation against him must be released either on personal bond or by reducing the amount of bail required, if the state is not ready for trial of the accusation for which he is being detained within: (1) 90 days from the commencement of his detention if he is accused of a felony; (2) 30 days from the commencement of his detention if he is accused of a misdemeanor punishable by a sentence of imprisonment in jail for more than 180 days; (3) 15 days from the commencement of his detention if he is accused of a misdemeanor punishable by a sentence of imprisonment for 180 days or less.",
        "affirmative_defenses": ["Competency delay under Art. 46B", "Defendant requested continuance"]
    },
    {
        "code": "TEX. CODE CRIM. PROC. ART. 26.04",
        "chapter": "Chapter 26",
        "section": "26.04",
        "title": "Procedures for Appointing Counsel & 48-Hour Contact Rule",
        "category": "Indigent Defense & Appointment",
        "degree": "Statutory Appointment Directive",
        "penalty_range": "Removal from indigent appointment list, professional grievance",
        "elements": [
            "Court signs Order of Appointment designating qualified private attorney from county wheel",
            "Appointed attorney must make every reasonable effort to contact defendant by end of first working day after appointment",
            "Appointed attorney must interview the defendant as soon as practicable",
            "Attorney must maintain representation until charges dismissed, acquitted, appeals exhausted, or relieved by court"
        ],
        "summary": "Governs Texas Fair Defense Act indigent appointments. Appointed counsel must make reasonable effort to contact defendant not later than the end of the first working day after appointment, affirmed through filed Acceptance of Appointment.",
        "full_text": "Article 26.04. PROCEDURES FOR APPOINTING COUNSEL. (j) An attorney appointed under this article shall: (1) make every reasonable effort to contact the defendant not later than the end of the first working day after the date on which the attorney is appointed and to interview the defendant as soon as practicable after the attorney is appointed.",
        "affirmative_defenses": []
    },
    {
        "code": "TEX. CODE CRIM. PROC. ART. 26.05",
        "chapter": "Chapter 26",
        "section": "26.05",
        "title": "Compensation of Appointed Counsel (CJA Vouchers)",
        "category": "Indigent Defense Billing",
        "degree": "Judicial / County Mandate",
        "penalty_range": "County Auditor reimbursement",
        "elements": [
            "Reasonable attorney fee paid according to county indigent defense fee schedule",
            "Itemized statement of hours (in-court, out-of-court, trial preparation, client interviews)",
            "Review and approval by presiding trial judge",
            "Warrant issued by County Auditor after verification"
        ],
        "summary": "Governs voucher payment for court-appointed counsel. Texas law contains no statewide 30-day forfeiture rule; vouchers are paid in accordance with the local Nueces County fee schedule upon judicial approval.",
        "full_text": "Article 26.05. COMPENSATION OF COUNSEL APPOINTED TO DEFEND. (a) A counsel, other than an attorney with a public defender's office or an attorney employed by the office of capital and forensic writs, appointed to represent a defendant in a criminal proceeding, including a habeas corpus hearing, shall be paid a reasonable attorney's fee for performing the following services, based on the time and labor required, the complexity of the case, and the experience and ability of the appointed counsel.",
        "affirmative_defenses": []
    },
    {
        "code": "TEX. CODE CRIM. PROC. ART. 27.18",
        "chapter": "Chapter 27",
        "section": "27.18",
        "title": "Plea or Waiver of Arraignment by Attorney",
        "category": "Arraignment & Pleadings",
        "degree": "Pleading Procedure",
        "penalty_range": "Entry of Not Guilty plea on docket",
        "elements": [
            "Formal written statement signed by defendant or attorney of record",
            "Acknowledges receipt of indictment or information copy",
            "Waives formal reading of charging instrument in open court",
            "Enters plea of Not Guilty and requests pre-trial/trial settings"
        ],
        "summary": "Permits defense counsel to file a written Waiver of Arraignment and entry of Not Guilty plea, excusing defendant's physical appearance at formal arraignment call.",
        "full_text": "Article 27.18. PLEA OR WAIVER OF ARRAIGNMENT. An attorney representing the defendant in a criminal case may file a written waiver of arraignment. The waiver must be signed by the defendant or the attorney and state that the defendant has received a copy of the indictment or information and waives formal arraignment.",
        "affirmative_defenses": []
    },
    {
        "code": "TEX. CODE CRIM. PROC. ART. 38.22",
        "chapter": "Chapter 38",
        "section": "38.22",
        "title": "When Statements May Be Used (Strict Custodial Interrogation Recording)",
        "category": "Suppression & Evidence",
        "degree": "Statutory Exclusionary Rule",
        "penalty_range": "Mandatory suppression of oral custodial statements",
        "elements": [
            "Applies to oral statements made as a result of custodial interrogation",
            "Electronic recording (audio and visual) must be made of statement",
            "Statutory Miranda-style warnings under Section 2(a) must be given ON THE RECORDING prior to statement",
            "Accused must knowingly, intelligently, and voluntarily waive rights on the recording",
            "Recording device must be capable of accurate recording and operator competent",
            "All voices on recording must be identified",
            "Defense counsel must be provided accurate copy of recording not later than 20th day before proceeding"
        ],
        "summary": "In Texas, no oral statement made as a result of custodial interrogation is admissible against the defendant in a criminal proceeding unless an electronic audio-visual recording was made with statutory warnings administered on tape.",
        "full_text": "Article 38.22. WHEN STATEMENTS MAY BE USED. Sec. 3. (a) No oral or sign language statement of an accused made as a result of custodial interrogation shall be admissible against the accused in a criminal proceeding unless: (1) an electronic recording, which may include motion picture, video tape, or other visual recording, is made of the statement; (2) prior to the statement but during the recording the accused is given the warning in Subsection (a) of Section 2 above and the accused knowingly, intelligently, and voluntarily waives any rights set out in the warning.",
        "affirmative_defenses": ["Res gestae statement", "Statement made before magistrate in open court"]
    },
    {
        "code": "TEX. CODE CRIM. PROC. ART. 38.23",
        "chapter": "Chapter 38",
        "section": "38.23",
        "title": "Evidence Not to Be Used (Texas Statutory Exclusionary Rule)",
        "category": "Suppression & Exclusionary Rule",
        "degree": "Constitutional & Statutory Exclusion",
        "penalty_range": "Mandatory suppression of unlawfully obtained evidence",
        "elements": [
            "Evidence obtained by an officer or other person in violation of any provisions of the Constitution or laws of the State of Texas or United States",
            "Broader than Federal 4th Amendment exclusionary rule (applies to statutory violations, not merely constitutional)",
            "Jury instruction mandatory if fact issue exists as to legality of police conduct"
        ],
        "summary": "Texas statutory exclusionary rule. Broader than the Federal Fourth Amendment: any evidence obtained in violation of any law or constitution of Texas or the US is strictly inadmissible. If a factual dispute exists, the jury must be instructed to disregard the evidence.",
        "full_text": "Article 38.23. EVIDENCE NOT TO BE USED. (a) No evidence obtained by an officer or other person in violation of any provisions of the Constitution or laws of the State of Texas, or of the Constitution or laws of the United States of America, shall be admitted in evidence against the accused on the trial of any criminal case.",
        "affirmative_defenses": ["Good faith reliance on search warrant issued by neutral magistrate based on probable cause"]
    },

    # --- Texas Penal Code ---
    {
        "code": "TEX. PENAL CODE § 22.01",
        "chapter": "Chapter 22",
        "section": "22.01",
        "title": "Assault (Including Family Violence)",
        "category": "Offenses Against the Person",
        "degree": "Class A Misdemeanor (Enhanceable to 3rd or 2nd Degree Felony)",
        "penalty_range": "Class A: up to 1 year jail / $4,000 fine. 3rd Degree: 2-10 years TDCJ.",
        "elements": [
            "A person intentionally, knowingly, or recklessly causes bodily injury to another (including spouse)",
            "OR intentionally or knowingly threatens another with imminent bodily injury",
            "OR intentionally or knowingly causes physical contact with another when the person knows or should reasonably believe that the other will regard the contact as offensive or provocative",
            "Enhancement to 3rd Degree Felony: committed against person whose relationship is family/dating/household AND previously convicted of assault family violence OR committed by intentionally, knowingly, or recklessly impeding normal breathing or circulation (choking)"
        ],
        "summary": "Intentionally, knowingly, or recklessly causing bodily injury to another. Baseline Class A Misdemeanor; enhanced to 3rd Degree Felony if committed against family/dating partner with prior conviction or by impeding breath/circulation.",
        "full_text": "Sec. 22.01. ASSAULT. (a) A person commits an offense if the person: (1) intentionally, knowingly, or recklessly causes bodily injury to another, including the person's spouse; (2) intentionally or knowingly threatens another with imminent bodily injury, including the person's spouse; or (3) intentionally or knowingly causes physical contact with another when the person knows or should reasonably believe that the other will regard the contact as offensive or provocative.",
        "affirmative_defenses": ["Self-defense (Tex. Penal Code § 9.31)", "Defense of third person (Tex. Penal Code § 9.32)", "Consent (Tex. Penal Code § 22.06)"]
    },
    {
        "code": "TEX. PENAL CODE § 22.02",
        "chapter": "Chapter 22",
        "section": "22.02",
        "title": "Aggravated Assault",
        "category": "Offenses Against the Person",
        "degree": "Second Degree Felony (Enhanceable to 1st Degree Felony)",
        "penalty_range": "2nd Degree: 2-20 years TDCJ / $10,000 fine. 1st Degree: 5-99 years or Life.",
        "elements": [
            "A person commits assault as defined in Section 22.01",
            "AND causes serious bodily injury to another",
            "OR uses or exhibits a deadly weapon during the commission of the assault",
            "Enhancement to 1st Degree Felony: committed against public servant, security officer, or family member with deadly weapon causing serious bodily injury"
        ],
        "summary": "Assault causing serious bodily injury or involving the use or exhibition of a deadly weapon. Second Degree Felony; enhanced to First Degree Felony under specified aggravating circumstances.",
        "full_text": "Sec. 22.02. AGGRAVATED ASSAULT. (a) A person commits an offense if the person commits assault as defined in Sec. 22.01 and the person: (1) causes serious bodily injury to another, including the person's spouse; or (2) uses or exhibits a deadly weapon during the commission of the assault.",
        "affirmative_defenses": ["Self-defense with deadly force (Tex. Penal Code § 9.32)", "Defense of property (Tex. Penal Code § 9.42)"]
    },
    {
        "code": "TEX. PENAL CODE § 49.04",
        "chapter": "Chapter 49",
        "section": "49.04",
        "title": "Driving While Intoxicated (DWI)",
        "category": "Intoxication Offenses",
        "degree": "Class B Misdemeanor (Class A if BAC >= 0.15; 3rd Degree Felony on 3rd offense)",
        "penalty_range": "Class B: 72h-180 days jail. Class A: up to 1 year jail. 3rd Degree: 2-10 years TDCJ.",
        "elements": [
            "A person operates a motor vehicle in a public place",
            "AND is intoxicated (loss of normal use of mental or physical faculties OR alcohol concentration >= 0.08)",
            "Class A Enhancement: alcohol concentration analysis shows an alcohol concentration of 0.15 or more at the time the analysis was performed",
            "Third Degree Felony: defendant has previously been convicted two times of any other offense relating to the operating of a motor vehicle while intoxicated"
        ],
        "summary": "Operating a motor vehicle in a public place while intoxicated. Baseline Class B Misdemeanor (mandatory 72h minimum confinement); enhanced to Class A if BAC >= 0.15; enhanced to 3rd Degree Felony if defendant has 2 prior DWI convictions.",
        "full_text": "Sec. 49.04. DRIVING WHILE INTOXICATED. (a) A person commits an offense if the person is intoxicated while operating a motor vehicle in a public place. (b) Except as provided by Subsections (c) and (d) and Section 49.09, an offense under this section is a Class B misdemeanor, with a minimum term of confinement of 72 hours. (d) If it is shown on the trial of an offense under this section that an analysis of a specimen of the person's blood, breath, or urine showed an alcohol concentration level of 0.15 or more at the time the analysis was performed, the offense is a Class A misdemeanor.",
        "affirmative_defenses": ["Involuntary intoxication", "Rising BAC / retrograde extrapolation defect", "Breathalyzer operator calibration non-compliance"]
    },
    {
        "code": "TEX. PENAL CODE § 38.04",
        "chapter": "Chapter 38",
        "section": "38.04",
        "title": "Evading Arrest or Detention",
        "category": "Obstruction of Justice",
        "degree": "Class A Misdemeanor (State Jail Felony if prior; 3rd Degree if vehicle used)",
        "penalty_range": "Class A: up to 1 year jail. 3rd Degree: 2-10 years TDCJ.",
        "elements": [
            "A person intentionally flees from a person he knows is a peace officer or federal special investigator",
            "The peace officer is attempting lawfully to arrest or detain him",
            "Enhancement: State Jail Felony if defendant has prior conviction under § 38.04",
            "Enhancement: Third Degree Felony if defendant uses a vehicle while in flight"
        ],
        "summary": "Intentionally fleeing from a known peace officer who is lawfully attempting to arrest or detain the person. Class A Misdemeanor on foot; enhanced to 3rd Degree Felony if a motor vehicle is used.",
        "full_text": "Sec. 38.04. EVADING ARREST OR DETENTION. (a) A person commits an offense if he intentionally flees from a person he knows is a peace officer or federal special investigator attempting lawfully to arrest or detain him. (b) An offense under this section is a Class A misdemeanor, except that the offense is: (1) a state jail felony if the actor has been previously convicted under this section; (2) a felony of the third degree if: (A) the actor uses a vehicle or watercraft while the actor is in flight.",
        "affirmative_defenses": ["Detention or attempted arrest was unlawful", "Lack of knowledge that pursuer was a peace officer"]
    },
    {
        "code": "TEX. HEALTH & SAFETY CODE § 481.115",
        "chapter": "Chapter 481",
        "section": "481.115",
        "title": "Possession of Controlled Substance in Penalty Group 1 / 1-B",
        "category": "Controlled Substances",
        "degree": "State Jail Felony to First Degree Felony",
        "penalty_range": "<1g: 180 days-2 years SJF. 1-4g: 2-10 years (3rd Deg). 4-200g: 2-20 years (2nd Deg).",
        "elements": [
            "A person knowingly or intentionally possesses a controlled substance listed in Penalty Group 1 or Penalty Group 1-B (cocaine, heroin, methamphetamine, fentanyl)",
            "Thresholds: Less than 1 gram = State Jail Felony",
            "1 gram or more but less than 4 grams = Third Degree Felony",
            "4 grams or more but less than 200 grams = Second Degree Felony",
            "200 grams or more but less than 400 grams = First Degree Felony",
            "Affirmative link required: defendant exercised actual care, custody, control, or management and knew substance was contraband"
        ],
        "summary": "Possession of PG 1 or PG 1-B substances (cocaine, methamphetamine, fentanyl). Under 1 gram is a State Jail Felony; 1-4 grams is 3rd Degree; 4-200 grams is 2nd Degree. The State must prove affirmative links showing knowledge and control.",
        "full_text": "Sec. 481.115. OFFENSE: POSSESSION OF SUBSTANCE IN PENALTY GROUP 1 OR 1-B. (a) Except as authorized by this chapter, a person commits an offense if the person knowingly or intentionally possesses a controlled substance listed in Penalty Group 1 or 1-B, unless the person obtained the substance directly from or under a valid prescription or order of a practitioner acting in the course of professional practice.",
        "affirmative_defenses": ["Valid prescription", "Lack of care, custody, or control (mere presence)", "Illegal warrantless search under Art. 38.23"]
    }
]


class TexasStatutesService:
    """Service to query the offline SQLite Texas Statutory Corpus."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._ensure_database()

    def _ensure_database(self):
        """Creates and populates the SQLite database with FTS5 index if missing or empty."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS statutes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            chapter TEXT,
            section TEXT,
            title TEXT NOT NULL,
            category TEXT,
            degree TEXT,
            penalty_range TEXT,
            elements_json TEXT,
            summary TEXT,
            full_text TEXT,
            affirmative_defenses_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # FTS5 Virtual Table for high-performance zero-latency search
        cursor.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS statutes_fts USING fts5(
            code,
            title,
            category,
            degree,
            summary,
            full_text,
            content=statutes,
            content_rowid=id
        );
        """)

        # Check if table already populated
        cursor.execute("SELECT COUNT(*) FROM statutes")
        count = cursor.fetchone()[0]

        if count == 0:
            for item in INITIAL_TEXAS_STATUTES:
                cursor.execute("""
                INSERT INTO statutes (
                    code, chapter, section, title, category, degree, penalty_range,
                    elements_json, summary, full_text, affirmative_defenses_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    item["code"],
                    item["chapter"],
                    item["section"],
                    item["title"],
                    item["category"],
                    item["degree"],
                    item["penalty_range"],
                    json.dumps(item["elements"]),
                    item["summary"],
                    item["full_text"],
                    json.dumps(item["affirmative_defenses"])
                ))
                row_id = cursor.lastrowid
                cursor.execute("""
                INSERT INTO statutes_fts (rowid, code, title, category, degree, summary, full_text)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    row_id,
                    item["code"],
                    item["title"],
                    item["category"],
                    item["degree"],
                    item["summary"],
                    item["full_text"]
                ))
            conn.commit()

        cursor.close()
        conn.close()

    def search_statutes(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Searches Texas statutes using FTS5 full-text search with fallback to LIKE."""
        if not query or not query.strip():
            return self.get_all_statutes()

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        results = []
        clean_q = query.replace('"', '""').strip()

        # FTS5 Match
        try:
            fts_sql = """
            SELECT s.*, rank
            FROM statutes_fts f
            JOIN statutes s ON s.id = f.rowid
            WHERE statutes_fts MATCH ?
            ORDER BY rank
            LIMIT ?;
            """
            cursor.execute(fts_sql, (f"{clean_q}*", limit))
            for row in cursor.fetchall():
                results.append(self._row_to_dict(row))
        except Exception:
            # Fallback to standard LIKE if query syntax was unusual
            like_sql = """
            SELECT * FROM statutes
            WHERE code LIKE ? OR title LIKE ? OR summary LIKE ? OR full_text LIKE ?
            LIMIT ?;
            """
            param = f"%{clean_q}%"
            cursor.execute(like_sql, (param, param, param, param, limit))
            for row in cursor.fetchall():
                results.append(self._row_to_dict(row))

        cursor.close()
        conn.close()
        return results

    def get_statute_by_code(self, code_str: str) -> Optional[Dict[str, Any]]:
        """Exact lookup by statute code (e.g. 'TEX. CODE CRIM. PROC. ART. 39.14' or '39.14' or '22.01')."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM statutes WHERE UPPER(code) = ? OR section = ?", (code_str.upper().strip(), code_str.strip()))
        row = cursor.fetchone()
        if not row:
            # Fuzzy section match
            cursor.execute("SELECT * FROM statutes WHERE code LIKE ?", (f"%{code_str.strip()}%",))
            row = cursor.fetchone()

        cursor.close()
        conn.close()
        return self._row_to_dict(row) if row else None

    def get_all_statutes(self) -> List[Dict[str, Any]]:
        """Returns all statutes in the local corpus."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM statutes ORDER BY category, code")
        results = [self._row_to_dict(r) for r in cursor.fetchall()]

        cursor.close()
        conn.close()
        return results

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Converts an SQLite row into a clean dictionary."""
        d = dict(row)
        d["elements"] = json.loads(d.get("elements_json") or "[]")
        d["affirmative_defenses"] = json.loads(d.get("affirmative_defenses_json") or "[]")
        return d


# Singleton service instance
texas_statutes_service = TexasStatutesService()
