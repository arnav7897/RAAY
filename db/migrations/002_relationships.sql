BEGIN;

INSERT INTO document_aliases (document_id, alias, alias_kind)
SELECT id, rbi_ref, 'rbi_ref' FROM documents WHERE rbi_ref IS NOT NULL
ON CONFLICT DO NOTHING;

INSERT INTO document_aliases (document_id, alias, alias_kind)
SELECT id, dept_ref, 'dept_ref' FROM documents WHERE dept_ref IS NOT NULL
ON CONFLICT DO NOTHING;

INSERT INTO document_aliases (document_id, alias, alias_kind)
SELECT id, title, 'title' FROM documents
ON CONFLICT DO NOTHING;

CREATE TABLE IF NOT EXISTS document_relations (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_document_id BIGINT NOT NULL REFERENCES documents(id) ON DELETE RESTRICT,
    target_document_id BIGINT REFERENCES documents(id) ON DELETE RESTRICT,
    target_ref_raw TEXT NOT NULL CHECK (length(target_ref_raw) > 0),
    target_clause TEXT,
    relation_type TEXT NOT NULL CHECK (
        relation_type IN ('AMENDS', 'REPLACES', 'REPEALS', 'CONSOLIDATED_INTO', 'RELATED_TO')
    ),
    evidence_text TEXT NOT NULL CHECK (length(evidence_text) > 0),
    evidence_page INTEGER CHECK (evidence_page IS NULL OR evidence_page > 0),
    evidence_dom_locator TEXT,
    char_start INTEGER NOT NULL CHECK (char_start >= 0),
    char_end INTEGER NOT NULL CHECK (char_end > char_start),
    source_url TEXT NOT NULL CHECK (length(source_url) > 0),
    evidence_type TEXT NOT NULL CHECK (
        evidence_type IN ('EXPLICIT_REF', 'AMEND_INSTRUCTION', 'REPEAL_LIST', 'SEMANTIC')
    ),
    verification_status TEXT NOT NULL CHECK (
        verification_status IN ('VERIFIED', 'UNRESOLVED', 'CANDIDATE')
    ),
    extractor TEXT NOT NULL,
    extractor_version TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK ((evidence_page IS NULL) <> (evidence_dom_locator IS NULL)),
    CHECK (verification_status != 'VERIFIED' OR target_document_id IS NOT NULL),
    CHECK (
        verification_status != 'VERIFIED'
        OR relation_type = 'RELATED_TO'
        OR evidence_type != 'SEMANTIC'
    ),
    UNIQUE (
        source_document_id, target_ref_raw, relation_type, char_start, char_end,
        extractor, extractor_version
    )
);

CREATE INDEX IF NOT EXISTS document_relations_source_idx
    ON document_relations (source_document_id, verification_status);
CREATE INDEX IF NOT EXISTS document_relations_target_idx
    ON document_relations (target_document_id, verification_status);

CREATE TABLE IF NOT EXISTS clause_versions (
    relation_id BIGINT PRIMARY KEY REFERENCES document_relations(id) ON DELETE CASCADE,
    target_clause_id BIGINT REFERENCES clauses(id) ON DELETE RESTRICT,
    source_clause_id BIGINT REFERENCES clauses(id) ON DELETE RESTRICT,
    old_text TEXT,
    new_text TEXT,
    diff_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    CHECK (old_text IS NOT NULL OR new_text IS NOT NULL)
);

COMMIT;
