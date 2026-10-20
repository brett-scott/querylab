import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import type { User } from '@supabase/supabase-js';
import { accountClient, accountsConfigured, cleanAuthCallback, rememberChallenge } from './client';
import { pendingKey, readPending } from './progress';
import type { Attempt, ChallengeProgress } from './progress';

interface AccountContextValue {
  configured: boolean; user: User | null; initializing: boolean; loading: boolean;
  progress: ChallengeProgress[]; recent: Attempt[]; pending: number; error: string | null;
  signIn: () => Promise<void>; signOut: () => Promise<void>; retry: () => Promise<void>;
  record: (attempt: Attempt) => void;
}
const AccountContext = createContext<AccountContextValue | null>(null);
export function useAccount() {
  const value = useContext(AccountContext);
  if (!value) throw new Error('AccountProvider is required.');
  return value;
}

export default function AccountProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [initializing, setInitializing] = useState(accountsConfigured);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState<ChallengeProgress[]>([]);
  const [recent, setRecent] = useState<Attempt[]>([]);
  const [pending, setPending] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const owner = useRef<string | null>(null);
  const queues = useRef(new Map<string, Attempt[]>());
  const unpersisted = useRef(new Set<string>());
  const syncing = useRef(new Map<string, Promise<void>>());
  const loadSequence = useRef(0);
  const alive = useRef(true);

  const queueFor = useCallback((id: string) => {
    let queue = queues.current.get(id);
    if (!queue) {
      try { queue = readPending(localStorage.getItem(pendingKey(id)), id); } catch { queue = []; }
      queues.current.set(id, queue);
    }
    return queue;
  }, []);

  const persist = useCallback((id: string, queue: Attempt[]) => {
    queues.current.set(id, queue);
    try { if (queue.length) localStorage.setItem(pendingKey(id), JSON.stringify(queue)); else localStorage.removeItem(pendingKey(id)); unpersisted.current.delete(id); }
    catch { unpersisted.current.add(id); if (owner.current === id) setError('Progress cannot be kept for retry after closing this tab. Keep it open and choose Retry sync.'); }
    if (alive.current && owner.current === id) setPending(queue.length);
  }, []);

  const load = useCallback(async (id: string) => {
    if (!accountClient || owner.current !== id) return;
    const sequence = ++loadSequence.current;
    setLoading(true);
    try {
      const [summary, history] = await Promise.all([
        accountClient.from('challenge_progress').select('*').eq('user_id', id).order('last_attempt_at', { ascending: false }),
        accountClient.from('challenge_attempts').select('*').eq('user_id', id).order('completed_at', { ascending: false }).limit(20),
      ]);
      if (summary.error || history.error) throw new Error('load');
      if (alive.current && owner.current === id && sequence === loadSequence.current) {
        setProgress(summary.data as ChallengeProgress[]); setRecent(history.data as Attempt[]);
      }
    } catch {
      if (alive.current && owner.current === id && sequence === loadSequence.current) setError('Your saved progress could not be loaded. You can keep practising and retry here.');
    } finally { if (alive.current && owner.current === id && sequence === loadSequence.current) setLoading(false); }
  }, []);

  const sync = useCallback(async (id: string): Promise<void> => {
    if (!accountClient || owner.current !== id) return;
    if (syncing.current.has(id)) return syncing.current.get(id);
    let failed = false;
    const work = (async () => {
      try {
        while (owner.current === id && queueFor(id).length) {
          const attempt = queueFor(id)[0];
          const { error } = await accountClient.from('challenge_attempts').upsert(attempt, { onConflict: 'id', ignoreDuplicates: true });
          if (error) throw error;
          // A logout or another account login must not update the new account's UI.
          persist(id, queueFor(id).filter(item => item.id !== attempt.id));
        }
        if (alive.current && owner.current === id) { setError(null); await load(id); }
      } catch {
        failed = true;
        if (alive.current && owner.current === id) setError(unpersisted.current.has(id) ? 'Your result is not saved yet. Keep this tab open and choose Retry sync when the connection returns.' : 'Your result is waiting to sync. Keep practising; retry here when the connection returns.');
      }
    })();
    syncing.current.set(id, work);
    try { await work; } finally {
      syncing.current.delete(id);
      // A submission can finish while the previous sync is loading its summary.
      if (!failed && alive.current && owner.current === id && queueFor(id).length) void sync(id);
    }
  }, [load, persist, queueFor]);

  useEffect(() => {
    alive.current = true;
    if (!accountClient) return () => { alive.current = false; };
    let disposed = false;
    const applyUser = (next: User | null) => {
      if (disposed || !alive.current) return;
      if (owner.current !== (next?.id ?? null)) {
        owner.current = next?.id ?? null; loadSequence.current++;
        setProgress([]); setRecent([]); setPending(0); setLoading(false); setError(null);
      }
      setUser(next); setInitializing(false);
    };
    const { data: { subscription } } = accountClient.auth.onAuthStateChange((_event, session) => applyUser(session?.user ?? null));
    // No Supabase calls are awaited inside onAuthStateChange: the SDK holds its
    // auth lock while delivering the callback.
    void accountClient.auth.getSession().then(({ data, error }) => {
      if (disposed || !alive.current) return;
      applyUser(data.session?.user ?? null);
      if (error || new URLSearchParams(location.search).has('error')) setError('Google sign-in could not be completed. Please try again.');
      cleanAuthCallback();
    }).catch(() => {
      if (!disposed && alive.current) { setInitializing(false); setError('Sign-in is unavailable. You can continue as a guest.'); cleanAuthCallback(); }
    });
    return () => { disposed = true; alive.current = false; subscription.unsubscribe(); };
  }, []);

  useEffect(() => {
    if (!user) return;
    setPending(queueFor(user.id).length);
    void sync(user.id);
    const retry = () => { void sync(user.id); };
    window.addEventListener('online', retry);
    return () => window.removeEventListener('online', retry);
  }, [user?.id, queueFor, sync]);

  const signIn = async () => {
    if (!accountClient) return;
    setError(null); rememberChallenge();
    try {
      const { error } = await accountClient.auth.signInWithOAuth({ provider: 'google', options: { redirectTo: new URL(import.meta.env.BASE_URL, location.origin).href } });
      if (error) throw error;
    } catch { setError('Google sign-in could not be started. Please try again.'); }
  };
  const signOut = async () => {
    if (!accountClient) return;
    setError(null);
    try {
      const { error } = await accountClient.auth.signOut({ scope: 'local' });
      if (error) throw error;
    } catch { setError('Sign-out could not be completed. Please try again.'); }
  };
  const record = useCallback((attempt: Attempt) => {
    if (!owner.current || owner.current !== attempt.user_id) return;
    const queue = queueFor(attempt.user_id);
    if (!queue.some(item => item.id === attempt.id)) persist(attempt.user_id, [...queue, attempt]);
    void sync(attempt.user_id);
  }, [persist, queueFor, sync]);

  return <AccountContext.Provider value={{ configured: accountsConfigured, user, initializing, loading, progress, recent, pending, error, signIn, signOut, record, retry: async () => { if (owner.current) await sync(owner.current); } }}>{children}</AccountContext.Provider>;
}
