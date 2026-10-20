export function validateAccountConfig(url, key) {
  if (!url && !key) return;
  if (!url || !key) throw new Error('Set both VITE_SUPABASE_URL and VITE_SUPABASE_PUBLISHABLE_KEY, or leave both empty for guest mode.');
  const parsed = new URL(url);
  const local = ['localhost', '127.0.0.1', '[::1]'].includes(parsed.hostname);
  if ((parsed.protocol !== 'https:' && !(local && parsed.protocol === 'http:')) || parsed.username || parsed.password || !['', '/'].includes(parsed.pathname) || parsed.search || parsed.hash) {
    throw new Error('VITE_SUPABASE_URL must be an HTTPS origin, or a local HTTP development origin.');
  }
  if (/^sb_publishable_[A-Za-z0-9_-]+$/.test(key)) return;
  try {
    const payload = JSON.parse(Buffer.from(key.split('.')[1], 'base64url').toString());
    if (key.split('.').length === 3 && payload.role === 'anon') return;
  } catch { /* Reject anything other than a public publishable/legacy anon key. */ }
  throw new Error('Use only a public Supabase publishable key or legacy anon key. Secret and service-role keys must never enter a browser build.');
}
