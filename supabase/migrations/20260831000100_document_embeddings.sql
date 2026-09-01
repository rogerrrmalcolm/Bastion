create extension if not exists vector with schema extensions;

create table if not exists public.documents (
    id uuid primary key default gen_random_uuid(),
    source_uri text not null unique,
    filename text not null,
    page_count integer not null default 0 check (page_count >= 0),
    chunk_count integer not null default 0 check (chunk_count >= 0),
    embedding_model text not null,
    embedding_dimensions integer not null check (embedding_dimensions > 0),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists public.document_chunks (
    id bigint generated always as identity primary key,
    document_id uuid not null references public.documents(id) on delete cascade,
    page integer not null check (page > 0),
    chunk_index integer not null check (chunk_index >= 0),
    content text not null,
    embedding extensions.vector(768) not null,
    created_at timestamptz not null default now(),
    unique (document_id, page, chunk_index)
);

create index if not exists document_chunks_document_id_idx
    on public.document_chunks (document_id);

create index if not exists document_chunks_embedding_hnsw_idx
    on public.document_chunks
    using hnsw (embedding extensions.vector_cosine_ops);

alter table public.documents enable row level security;
alter table public.document_chunks enable row level security;

revoke all on public.documents from anon, authenticated;
revoke all on public.document_chunks from anon, authenticated;
grant all on public.documents to service_role;
grant all on public.document_chunks to service_role;
grant usage, select on sequence public.document_chunks_id_seq to service_role;

create or replace function public.match_document_chunks(
    query_embedding extensions.vector(768),
    source_uris text[],
    match_count integer default 6
)
returns table (
    source_uri text,
    filename text,
    page integer,
    chunk_index integer,
    content text,
    similarity double precision
)
language sql
stable
security invoker
set search_path = ''
as $$
    select
        d.source_uri,
        d.filename,
        c.page,
        c.chunk_index,
        c.content,
        1 - (
            c.embedding OPERATOR(extensions.<=>) query_embedding
        ) as similarity
    from public.document_chunks c
    join public.documents d on d.id = c.document_id
    where d.source_uri = any(source_uris)
    order by c.embedding OPERATOR(extensions.<=>) query_embedding
    limit least(greatest(match_count, 1), 50);
$$;

revoke all on function public.match_document_chunks(
    extensions.vector(768), text[], integer
) from public, anon, authenticated;
grant execute on function public.match_document_chunks(
    extensions.vector(768), text[], integer
) to service_role;
