import { createClient } from '@supabase/supabase-js';

const url = import.meta.env.VITE_SUPABASE_URL?.trim();
const key = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY?.trim();
export const accountsConfigured = Boolean(url && key);
export const accountClient = accountsConfigured ? createClient(url!, key!, {
  auth: {
    flowType: 'pkce', detectSessionInUrl: true, persistSession: true, autoRefreshToken: true,
    storageKey: `querylab:account:${import.meta.env.BASE_URL}`,
  },
}) : null;

const returnKey = 'querylab:account:return-challenge';
export function rememberChallenge() {
  try { sessionStorage.setItem(returnKey, new URLSearchParams(location.search).get('challenge') ?? 'OS-Q01'); } catch { /* The SQL draft is saved separately. */ }
}
export function initialChallenge() {
  const url = new URL(location.href);
  if (url.searchParams.has('code') || url.searchParams.has('error')) {
    try {
      const previous = sessionStorage.getItem(returnKey);
      sessionStorage.removeItem(returnKey);
      if (previous && /^(OS|BI)-[QFP]\d{2}$/.test(previous)) {
        url.searchParams.set('challenge', previous);
        history.replaceState(null, '', url);
      }
    } catch { /* Continue with the normal challenge selection. */ }
  }
  return url.searchParams.get('challenge') ?? 'OS-Q01';
}

export function cleanAuthCallback() {
  const url = new URL(location.href);
  if (!url.searchParams.has('code') && !url.searchParams.has('error')) return;
  for (const name of ['code', 'error', 'error_code', 'error_description']) url.searchParams.delete(name);
  history.replaceState(null, '', url);
}
