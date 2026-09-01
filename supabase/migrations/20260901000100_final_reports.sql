create table if not exists public.final_reports (
    id uuid primary key default gen_random_uuid(),
    workflow_run_id uuid not null unique,
    session_id text not null,
    title text not null,
    recommendation text not null,
    request_payload jsonb not null,
    investment_memo jsonb not null,
    report_payload jsonb not null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists final_reports_session_created_idx
    on public.final_reports (session_id, created_at desc);

alter table public.final_reports enable row level security;
revoke all on public.final_reports from anon, authenticated;
grant all on public.final_reports to service_role;
