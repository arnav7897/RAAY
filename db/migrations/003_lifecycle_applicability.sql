BEGIN;

CREATE TABLE IF NOT EXISTS entity_ontology (
    code TEXT PRIMARY KEY,
    parent_code TEXT REFERENCES entity_ontology(code) ON DELETE RESTRICT,
    label TEXT NOT NULL
);

INSERT INTO entity_ontology (code, parent_code, label) VALUES
    ('REGULATED_ENTITY', NULL, 'Regulated entity'),
    ('BANK', 'REGULATED_ENTITY', 'Bank'),
    ('COMMERCIAL_BANK', 'BANK', 'Commercial bank'),
    ('SMALL_FINANCE_BANK', 'COMMERCIAL_BANK', 'Small finance bank'),
    ('LOCAL_AREA_BANK', 'COMMERCIAL_BANK', 'Local area bank'),
    ('REGIONAL_RURAL_BANK', 'COMMERCIAL_BANK', 'Regional rural bank'),
    ('PAYMENTS_BANK', 'COMMERCIAL_BANK', 'Payments bank'),
    ('COOPERATIVE_BANK', 'BANK', 'Co-operative bank'),
    ('PRIMARY_URBAN_COOPERATIVE_BANK', 'COOPERATIVE_BANK', 'Primary urban co-operative bank'),
    ('STATE_COOPERATIVE_BANK', 'COOPERATIVE_BANK', 'State co-operative bank'),
    ('DISTRICT_CENTRAL_COOPERATIVE_BANK', 'COOPERATIVE_BANK', 'District central co-operative bank'),
    ('NBFC', 'REGULATED_ENTITY', 'Non-banking financial company'),
    ('NBFC_ICC', 'NBFC', 'NBFC investment and credit company'),
    ('NBFC_MFI', 'NBFC', 'NBFC microfinance institution'),
    ('HFC', 'NBFC', 'Housing finance company')
ON CONFLICT (code) DO UPDATE SET
    parent_code = EXCLUDED.parent_code,
    label = EXCLUDED.label;

CREATE TABLE IF NOT EXISTS applicability_facts (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    document_id BIGINT NOT NULL REFERENCES documents(id) ON DELETE RESTRICT,
    clause_id BIGINT REFERENCES clauses(id) ON DELETE RESTRICT,
    entity_code TEXT NOT NULL REFERENCES entity_ontology(code) ON DELETE RESTRICT,
    polarity TEXT NOT NULL CHECK (polarity IN ('INCLUDES', 'EXCLUDES')),
    condition_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    evidence_text TEXT NOT NULL CHECK (length(evidence_text) > 0),
    evidence_page INTEGER CHECK (evidence_page IS NULL OR evidence_page > 0),
    evidence_dom_locator TEXT,
    char_start INTEGER NOT NULL CHECK (char_start >= 0),
    char_end INTEGER NOT NULL CHECK (char_end > char_start),
    source_url TEXT NOT NULL CHECK (length(source_url) > 0),
    extractor TEXT NOT NULL,
    extractor_version TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK ((evidence_page IS NULL) <> (evidence_dom_locator IS NULL)),
    UNIQUE (
        document_id, entity_code, polarity, char_start, char_end,
        extractor, extractor_version
    )
);

CREATE INDEX IF NOT EXISTS applicability_facts_document_idx
    ON applicability_facts (document_id, entity_code, polarity);

COMMIT;
