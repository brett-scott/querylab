import { spawnSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { randomBytes } from 'node:crypto';

const name = `querylab-progress-test-${randomBytes(6).toString('hex')}`;
function docker(args, input, allowFailure = false) {
  const result = spawnSync('docker', args, { input, encoding: 'utf8', timeout: 180000 });
  if (!allowFailure && (result.error || result.status !== 0)) throw new Error(result.stderr || result.error?.message || 'Docker command failed.');
  return result;
}
let started = false;
try {
  docker(['run', '--detach', '--rm', '--network', 'none', '--label', 'querylab.qa=progress', '--name', name, '-e', 'POSTGRES_HOST_AUTH_METHOD=trust', 'postgres:17-alpine']);
  started = true;
  let ready = false;
  for (let attempt = 0; attempt < 60; attempt++) {
    const result = docker(['exec', name, 'pg_isready', '-U', 'postgres'], undefined, true);
    if (result.status === 0) { ready = true; break; }
    await new Promise(resolve => setTimeout(resolve, 500));
  }
  if (!ready) throw new Error('Disposable PostgreSQL was not ready.');
  const sql = ['exec', '-i', name, 'psql', '-U', 'postgres', '-v', 'ON_ERROR_STOP=1'];
  docker(sql, `create role anon nologin; create role authenticated nologin;
create schema auth;
create table auth.users(id uuid primary key);
create function auth.uid() returns uuid language sql stable as $$ select nullif(current_setting('request.jwt.claim.sub', true), '')::uuid $$;
grant usage on schema auth, public to anon, authenticated;
grant execute on function auth.uid() to anon, authenticated;
`);
  docker(sql, readFileSync(new URL('../supabase/migrations/202610180001_progress.sql', import.meta.url), 'utf8'));
  const result = docker(sql, readFileSync(new URL('../supabase/tests/progress.sql', import.meta.url), 'utf8'));
  console.log(result.stdout.split('\n').find(line => line.includes('PASS:'))?.trim() ?? result.stdout);
} finally {
  if (started) {
    const label = docker(['inspect', '--format', '{{index .Config.Labels "querylab.qa"}}', name], undefined, true);
    if (label.stdout.trim() === 'progress') docker(['rm', '--force', name]);
    else throw new Error(`Did not remove ${name}: ownership label could not be verified.`);
  }
}
