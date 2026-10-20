-- Run in the QueryLab Supabase project's SQL editor before enabling accounts.
-- Local helper results are a personal practice record, not certified grading.
begin;

create table public.challenge_attempts (
  id uuid primary key,
  user_id uuid not null references auth.users(id) on delete cascade,
  challenge_id text not null check (challenge_id in ('OS-Q01','OS-Q02','OS-Q03','OS-F01','OS-F02','OS-P01','BI-Q01','BI-Q02','BI-Q03','BI-F01','BI-P01','BI-P02')),
  challenge_version text not null check (challenge_version ~ '^[0-9]+\.[0-9]+\.[0-9]+$' and length(challenge_version) <= 40),
  challenge_title text not null check (length(challenge_title) between 1 and 160),
  challenge_type text not null check (challenge_type in ('query','function','procedure')),
  dataset text not null check (dataset in ('online-store','inventory')),
  passed boolean not null,
  hints_used smallint not null check (hints_used between 0 and 3),
  solution_viewed boolean not null,
  completed_at timestamptz not null,
  saved_at timestamptz not null default now(),
  constraint challenge_metadata_matches check (
    (left(challenge_id, 2) = 'OS' and dataset = 'online-store' or left(challenge_id, 2) = 'BI' and dataset = 'inventory')
    and substring(challenge_id, 4, 1) = case challenge_type when 'query' then 'Q' when 'function' then 'F' else 'P' end
  )
);

create index challenge_attempts_user_completed on public.challenge_attempts(user_id, completed_at desc);
alter table public.challenge_attempts enable row level security;
revoke all on public.challenge_attempts from public, anon, authenticated;
grant select, insert on public.challenge_attempts to authenticated;
create policy read_own_attempts on public.challenge_attempts for select to authenticated using ((select auth.uid()) = user_id);
create policy insert_own_attempts on public.challenge_attempts for insert to authenticated with check ((select auth.uid()) = user_id);
-- Append-only history: clients cannot rewrite a failed result or erase it.
-- A retry uses the same UUID and ON CONFLICT DO NOTHING, so it counts once.

create view public.challenge_progress with (security_invoker = true) as
select user_id, challenge_id, challenge_version,
  max(challenge_title) as challenge_title, max(challenge_type) as challenge_type,
  count(*) as attempt_count,
  count(*) filter (where passed) as passed_count,
  count(*) filter (where passed and hints_used = 0 and not solution_viewed) as unassisted_pass_count,
  max(completed_at) as last_attempt_at
from public.challenge_attempts
group by user_id, challenge_id, challenge_version;

revoke all on public.challenge_progress from public, anon, authenticated;
grant select on public.challenge_progress to authenticated;

commit;
