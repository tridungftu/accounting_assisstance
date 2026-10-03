"""Append-only migrations for M2-M6. Existing M1 migration bytes remain unchanged."""

FEATURE_MIGRATIONS = (
    (
        """CREATE TABLE knowledge_versions (
            id TEXT PRIMARY KEY, category TEXT NOT NULL, logical_key TEXT NOT NULL, revision INTEGER NOT NULL,
            payload_json TEXT NOT NULL, content_hash TEXT NOT NULL, valid_from TEXT NOT NULL, valid_to TEXT,
            known_at TEXT NOT NULL, evidence_json TEXT NOT NULL, supersedes_id TEXT REFERENCES knowledge_versions(id),
            created_at TEXT NOT NULL, actor TEXT NOT NULL, UNIQUE(category,logical_key,revision))""",
        """CREATE TABLE knowledge_events (
            id INTEGER PRIMARY KEY, version_id TEXT NOT NULL REFERENCES knowledge_versions(id),
            action TEXT NOT NULL CHECK(action IN ('APPROVE','REVOKE')), event_at TEXT NOT NULL,
            actor TEXT NOT NULL, reason TEXT NOT NULL)""",
        """CREATE TABLE historical_links (
            id TEXT PRIMARY KEY, source_id TEXT NOT NULL REFERENCES documents(id), target_id TEXT NOT NULL REFERENCES documents(id),
            level TEXT NOT NULL CHECK(level IN ('LINK_A','LINK_B','LINK_C')), evidence_json TEXT NOT NULL,
            known_at TEXT NOT NULL, checked_at TEXT, checker TEXT, UNIQUE(source_id,target_id,known_at))""",
        """CREATE TABLE activity_log (
            id INTEGER PRIMARY KEY, module TEXT NOT NULL, action TEXT NOT NULL, subject_id TEXT,
            actor TEXT NOT NULL, event_at TEXT NOT NULL, recorded_at TEXT NOT NULL, details_json TEXT NOT NULL)""",
    ),
    (
        """CREATE TABLE sessions (
            id TEXT PRIMARY KEY, mode TEXT NOT NULL CHECK(mode IN ('fixture','shadow','backtest')),
            state TEXT NOT NULL CHECK(state IN ('OPEN','PREPARING','CLOSED','CANCELLED')),
            cutoff TEXT NOT NULL, source_attempt_id TEXT NOT NULL REFERENCES attempts(id), snapshot_id TEXT NOT NULL,
            bank_ids_json TEXT NOT NULL, knowledge_ids_json TEXT NOT NULL,
            actor TEXT NOT NULL, opened_at TEXT NOT NULL, closed_at TEXT, reason TEXT)""",
        "CREATE UNIQUE INDEX single_active_session ON sessions((1)) WHERE state IN ('OPEN','PREPARING')",
        """CREATE TABLE proposals (
            id TEXT PRIMARY KEY, session_id TEXT NOT NULL REFERENCES sessions(id), bank_id TEXT NOT NULL REFERENCES documents(id),
            revision INTEGER NOT NULL, state TEXT NOT NULL, payload_json TEXT NOT NULL,
            created_at TEXT NOT NULL, UNIQUE(session_id,bank_id))""",
        """CREATE TABLE allocations (
            id TEXT PRIMARY KEY, proposal_id TEXT NOT NULL REFERENCES proposals(id),
            open_item_id TEXT NOT NULL REFERENCES documents(id), item_key TEXT NOT NULL,
            amount_minor INTEGER NOT NULL CHECK(amount_minor>0), state TEXT NOT NULL
            CHECK(state IN ('RESERVED','APPROVED','EXPORTED','POSTED','CANCELLED')),
            UNIQUE(proposal_id,open_item_id))""",
    ),
    (
        """CREATE TABLE review_workbooks (
            id TEXT PRIMARY KEY, session_id TEXT NOT NULL REFERENCES sessions(id),
            baseline_json TEXT NOT NULL, artifact_hash TEXT NOT NULL REFERENCES artifacts(hash),
            created_at TEXT NOT NULL, actor TEXT NOT NULL)""",
        """CREATE TABLE review_imports (
            artifact_hash TEXT PRIMARY KEY REFERENCES artifacts(hash), workbook_id TEXT NOT NULL REFERENCES review_workbooks(id),
            result_json TEXT NOT NULL, imported_at TEXT NOT NULL, actor TEXT NOT NULL)""",
        """CREATE TABLE decisions (
            id TEXT PRIMARY KEY, proposal_id TEXT NOT NULL REFERENCES proposals(id), revision INTEGER NOT NULL,
            action TEXT NOT NULL CHECK(action IN ('APPROVE','REJECT')), payload_json TEXT NOT NULL,
            reason TEXT NOT NULL, actor TEXT NOT NULL, decided_at TEXT NOT NULL,
            UNIQUE(proposal_id,revision))""",
        """CREATE TABLE export_batches (
            id TEXT PRIMARY KEY, session_id TEXT NOT NULL UNIQUE REFERENCES sessions(id),
            state TEXT NOT NULL CHECK(state IN ('PREPARING','EXPORTED','PARTIALLY_VERIFIED','VERIFIED')),
            target TEXT NOT NULL CHECK(target='fixture'), artifact_hash TEXT NOT NULL REFERENCES artifacts(hash),
            manifest_hash TEXT NOT NULL REFERENCES artifacts(hash), relative_path TEXT NOT NULL,
            prepared_at TEXT NOT NULL, exported_at TEXT, actor TEXT NOT NULL)""",
        """CREATE TABLE export_items (
            id TEXT PRIMARY KEY, batch_id TEXT NOT NULL REFERENCES export_batches(id),
            proposal_id TEXT NOT NULL UNIQUE REFERENCES proposals(id), decision_id TEXT NOT NULL REFERENCES decisions(id),
            payload_json TEXT NOT NULL, verification_state TEXT NOT NULL DEFAULT 'UNVERIFIED')""",
        """CREATE TABLE expected_balances (
            batch_id TEXT NOT NULL REFERENCES export_batches(id), item_key TEXT NOT NULL,
            source_open_item_id TEXT NOT NULL REFERENCES documents(id), before_minor INTEGER NOT NULL,
            delta_minor INTEGER NOT NULL, expected_minor INTEGER NOT NULL,
            PRIMARY KEY(batch_id,item_key))""",
    ),
    (
        """CREATE TABLE verification_runs (
            id TEXT PRIMARY KEY, batch_id TEXT NOT NULL REFERENCES export_batches(id),
            source_attempt_id TEXT NOT NULL REFERENCES attempts(id), source_hash TEXT NOT NULL,
            verified_at TEXT NOT NULL, actor TEXT NOT NULL, report_json TEXT NOT NULL,
            UNIQUE(batch_id,source_hash))""",
        """CREATE TABLE field_verifications (
            run_id TEXT NOT NULL REFERENCES verification_runs(id), export_item_id TEXT NOT NULL REFERENCES export_items(id),
            fields_json TEXT NOT NULL, evidence_json TEXT NOT NULL, status TEXT NOT NULL,
            PRIMARY KEY(run_id,export_item_id))""",
        """CREATE TABLE labels (
            id TEXT PRIMARY KEY, bank_id TEXT NOT NULL REFERENCES documents(id), revision INTEGER NOT NULL,
            fields_json TEXT NOT NULL, verified_fields_json TEXT NOT NULL, context_json TEXT NOT NULL,
            amount_minor INTEGER NOT NULL, known_at TEXT NOT NULL, verified_at TEXT NOT NULL, eligible_at TEXT NOT NULL,
            valid_from TEXT NOT NULL, valid_to TEXT, evidence_json TEXT NOT NULL,
            origin TEXT NOT NULL, verifier TEXT NOT NULL, UNIQUE(bank_id,revision))""",
        """CREATE TABLE label_events (
            id INTEGER PRIMARY KEY, label_id TEXT NOT NULL REFERENCES labels(id),
            action TEXT NOT NULL CHECK(action IN ('ACTIVATE','REVOKE','SUPERSEDE')),
            event_at TEXT NOT NULL, actor TEXT NOT NULL, reason TEXT NOT NULL)""",
        """CREATE TABLE learning_runs (
            id TEXT PRIMARY KEY, cutoff TEXT NOT NULL, context_json TEXT NOT NULL,
            fingerprint TEXT NOT NULL UNIQUE, report_json TEXT NOT NULL, created_at TEXT NOT NULL)""",
    ),
    (
        """CREATE TABLE evaluation_datasets (
            id TEXT PRIMARY KEY, version TEXT NOT NULL, artifact_hash TEXT NOT NULL REFERENCES artifacts(hash),
            manifest_json TEXT NOT NULL, UNIQUE(id,version))""",
        """CREATE TABLE quality_runs (
            id TEXT PRIMARY KEY, dataset_id TEXT NOT NULL REFERENCES evaluation_datasets(id),
            fingerprint TEXT NOT NULL UNIQUE, report_json TEXT NOT NULL, created_at TEXT NOT NULL)""",
        """CREATE TABLE month_closures (
            month TEXT PRIMARY KEY, source_attempt_id TEXT NOT NULL REFERENCES attempts(id),
            actor TEXT NOT NULL, closed_at TEXT NOT NULL, evidence_json TEXT NOT NULL)""",
    ),
    (
        "ALTER TABLE export_batches ADD COLUMN cancelled_at TEXT",
        "ALTER TABLE export_batches ADD COLUMN cancelled_by TEXT",
        "ALTER TABLE export_batches ADD COLUMN cancellation_reason TEXT",
    ),
    (
        """CREATE INDEX knowledge_policy_rank ON knowledge_versions
            (category, json_extract(payload_json,'$.partition'), json_extract(payload_json,'$.tier'), json_extract(payload_json,'$.order'))
            WHERE category='POLICY' AND json_extract(payload_json,'$.contract_version')=2""",
        "CREATE TABLE knowledge_epoch (id INTEGER PRIMARY KEY CHECK(id=1), revision TEXT NOT NULL)",
        "INSERT INTO knowledge_epoch VALUES (1,'initial')",
        *tuple(f"CREATE TRIGGER knowledge_epoch_{table}_{event.lower()} AFTER {event} ON {table} BEGIN UPDATE knowledge_epoch SET revision=lower(hex(randomblob(16))) WHERE id=1; END"
               for table in ('knowledge_versions', 'knowledge_events') for event in ('INSERT', 'UPDATE', 'DELETE')),
    ),
    (
        "ALTER TABLE proposals ADD COLUMN lines_json TEXT NOT NULL DEFAULT '[]'",
        "ALTER TABLE decisions ADD COLUMN lines_json TEXT NOT NULL DEFAULT '[]'",
        "ALTER TABLE export_items ADD COLUMN line_checksum TEXT NOT NULL DEFAULT ''",
        """CREATE TABLE export_item_lines (
            id TEXT PRIMARY KEY, export_item_id TEXT NOT NULL REFERENCES export_items(id), line_no INTEGER NOT NULL,
            account TEXT NOT NULL, debit_minor INTEGER NOT NULL DEFAULT 0, credit_minor INTEGER NOT NULL DEFAULT 0,
            tax_rate TEXT, tax_basis TEXT, state TEXT NOT NULL CHECK(state IN ('READY','WAIT_TAX_EVIDENCE')),
            payload_json TEXT NOT NULL, line_hash TEXT NOT NULL, UNIQUE(export_item_id,line_no))""",
        """CREATE TABLE document_observations (
            document_id TEXT NOT NULL REFERENCES documents(id), source_record_id TEXT NOT NULL REFERENCES source_records(id),
            source TEXT NOT NULL, observed_core_json TEXT NOT NULL, observed_hash TEXT NOT NULL,
            known_at TEXT, status TEXT NOT NULL CHECK(status IN ('MATCHED','WARNING_MONEY_CONFLICT','QUARANTINED')),
            PRIMARY KEY(document_id,source_record_id))""",
        "CREATE INDEX document_observations_document ON document_observations(document_id,source,status)",
    ),
    (
        """CREATE TABLE knowledge_import_batches (
            id TEXT PRIMARY KEY, artifact_hash TEXT NOT NULL REFERENCES artifacts(hash), source_json TEXT NOT NULL,
            known_at TEXT NOT NULL, actor TEXT NOT NULL, created_at TEXT NOT NULL, UNIQUE(artifact_hash,known_at))""",
        """CREATE TABLE knowledge_workbooks (
            id TEXT PRIMARY KEY, baseline_hash TEXT NOT NULL, artifact_hash TEXT NOT NULL REFERENCES artifacts(hash),
            created_at TEXT NOT NULL, actor TEXT NOT NULL)""",
        """CREATE TABLE knowledge_review_requests (
            id TEXT PRIMARY KEY, workbook_id TEXT NOT NULL REFERENCES knowledge_workbooks(id),
            knowledge_version_id TEXT NOT NULL REFERENCES knowledge_versions(id), action TEXT NOT NULL CHECK(action IN ('APPROVE_REQUEST','REVOKE_REQUEST')),
            note TEXT NOT NULL, requested_at TEXT NOT NULL, actor TEXT NOT NULL,
            UNIQUE(workbook_id,knowledge_version_id,action))""",
    ),
    (
        "CREATE INDEX knowledge_visibility_query ON knowledge_versions(category,logical_key,valid_from,valid_to,known_at)",
        "CREATE INDEX knowledge_events_cutoff ON knowledge_events(event_at,version_id,action)",
        "CREATE INDEX open_item_candidate_lookup ON documents(kind,currency,business_date)",
    ),
    (
        """CREATE TABLE shadow_exports (
            id TEXT PRIMARY KEY, session_id TEXT NOT NULL UNIQUE REFERENCES sessions(id), state TEXT NOT NULL CHECK(state='SHADOW_PREPARED'),
            manifest_hash TEXT NOT NULL REFERENCES artifacts(hash), thu_hash TEXT NOT NULL REFERENCES artifacts(hash), chi_hash TEXT NOT NULL REFERENCES artifacts(hash),
            prepared_at TEXT NOT NULL, actor TEXT NOT NULL)""",
    ),
    (
        """CREATE TABLE shadow_verification_runs (
            id TEXT PRIMARY KEY, shadow_id TEXT NOT NULL REFERENCES shadow_exports(id), source_attempt_id TEXT NOT NULL REFERENCES attempts(id),
            source_hash TEXT NOT NULL, verified_at TEXT NOT NULL, actor TEXT NOT NULL, report_json TEXT NOT NULL,
            UNIQUE(shadow_id,source_hash))""",
    ),
    (
        """CREATE TABLE quarantine_records (
            attempt_id TEXT NOT NULL REFERENCES attempts(id), ordinal INTEGER NOT NULL,
            code TEXT NOT NULL, message TEXT NOT NULL, raw_hash TEXT NOT NULL,
            PRIMARY KEY(attempt_id,ordinal,code))""",
        "CREATE INDEX quarantine_records_attempt ON quarantine_records(attempt_id,ordinal)",
    ),
    (
        """CREATE TABLE quick_runs (
            id TEXT PRIMARY KEY, source_attempt_id TEXT NOT NULL REFERENCES attempts(id), source_kind TEXT NOT NULL,
            created_at TEXT NOT NULL, actor TEXT NOT NULL, UNIQUE(source_attempt_id,source_kind))""",
        """CREATE TABLE quick_items (
            id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES quick_runs(id), document_id TEXT NOT NULL REFERENCES documents(id),
            proposal_json TEXT NOT NULL, state TEXT NOT NULL CHECK(state IN ('WAIT','APPROVE','SKIP','EXISTING','EXPORTED')),
            decision_json TEXT, reason TEXT NOT NULL DEFAULT '', decided_at TEXT, actor TEXT,
            UNIQUE(run_id,document_id))""",
        """CREATE TABLE quick_learning (
            id TEXT PRIMARY KEY, document_key TEXT NOT NULL UNIQUE, fields_json TEXT NOT NULL,
            evidence_json TEXT NOT NULL, created_at TEXT NOT NULL, actor TEXT NOT NULL)""",
        "CREATE INDEX quick_items_run_state ON quick_items(run_id,state)",
    ),
    (
        """CREATE TABLE cash_account_mappings (
            bank_account TEXT PRIMARY KEY,
            cash_account TEXT NOT NULL,
            source TEXT NOT NULL CHECK(source IN ('MANUAL','JOURNAL_UNIQUE')),
            evidence_json TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            actor TEXT NOT NULL)""",
        """CREATE TABLE bank_journal_matches (
            bank_document_id TEXT PRIMARY KEY REFERENCES documents(id),
            journal_document_id TEXT NOT NULL REFERENCES documents(id),
            similarity REAL NOT NULL CHECK(similarity>=0 AND similarity<=1),
            state TEXT NOT NULL CHECK(state IN ('UNIQUE','AMBIGUOUS','UNMATCHED')),
            excluded_from_export INTEGER NOT NULL DEFAULT 1 CHECK(excluded_from_export IN (0,1)),
            matched_at TEXT NOT NULL,
            actor TEXT NOT NULL)""",
        "ALTER TABLE quick_items ADD COLUMN excluded_from_export INTEGER NOT NULL DEFAULT 0 CHECK(excluded_from_export IN (0,1))",
        """CREATE TABLE quick_condition_learning (
            id TEXT PRIMARY KEY,
            condition_type TEXT NOT NULL CHECK(condition_type IN ('BANK_ACCOUNT','COUNTERPARTY_NAME','KEYWORD')),
            condition_value TEXT NOT NULL,
            revision INTEGER NOT NULL,
            fields_json TEXT NOT NULL,
            knowledge_id TEXT REFERENCES knowledge_versions(id),
            active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1)),
            valid_from TEXT NOT NULL,
            created_at TEXT NOT NULL,
            actor TEXT NOT NULL,
            evidence_json TEXT NOT NULL,
            UNIQUE(condition_type,condition_value,revision))""",
        "CREATE INDEX quick_condition_lookup ON quick_condition_learning(condition_type,condition_value,active,valid_from)",
        """CREATE TABLE export_counters (
            prefix_month TEXT PRIMARY KEY,
            last_number INTEGER NOT NULL CHECK(last_number>=0),
            updated_at TEXT NOT NULL,
            actor TEXT NOT NULL)""",
    ),
    (
        # TTCP is a dimension of a quick proposal, not a sixth core posting
        # field.  Keeping it separate preserves the V1--V8 field contract
        # while allowing V9b to retain and edit the value in Entry2.CenterID.
        "ALTER TABLE quick_items ADD COLUMN decision_cost_center TEXT",
    ),
    (
        # V10 screen: an operator may edit the complete entry (several lines,
        # each with its own counterparty/project/expense/TTCP).  The header
        # decision_json stays the V9b contract; the lines are an addition.
        "ALTER TABLE quick_items ADD COLUMN decision_lines_json TEXT",
        "ALTER TABLE quick_runs ADD COLUMN source_name TEXT",
        "ALTER TABLE quick_runs ADD COLUMN source_hash TEXT",
        "ALTER TABLE quick_runs ADD COLUMN source_info_json TEXT",
        "CREATE INDEX quick_runs_source_hash ON quick_runs(source_hash)",
        """CREATE TABLE quick_exports (
            id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL REFERENCES quick_runs(id),
            exported_at TEXT NOT NULL,
            actor TEXT NOT NULL,
            item_count INTEGER NOT NULL CHECK(item_count>=0),
            total_minor INTEGER NOT NULL CHECK(total_minor>=0),
            files_json TEXT NOT NULL)""",
    ),
)
