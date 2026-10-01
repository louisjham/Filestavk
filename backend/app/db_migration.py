"""
Database schema auto-migration utility for SQLite.
Ensures newly added columns in SQLAlchemy models are automatically added to existing tables.
"""

from sqlalchemy import text


def sync_migrate_sqlite_schema(conn):
    """Inspects SQLite PRAGMA table_info and adds missing columns dynamically."""
    tables_columns = {
        "cases": [
            ("client_id", "INTEGER"),
            ("case_number", "VARCHAR"),
            ("court", "VARCHAR"),
            ("judge", "VARCHAR"),
            ("case_type", "VARCHAR"),
            ("charge_description", "VARCHAR"),
            ("status", "VARCHAR"),
            ("stage", "VARCHAR DEFAULT 'DISCOVERY'"),
            ("is_cja", "BOOLEAN DEFAULT 0"),
            ("in_custody", "BOOLEAN DEFAULT 0"),
            ("jail_booking_date", "VARCHAR"),
            ("jail_facility", "VARCHAR DEFAULT 'Nueces County Jail - Main'"),
            ("voucher_status", "VARCHAR DEFAULT 'NONE'"),
            ("bond_amount", "FLOAT"),
            ("bond_type", "VARCHAR"),
            ("bond_conditions", "TEXT"),
            ("morton_discovery_json", "TEXT"),
            ("has_appointment_order", "BOOLEAN DEFAULT 0"),
            ("appointment_order_date", "VARCHAR"),
            ("has_appointment_acceptance", "BOOLEAN DEFAULT 0"),
            ("acceptance_filed_date", "VARCHAR"),
            ("client_contact_date", "VARCHAR"),
            ("appointment_status", "VARCHAR DEFAULT 'UNKNOWN'"),
            ("appellate_case_number", "VARCHAR"),
            ("trial_court_case_number", "VARCHAR"),
            ("appellate_court", "VARCHAR"),
            ("appellate_brief_due_date", "VARCHAR"),
            ("appellate_extension_count", "INTEGER DEFAULT 0"),
            ("appellate_extension_reason", "TEXT"),
            ("appellate_motion_status", "VARCHAR"),
            ("disposition_type", "VARCHAR"),
            ("disposition_date", "VARCHAR"),
            ("source_spreadsheet_row_id", "VARCHAR"),
            ("opened_date", "VARCHAR"),
            ("closed_date", "VARCHAR"),
            ("notes", "TEXT"),
        ],
        "clients": [
            ("name", "VARCHAR"),
            ("dob", "VARCHAR"),
            ("address", "VARCHAR"),
            ("phone", "VARCHAR"),
            ("email", "VARCHAR"),
            ("notes", "TEXT"),
        ],
        "documents": [
            ("case_id", "INTEGER"),
            ("client_id", "INTEGER"),
            ("filename", "VARCHAR"),
            ("filepath", "VARCHAR"),
            ("doc_type", "VARCHAR"),
            ("source", "VARCHAR"),
            ("content_text", "TEXT"),
            ("metadata_json", "TEXT"),
            ("classification_label", "VARCHAR"),
            ("classification_confidence", "FLOAT"),
            ("ingested_at", "DATETIME"),
        ],
        "vouchers": [
            ("case_id", "INTEGER"),
            ("voucher_number", "VARCHAR"),
            ("voucher_type", "VARCHAR DEFAULT 'CJA-FELONY'"),
            ("submission_method", "VARCHAR DEFAULT 'ONLINE_PORTAL'"),
            ("status", "VARCHAR DEFAULT 'DRAFT'"),
            ("has_appointment_order_verified", "BOOLEAN DEFAULT 0"),
            ("amount_requested", "FLOAT DEFAULT 0.0"),
            ("amount_approved", "FLOAT"),
            ("amount_paid", "FLOAT"),
            ("disposition_date", "VARCHAR"),
            ("submitted_date", "VARCHAR"),
            ("approved_date", "VARCHAR"),
            ("paid_date", "VARCHAR"),
            ("warrant_number", "VARCHAR"),
            ("rejection_reason", "VARCHAR"),
            ("itemized_json", "TEXT"),
            ("notes", "TEXT"),
        ],
        "document_rules": [
            ("document_type", "VARCHAR UNIQUE"),
            ("display_name", "VARCHAR"),
            ("description", "TEXT"),
            ("lifecycle_stage", "VARCHAR DEFAULT 'Pretrial - Magistrate Hearing'"),
            ("target_case_stage", "VARCHAR DEFAULT 'MAGISTRATE_HEARING'"),
            ("target_case_status", "VARCHAR DEFAULT 'open'"),
            ("is_cja_default", "BOOLEAN DEFAULT 1"),
            ("set_has_appointment_order", "BOOLEAN DEFAULT 0"),
            ("set_has_appointment_acceptance", "BOOLEAN DEFAULT 0"),
            ("set_appointment_status", "VARCHAR DEFAULT 'UNKNOWN'"),
            ("auto_populate_client", "BOOLEAN DEFAULT 1"),
            ("auto_populate_case", "BOOLEAN DEFAULT 1"),
            ("create_docket_event", "BOOLEAN DEFAULT 1"),
            ("event_type", "VARCHAR DEFAULT 'order'"),
            ("event_title_template", "VARCHAR"),
            ("event_desc_template", "TEXT"),
            ("trigger_statutory_deadline", "BOOLEAN DEFAULT 0"),
            ("statutory_basis", "VARCHAR"),
            ("deadline_name", "VARCHAR"),
            ("deadline_hours_offset", "INTEGER DEFAULT 48"),
            ("confidence_threshold", "FLOAT DEFAULT 0.70"),
            ("require_human_verification", "BOOLEAN DEFAULT 0"),
            ("is_active", "BOOLEAN DEFAULT 1"),
            ("custom_actions_json", "TEXT DEFAULT '{}'"),
            ("updated_at", "DATETIME"),
            ("created_at", "DATETIME"),
        ],
        "extraction_sub_rules": [
            ("document_type", "VARCHAR"),
            ("field_name", "VARCHAR"),
            ("rule_type", "VARCHAR DEFAULT 'REGEX_PATTERN'"),
            ("pattern_or_value", "TEXT"),
            ("sample_text_snippet", "TEXT"),
            ("capture_group", "INTEGER DEFAULT 1"),
            ("is_active", "BOOLEAN DEFAULT 1"),
            ("learned_from_doc_id", "INTEGER"),
            ("created_by", "VARCHAR DEFAULT 'attorney'"),
            ("created_at", "DATETIME"),
            ("updated_at", "DATETIME"),
        ],
    }

    # Ensure extraction_sub_rules table exists
    try:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS extraction_sub_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_type VARCHAR NOT NULL,
                field_name VARCHAR NOT NULL,
                rule_type VARCHAR DEFAULT 'REGEX_PATTERN',
                pattern_or_value TEXT NOT NULL,
                sample_text_snippet TEXT,
                capture_group INTEGER DEFAULT 1,
                is_active BOOLEAN DEFAULT 1,
                learned_from_doc_id INTEGER,
                created_by VARCHAR DEFAULT 'attorney',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """))
    except Exception:
        pass

    for table, cols in tables_columns.items():
        try:
            res = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
            existing_col_names = {row[1] for row in res}
            if not existing_col_names:
                continue
            for col_name, col_type in cols:
                if col_name not in existing_col_names:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type}"))
        except Exception:
            pass
