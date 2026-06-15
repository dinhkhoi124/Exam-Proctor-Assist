BEGIN;

CREATE TABLE IF NOT EXISTS public.rag_documents (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    file_name character varying(255) NOT NULL,
    storage_path text NOT NULL,
    file_size bigint DEFAULT 0 NOT NULL,
    checksum_sha256 character varying(64),
    status character varying(20) DEFAULT 'indexing'::character varying NOT NULL,
    chunk_count integer DEFAULT 0 NOT NULL,
    uploaded_by uuid,
    error_message text,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    indexed_at timestamp with time zone,
    deleted_at timestamp with time zone,
    CONSTRAINT rag_documents_pkey PRIMARY KEY (id),
    CONSTRAINT rag_documents_file_name_key UNIQUE (file_name),
    CONSTRAINT rag_documents_uploaded_by_fkey
        FOREIGN KEY (uploaded_by) REFERENCES public.users(id) ON DELETE SET NULL,
    CONSTRAINT rag_documents_status_check
        CHECK (status IN ('indexing', 'ready', 'failed', 'deleted'))
);

CREATE INDEX IF NOT EXISTS idx_rag_documents_status
    ON public.rag_documents USING btree (status);

CREATE INDEX IF NOT EXISTS idx_rag_documents_uploaded_by
    ON public.rag_documents USING btree (uploaded_by);

DROP TRIGGER IF EXISTS update_rag_document_modtime ON public.rag_documents;
CREATE TRIGGER update_rag_document_modtime
    BEFORE UPDATE ON public.rag_documents
    FOR EACH ROW EXECUTE FUNCTION public.update_modified_column();

COMMIT;
