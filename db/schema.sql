CREATE EXTENSION IF NOT EXISTS vector;

DO $$ BEGIN
    CREATE TYPE lifecycle_state AS ENUM ('DRAFT', 'IN_FORCE', 'REPEALED', 'SUPERSEDED');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

CREATE TABLE IF NOT EXISTS documents (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_key TEXT NOT NULL UNIQUE,
    rbi_ref TEXT,
    dept_ref TEXT,
    title TEXT NOT NULL,
    doc_type TEXT,
    published_at DATE,
    effective_at DATE,
    lifecycle_state lifecycle_state,
    valid_from DATE,
    valid_to DATE,
    source_url TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS document_versions (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    document_id BIGINT NOT NULL REFERENCES documents(id) ON DELETE RESTRICT,
    version_no INTEGER NOT NULL CHECK (version_no > 0),
    retrieved_at TIMESTAMPTZ NOT NULL,
    content_hash TEXT NOT NULL CHECK (content_hash ~ '^[0-9a-f]{64}$'),
    raw_cache_path TEXT,
    source_format TEXT NOT NULL CHECK (source_format IN ('html', 'pdf')),
    normalized_text TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (document_id, version_no),
    UNIQUE (document_id, content_hash)
);

CREATE TABLE IF NOT EXISTS document_aliases (
    document_id BIGINT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    alias TEXT NOT NULL,
    alias_kind TEXT NOT NULL,
    PRIMARY KEY (document_id, alias)
);

CREATE TABLE IF NOT EXISTS clauses (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    document_version_id BIGINT NOT NULL REFERENCES document_versions(id) ON DELETE RESTRICT,
    ordinal INTEGER NOT NULL CHECK (ordinal > 0),
    parent_id BIGINT REFERENCES clauses(id) ON DELETE RESTRICT,
    path TEXT NOT NULL,
    clause_no TEXT NOT NULL,
    page INTEGER CHECK (page IS NULL OR page > 0),
    dom_locator TEXT,
    char_start INTEGER NOT NULL CHECK (char_start >= 0),
    char_end INTEGER NOT NULL CHECK (char_end > char_start),
    text TEXT NOT NULL CHECK (length(text) > 0),
    tsv TSVECTOR GENERATED ALWAYS AS (to_tsvector('english', text)) STORED,
    CHECK ((page IS NULL) <> (dom_locator IS NULL)),
    UNIQUE (document_version_id, ordinal)
);

ALTER TABLE clauses ADD COLUMN IF NOT EXISTS ordinal INTEGER;
WITH ranked AS (
    SELECT id, row_number() OVER (PARTITION BY document_version_id ORDER BY char_start, id) AS value
    FROM clauses
    WHERE ordinal IS NULL
)
UPDATE clauses SET ordinal = ranked.value
FROM ranked WHERE clauses.id = ranked.id;
ALTER TABLE clauses ALTER COLUMN ordinal SET NOT NULL;
ALTER TABLE clauses DROP CONSTRAINT IF EXISTS clauses_document_version_id_path_key;
CREATE UNIQUE INDEX IF NOT EXISTS clauses_document_version_ordinal_idx
    ON clauses (document_version_id, ordinal);

CREATE INDEX IF NOT EXISTS clauses_tsv_idx ON clauses USING GIN (tsv);
CREATE INDEX IF NOT EXISTS clauses_document_version_idx ON clauses (document_version_id);

CREATE TABLE IF NOT EXISTS ingest_runs (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source TEXT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ,
    status TEXT NOT NULL CHECK (status IN ('RUNNING', 'SUCCEEDED', 'FAILED')),
    details JSONB NOT NULL DEFAULT '{}'::jsonb
);
