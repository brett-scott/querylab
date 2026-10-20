-- Disposable PostgreSQL test only. The bootstrap roles/auth.uid match the
-- Supabase authorization boundary; this does not test hosted OAuth or PostgREST.
begin;
insert into auth.users(id) values ('11111111-1111-4111-8111-111111111111'), ('22222222-2222-4222-8222-222222222222');
set local role authenticated;
select set_config('request.jwt.claim.sub', '11111111-1111-4111-8111-111111111111', true);

insert into public.challenge_attempts(id,user_id,challenge_id,challenge_version,challenge_title,challenge_type,dataset,passed,hints_used,solution_viewed,completed_at)
values ('aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',auth.uid(),'OS-Q01','1.0.0','Customer analysis','query','online-store',false,0,false,now());
insert into public.challenge_attempts(id,user_id,challenge_id,challenge_version,challenge_title,challenge_type,dataset,passed,hints_used,solution_viewed,completed_at)
values ('aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',auth.uid(),'OS-Q01','1.0.0','Customer analysis','query','online-store',false,0,false,now()) on conflict(id) do nothing;

do $$ begin
  if (select count(*) from public.challenge_attempts) <> 1 then raise exception 'Retry counted twice'; end if;
  begin
    insert into public.challenge_attempts(id,user_id,challenge_id,challenge_version,challenge_title,challenge_type,dataset,passed,hints_used,solution_viewed,completed_at)
    values ('bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb','22222222-2222-4222-8222-222222222222','OS-Q01','1.0.0','Forged owner','query','online-store',true,0,false,now());
    raise exception 'Cross-user insert was accepted';
  exception when insufficient_privilege then null; end;
  begin
    update public.challenge_attempts set passed=true;
    raise exception 'Attempt rewrite was accepted';
  exception when insufficient_privilege then null; end;
  begin
    delete from public.challenge_attempts;
    raise exception 'Attempt deletion was accepted';
  exception when insufficient_privilege then null; end;
  begin
    insert into public.challenge_attempts(id,user_id,challenge_id,challenge_version,challenge_title,challenge_type,dataset,passed,hints_used,solution_viewed,completed_at)
    values ('cccccccc-cccc-4ccc-8ccc-cccccccccccc',auth.uid(),'OS-Q01','1.0.0','Bad assistance','query','online-store',true,4,false,now());
    raise exception 'Invalid assistance was accepted';
  exception when check_violation then null; end;
end $$;

select set_config('request.jwt.claim.sub', '22222222-2222-4222-8222-222222222222', true);
do $$ begin
  if (select count(*) from public.challenge_attempts) <> 0 then raise exception 'Another user can read attempts'; end if;
  if (select count(*) from public.challenge_progress) <> 0 then raise exception 'View bypassed row security'; end if;
end $$;
insert into public.challenge_attempts(id,user_id,challenge_id,challenge_version,challenge_title,challenge_type,dataset,passed,hints_used,solution_viewed,completed_at)
values
  ('dddddddd-dddd-4ddd-8ddd-dddddddddddd',auth.uid(),'OS-Q01','1.0.0','Customer analysis','query','online-store',true,1,false,now()),
  ('eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee',auth.uid(),'OS-Q01','1.0.0','Customer analysis','query','online-store',true,0,true,now()),
  ('ffffffff-ffff-4fff-8fff-ffffffffffff',auth.uid(),'OS-Q01','1.0.0','Customer analysis','query','online-store',true,0,false,now());
do $$ begin
  if (select attempt_count from public.challenge_progress) <> 3 then raise exception 'Incorrect attempt aggregation'; end if;
  if (select passed_count from public.challenge_progress) <> 3 then raise exception 'Incorrect pass aggregation'; end if;
  if (select unassisted_pass_count from public.challenge_progress) <> 1 then raise exception 'Hints or solution counted as unassisted'; end if;
end $$;

select set_config('request.jwt.claim.sub', '11111111-1111-4111-8111-111111111111', true);
do $$ begin
  if (select attempt_count from public.challenge_progress) <> 1 then raise exception 'Another user affected aggregate'; end if;
  if (select passed_count from public.challenge_progress) <> 0 then raise exception 'Another user pass was exposed'; end if;
end $$;

set local role anon;
do $$ begin
  begin
    perform * from public.challenge_attempts;
    raise exception 'Anonymous read accepted';
  exception when insufficient_privilege then null; end;
  begin
    perform * from public.challenge_progress;
    raise exception 'Anonymous aggregate read accepted';
  exception when insufficient_privilege then null; end;
end $$;
rollback;
select 'PASS: own-account RLS, anonymous denial, append-only history, idempotency, aggregate isolation and assistance rules.' as result;
