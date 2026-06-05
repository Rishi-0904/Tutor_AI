-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Table for tracking topic mastery scores (0-100)
CREATE TABLE IF NOT EXISTS public.topic_mastery (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    topic       TEXT NOT NULL,
    score       INT NOT NULL DEFAULT 50 CHECK (score >= 0 AND score <= 100),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, topic)
);

CREATE INDEX IF NOT EXISTS idx_topic_mastery_user_id ON public.topic_mastery(user_id);

-- Alter profiles table to support current goal
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS current_goal TEXT DEFAULT 'JEE Advanced 2027';

-- PDF Documents Metadata Table
CREATE TABLE IF NOT EXISTS public.pdf_documents (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    filename    TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'processing' CHECK (status IN ('processing', 'completed', 'failed')),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- PDF Text Chunks Table with Vector Embedding Column (768 dimensions for text-embedding-004)
CREATE TABLE IF NOT EXISTS public.pdf_chunks (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pdf_id       UUID NOT NULL REFERENCES public.pdf_documents(id) ON DELETE CASCADE,
    chunk_index  INT NOT NULL,
    content      TEXT NOT NULL,
    embedding    vector(768) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_pdf_chunks_pdf_id ON public.pdf_chunks(pdf_id);

-- Learning Sessions Table for analytics tracking
CREATE TABLE IF NOT EXISTS public.learning_sessions (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    topic         TEXT NOT NULL,
    started_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at      TIMESTAMPTZ,
    score_before  INT,
    score_after   INT
);

CREATE INDEX IF NOT EXISTS idx_learning_sessions_user_id ON public.learning_sessions(user_id);

-- Whiteboard sketches SVG vector path table
CREATE TABLE IF NOT EXISTS public.whiteboard_sketches (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id          UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    conversation_id  UUID NOT NULL REFERENCES public.conversations(id) ON DELETE CASCADE,
    title            TEXT NOT NULL,
    svg_data         TEXT NOT NULL, -- JSON string representing canvas coordinates/lines
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Cosine Distance similarity match function for user-isolated vector retrieval
CREATE OR REPLACE FUNCTION match_pdf_chunks (
  query_embedding vector(768),
  match_threshold float,
  match_count int,
  p_user_id uuid
)
RETURNS TABLE (
  id uuid,
  pdf_id uuid,
  content text,
  similarity float
)
LANGUAGE plpgsql AS $$
BEGIN
  RETURN QUERY
  SELECT
    pdf_chunks.id,
    pdf_chunks.pdf_id,
    pdf_chunks.content,
    1 - (pdf_chunks.embedding <=> query_embedding) AS similarity
  FROM pdf_chunks
  JOIN pdf_documents ON pdf_chunks.pdf_id = pdf_documents.id
  WHERE pdf_documents.user_id = p_user_id
    AND pdf_documents.status = 'completed'
    AND 1 - (pdf_chunks.embedding <=> query_embedding) > match_threshold
  ORDER BY pdf_chunks.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;
