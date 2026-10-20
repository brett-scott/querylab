import { lazy, Suspense, useCallback, useEffect, useRef, useState } from 'react';
import { ArrowDown, ArrowRight, BookOpen, Check, CheckCircle2, ChevronDown, ChevronRight, CircleHelp, Clock3, Code2, Database, FileCode2, Info, KeyRound, Lightbulb, LoaderCircle, Maximize2, MoreHorizontal, Play, RotateCcw, Search, Send, ShieldCheck, Square, Table2, X, XCircle } from 'lucide-react';
import { ApiError, disconnectHelper, downloadDataset, getHelperStatus, getHelperToken, getHelperUrl, helperMode, request } from './api';
import type { Challenge, ExecutionResult, HelperStatus, Job, ResultSet, Schema, Session } from './api';
import Dialog from './Dialog';
import HelperConnection from './HelperConnection';
import ResultsTable from './ResultsTable';
import ResultsDivider, { RESULTS_DIVIDER_HEIGHT } from './ResultsDivider';
import type { SqlEditorHandle } from './SqlEditor';
import AccountPanel from './accounts/AccountPanel';
import { useAccount } from './accounts/AccountProvider';
import { initialChallenge } from './accounts/client';
import { clearActiveSubmission, completedAttempt, readActiveSubmission, readAssistance, rememberAssistance, saveActiveSubmission } from './accounts/progress';
import type { SubmissionSnapshot } from './accounts/progress';
const SqlEditor = lazy(() => import('./SqlEditor'));

const titleCase = (value: string) => value.charAt(0).toUpperCase() + value.slice(1);
const errorMessage = (error: unknown) => error instanceof Error ? error.message : 'Something went wrong. Please try again.';
const isExpired = (error: unknown) => error instanceof ApiError && (error.status === 401 || error.code.toUpperCase().includes('EXPIRED') || error.code.toUpperCase() === 'SESSION_REQUIRED');

function Logo() { return <span className="brand"><svg viewBox="0 0 36 40" aria-hidden="true"><path fill="currentColor" fillRule="evenodd" d="M18 1 34 10v19L18 38 2 29V10L18 1Zm0 9L10 15v10l8 5 8-5V15l-8-5Z"/><path d="m23 27 9 9" stroke="currentColor" strokeWidth="7" strokeLinecap="round"/></svg><span>QueryLab<span className="brand-period">.</span></span></span>; }

export default function App() {
  const [challenges, setChallenges] = useState<Challenge[]>([]);
  const [selected, setSelected] = useState<string>(initialChallenge);
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [library, setLibrary] = useState(false);
  const [help, setHelp] = useState(false);
  const [busy, setBusy] = useState(false);
  const [renewing, setRenewing] = useState(false);
  const [expired, setExpired] = useState(false);
  const [connection, setConnection] = useState(false);
  const [helperStatus, setHelperStatus] = useState<HelperStatus | null>(null);
  const initialLoadStarted = useRef(false);
  const markExpired = useCallback(() => { setExpired(true); if (helperMode) { disconnectHelper(); setSession(null); setConnection(true); } }, []);
  const initialize = useCallback(async () => {
    if (helperMode && !getHelperToken()) { setLoading(false); setConnection(true); return false; }
    setLoading(previous => challenges.length ? previous : true); setError(null);
    try {
      if (helperMode) setHelperStatus(await getHelperStatus());
      const [catalog, currentSession] = await Promise.all([request<{ challenges: Challenge[] }>('/challenges'), request<Session>('/session', {})]);
      setChallenges(catalog.challenges); setSession(currentSession); setExpired(false);
      return true;
    } catch (failure) { setError(errorMessage(failure)); if (helperMode) { setSession(null); setConnection(true); if (isExpired(failure)) disconnectHelper(); } return false; } finally { setLoading(false); }
  }, [challenges.length]);
  useEffect(() => { if (!initialLoadStarted.current) { initialLoadStarted.current = true; void initialize(); } }, [initialize]);
  // The API renews an idle TTL on activity. Its initial expires_at is a
  // snapshot, so a client timer would incorrectly expire an active workspace.
  // Use the server's session_expired response as the authority instead.
  const renew = async () => {
    if (helperMode) { setConnection(true); return; }
    setRenewing(true);
    try { const next = await request<Session>('/session', {}); setSession(next); setExpired(false); setError(null); }
    catch (failure) { setError(errorMessage(failure)); } finally { setRenewing(false); }
  };
  const choose = (id: string) => {
    setSelected(id); setLibrary(false);
    const url = new URL(window.location.href); url.searchParams.set('challenge', id); window.history.replaceState(null, '', url);
  };
  const challenge = challenges.find(item => item.id === selected) ?? challenges[0];
  return <div className="app-shell">
    <header className="topbar">
      <a className="brand-link" href={`${import.meta.env.BASE_URL}${helperMode ? '?helper=1' : ''}`} aria-label="QueryLab home"><Logo /></a>
      <nav className="primary-nav" aria-label="Main navigation">
        <button className={library ? 'nav-item active' : 'nav-item'} onClick={() => setLibrary(true)} disabled={busy}>Challenges</button>
      </nav>
      {helperMode ? <button className="connection-button" aria-label="Connection" onClick={() => setConnection(true)}><span className={`status-dot ${session && !expired ? '' : 'status-offline'}`}/><span>{session && !expired ? 'Connected' : 'Connection'}</span></button> : <button className="connection-button" onClick={() => setHelp(true)}><span className={`status-dot ${session && !expired ? '' : 'status-offline'}`}/><span>Workspace help</span></button>}
      <AccountPanel disabled={busy}/>
    </header>
    {error && !loading && <div className="global-notice" role="alert"><Info size={17}/><span>{error}</span><button className="text-button" onClick={() => helperMode ? setConnection(true) : void initialize()}>Retry connection</button></div>}
    {loading ? <main className="loading-screen"><Logo/><LoaderCircle className="spin" size={23}/><p>Preparing your workbench…</p></main> : challenge ? <Workbench key={challenge.id} challenge={challenge} session={session} expired={expired} onExpired={markExpired} onRenew={() => void renew()} renewing={renewing} onBusy={setBusy} onHelp={() => setHelp(true)} /> : helperMode ? <main className="helper-onboarding"><section className="helper-card"><span className="eyebrow">MIDNIGHT WORKBENCH</span><h1>Your workbench, powered locally.</h1><HelperConnection busy={busy} onPaired={async () => { const ready = await initialize(); if (ready) setConnection(false); return ready; }} onDisconnect={() => { setSession(null); setError(null); }} onStatus={setHelperStatus}/></section></main> : <main className="loading-screen"><Database size={36}/><h1>Your workbench is waiting.</h1><p>We couldn’t load the challenge library.</p><button className="button primary" onClick={() => void initialize()}>Reconnect to QueryLab</button></main>}
    {library && <ChallengeLibrary challenges={challenges} selected={challenge?.id} onChoose={choose} onClose={() => setLibrary(false)} />}
    {helperMode && connection && challenge && <Dialog title="Connect your local helper" onClose={() => setConnection(false)}><div className="dialog-body"><HelperConnection key={getHelperToken() ? 'paired' : 'unpaired'} busy={busy} onPaired={async () => { const ready = await initialize(); if (ready) setConnection(false); return ready; }} onDisconnect={() => { setSession(null); setExpired(false); setError(null); setHelperStatus(null); }} onStatus={setHelperStatus}/>{helperStatus && <p className="sr-only">{helperStatus.database.connected ? 'Local database available' : 'Local database unavailable'}</p>}</div></Dialog>}
    {help && <Dialog title="Your SQL workbench" onClose={() => setHelp(false)}><div className="dialog-body help-content"><p>Practise realistic SQL problems in your own anonymous MySQL workspace. No account needed.</p><dl><dt>Run <kbd>Ctrl / ⌘ + Enter</kbd></dt><dd>Execute highlighted SQL, or the full editor script when nothing is selected. Separate SELECT or WITH queries can start on new lines without semicolons. Other statements and routine bodies still need their normal separators. Changes remain until reset or expiry. Run does not grade your answer.</dd><dt>Submit <kbd>Ctrl / ⌘ + Shift + Enter</kbd></dt><dd>Check the full editor script against fresh fixtures. Your practice data stays unchanged.</dd><dt>Reset workspace</dt><dd>Restore practice tables, data and routines. Your SQL draft stays in the editor.</dd><dt>Browser drafts</dt><dd>Drafts are saved per challenge in this browser. Clearing browser storage removes them; they do not sync across devices.</dd><dt>Session expiry</dt><dd>Practice workspaces expire after one hour without running SQL or inspecting data. You can start a fresh workspace and keep your browser drafts.</dd><dt>Keyboard editing</dt><dd>Tab inserts at the cursor. Select text to indent its lines together; Shift+Tab outdents. Press Escape to move to the results tabs, then Tab to continue through the workspace.</dd></dl></div></Dialog>}
  </div>;
}

function Workbench({ challenge, session, expired, onExpired, onRenew, renewing, onBusy, onHelp }: { challenge: Challenge; session: Session | null; expired: boolean; onExpired: () => void; onRenew: () => void; renewing: boolean; onBusy: (busy: boolean) => void; onHelp: () => void }) {
  const account = useAccount();
  const storageKey = `querylab:draft:${challenge.dataset}:${challenge.id}:v${challenge.version}`;
  const [sqlText, setSqlText] = useState(() => { try { return localStorage.getItem(storageKey) ?? challenge.starter_sql; } catch { return challenge.starter_sql; } });
  const [saved, setSaved] = useState(true);
  const [schema, setSchema] = useState<Schema | null>(null);
  const [schemaReadySession, setSchemaReadySession] = useState<Session | null>(null);
  const [schemaReadyRevision, setSchemaReadyRevision] = useState(-1);
  const [schemaError, setSchemaError] = useState<string | null>(null);
  const [hintCount, setHintCount] = useState(() => readAssistance(storageKey).hintsUsed);
  const hintsUsed = useRef(hintCount);
  hintsUsed.current = Math.max(hintsUsed.current, hintCount);
  const solutionViewed = useRef(readAssistance(storageKey).solutionViewed);
  const submissionSnapshot = useRef<SubmissionSnapshot | null>(null);
  const resumedGrading = useRef(false);
  const [mobilePane, setMobilePane] = useState('editor');
  const [narrowView, setNarrowView] = useState(() => window.matchMedia('(max-width: 899px)').matches);
  const [schemaOpen, setSchemaOpen] = useState(false);
  const [focused, setFocused] = useState(false);
  const priorPanels = useRef({ schemaOpen: false, mobilePane: 'editor' });
  const [resultsOpen, setResultsOpen] = useState(false);
  const [resultsHeight, setResultsHeight] = useState(30);
  const queryPanels = useRef<HTMLDivElement>(null);
  const sqlEditor = useRef<SqlEditorHandle>(null);
  const [hintsOpen, setHintsOpen] = useState(false);
  const schemaToggle = useRef<HTMLButtonElement>(null);
  const focusToggle = useRef<HTMLButtonElement>(null);
  const resultsToggle = useRef<HTMLButtonElement>(null);
  const toggleFocus = () => {
    if (focused) { setSchemaOpen(priorPanels.current.schemaOpen); setMobilePane(priorPanels.current.mobilePane); }
    else { priorPanels.current = { schemaOpen, mobilePane }; setSchemaOpen(false); setMobilePane('editor'); }
    setFocused(value => !value);
    if (executionError) setResultsOpen(true);
    requestAnimationFrame(() => {
      const toggle = focusToggle.current;
      if (toggle?.getClientRects().length) toggle.focus();
      else document.querySelector<HTMLButtonElement>('.mobile-tabs button[aria-pressed="true"]')?.focus();
    });
  };
  const closeSchema = () => { setSchemaOpen(false); setMobilePane('editor'); requestAnimationFrame(() => schemaToggle.current?.focus()); };
  const [tab, setTab] = useState<'run' | 'submit'>('run');
  const [result, setResult] = useState<ExecutionResult | null>(null);
  const [feedback, setFeedback] = useState<ExecutionResult | null>(null);
  const [executionError, setExecutionError] = useState<{ mode: 'run' | 'submit'; message: string } | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [job, setJob] = useState<Job | null>(null);
  const [pending, setPending] = useState(false);
  const [reset, setReset] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [solutionDialog, setSolutionDialog] = useState(false);
  const [solution, setSolution] = useState<{ sql: string; explanation: string } | null>(null);
  const [solutionError, setSolutionError] = useState<string | null>(null);
  const [solutionLoading, setSolutionLoading] = useState(false);
  const [resultIndex, setResultIndex] = useState(0);
  const [schemaRevision, setSchemaRevision] = useState(0);
  const [canceling, setCanceling] = useState(false);
  const mounted = useRef(true);
  const activeJob = useRef<string | null>(null);
  const activeMode = useRef<'run' | 'submit'>('run');
  const pollingTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const busy = pending || resetting || Boolean(job && ['running', 'queued'].includes(job.status));
  useEffect(() => { onBusy(busy); return () => onBusy(false); }, [busy, onBusy]);
  useEffect(() => {
    const viewport = window.matchMedia('(max-width: 899px)');
    const update = () => setNarrowView(viewport.matches);
    viewport.addEventListener('change', update);
    return () => viewport.removeEventListener('change', update);
  }, []);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; if (pollingTimer.current) clearTimeout(pollingTimer.current); }; }, []);
  useEffect(() => {
    try { localStorage.setItem(storageKey, sqlText); setSaved(true); } catch { setSaved(false); }
  }, [sqlText, storageKey]);
  useEffect(() => {
    if (!session || expired || !challenge.ready) return;
    const controller = new AbortController(); setSchemaError(null); setSchemaReadySession(null);
    request<Schema>(`/schema?challenge_id=${encodeURIComponent(challenge.id)}`, undefined, controller.signal).then(next => { if (!controller.signal.aborted) { setSchema(next); setSchemaReadySession(session); setSchemaReadyRevision(schemaRevision); } }).catch(failure => { if (controller.signal.aborted || failure instanceof Error && failure.name === 'AbortError') return; setSchemaError(errorMessage(failure)); if (isExpired(failure)) onExpired(); });
    return () => controller.abort();
  }, [challenge.id, challenge.ready, session, schemaRevision, expired, onExpired]);
  const recordGrading = (result: ExecutionResult) => {
    const snapshot = submissionSnapshot.current;
    if (!snapshot || result.mode !== 'submit' || !result.grading) return;
    submissionSnapshot.current = null;
    clearActiveSubmission(snapshot.userId);
    const assistance = readAssistance(storageKey);
    const attempt = completedAttempt({ ...snapshot, hintsUsed: Math.max(snapshot.hintsUsed, hintsUsed.current, assistance.hintsUsed), solutionViewed: snapshot.solutionViewed || solutionViewed.current || assistance.solutionViewed }, result);
    if (attempt) account.record(attempt);
  };
  const poll = async (id: string, mode: 'run' | 'submit') => {
    try {
      const next = await request<Job>(`/jobs/${id}`);
      if (!mounted.current || activeJob.current !== id) return;
      setJob(next);
      if (next.status === 'queued' || next.status === 'running') { pollingTimer.current = setTimeout(() => void poll(id, mode), 400); return; }
      activeJob.current = null; setCanceling(false);
      if (resumedGrading.current) { resumedGrading.current = false; setSchemaRevision(count => count + 1); }
      if (submissionSnapshot.current) clearActiveSubmission(submissionSnapshot.current.userId);
      if (next.status === 'completed' && next.result) { if (mode === 'run') { setResult(next.result); setSchemaRevision(count => count + 1); } else { setFeedback(next.result); recordGrading(next.result); } }
      else if (next.status === 'cancelled') setNotice('Execution cancelled. Your SQL draft is unchanged. Reset the workspace if you want to restore practice data.');
      else setExecutionError({ mode, message: next.error?.message ?? 'The SQL job did not complete. Please try again.' });
    } catch (failure) {
      if (!mounted.current) return;
      setExecutionError({ mode, message: `${errorMessage(failure)} Checking has stopped; the SQL job may still be running. Use Cancel before trying again.` });
      if (isExpired(failure)) { if (submissionSnapshot.current) clearActiveSubmission(submissionSnapshot.current.userId); onExpired(); activeJob.current = null; setJob(null); }
    }
  };
  const execute = async (mode: 'run' | 'submit') => {
    const sqlToExecute = mode === 'run' ? sqlEditor.current?.getRunSql() ?? sqlText : sqlText;
    if (busy || !challenge.ready || expired || !session || schemaReadySession !== session || schemaReadyRevision !== schemaRevision || !sqlToExecute.trim()) return;
    submissionSnapshot.current = mode === 'submit' && account.user ? {
      id: crypto.randomUUID(), userId: account.user.id,
      challenge: { id: challenge.id, version: challenge.version, title: challenge.title, type: challenge.type, dataset: challenge.dataset },
      hintsUsed: hintCount, solutionViewed: solutionViewed.current,
    } : null;
    setPending(true); setTab(mode); setResultsOpen(true); setMobilePane('editor'); setExecutionError(null); setNotice(null); setResultIndex(0);
    if (mode === 'run') setResult(null); else setFeedback(null);
    try {
      const started = await request<{ job_id: string; status: 'queued' }>(`/${mode}`, { challenge_id: challenge.id, sql: sqlToExecute });
      if (!mounted.current) return;
      activeJob.current = started.job_id; setJob({ ...started, result: null, error: null });
      if (submissionSnapshot.current) saveActiveSubmission(started.job_id, helperMode ? getHelperUrl() : location.origin, submissionSnapshot.current);
      activeMode.current = mode;
      void poll(started.job_id, mode);
    } catch (failure) { submissionSnapshot.current = null; setExecutionError({ mode, message: errorMessage(failure) }); if (isExpired(failure)) onExpired(); }
    finally { if (mounted.current) setPending(false); }
  };
  const cancel = async () => {
    if (!job || canceling) return;
    setCanceling(true);
    try {
      const cancelled = await request<Job>(`/jobs/${job.job_id}/cancel`, {});
      if (pollingTimer.current) clearTimeout(pollingTimer.current);
      setExecutionError(null);
      setJob(cancelled);
      if (['queued', 'running'].includes(cancelled.status)) {
        // A kill request can return before the worker has closed its connection.
        // Resume polling even when a previous network failure stopped it.
        activeJob.current = cancelled.job_id;
        void poll(cancelled.job_id, activeMode.current);
      } else {
        activeJob.current = null;
        if (submissionSnapshot.current) clearActiveSubmission(submissionSnapshot.current.userId);
        if (cancelled.status === 'failed') {
          setExecutionError({ mode: activeMode.current, message: cancelled.error?.message ?? 'The SQL job failed before cancellation.' });
        } else {
          setNotice(cancelled.status === 'completed' ? 'The execution finished before cancellation.' : 'Execution cancelled. Your SQL draft is unchanged.');
        }
        if (cancelled.result) { if (cancelled.result.mode === 'run') setResult(cancelled.result); else { setFeedback(cancelled.result); if (cancelled.status === 'completed') recordGrading(cancelled.result); } }
      }
    }
    catch (failure) {
      setExecutionError({ mode: activeMode.current, message: errorMessage(failure) });
      if (isExpired(failure)) { activeJob.current = null; setJob(null); onExpired(); }
    }
    finally { setCanceling(false); }
  };
  const doReset = async () => {
    setResetting(true);
    try { await request('/reset', { challenge_id: challenge.id }); setReset(false); setResult(null); setFeedback(null); setJob(null); setExecutionError(null); setNotice('Practice data and routines restored. Your SQL draft is unchanged.'); setSchemaRevision(count => count + 1); }
    catch (failure) { setReset(false); setResultsOpen(true); setExecutionError({ mode: tab, message: errorMessage(failure) }); if (isExpired(failure)) onExpired(); }
    finally { setResetting(false); }
  };
  const revealSolution = async () => {
    setSolutionLoading(true); setSolutionError(null);
    try { setSolution(await request(`/challenges/${challenge.id}/solution`)); solutionViewed.current = true; rememberAssistance(storageKey, hintCount, true); }
    catch (failure) { setSolutionError(errorMessage(failure)); if (isExpired(failure)) { if (helperMode) setSolutionDialog(false); onExpired(); } }
    finally { setSolutionLoading(false); }
  };
  useEffect(() => { if (executionError) { setResultsOpen(true); setMobilePane('editor'); } }, [executionError]);
  const schemaReady = schemaReadySession === session && schemaReadyRevision === schemaRevision;
  const available = Boolean(challenge.ready && session && !expired && schemaReady);
  useEffect(() => {
    if (!session || expired || !challenge.ready || !account.user || activeJob.current) return;
    const restored = readActiveSubmission(account.user.id, helperMode ? getHelperUrl() : location.origin, challenge);
    if (!restored) return;
    let disposed = false;
    setPending(true);
    void request<Job>(`/jobs/${encodeURIComponent(restored.jobId)}`).then(next => {
      if (disposed || !mounted.current || activeJob.current) return;
      submissionSnapshot.current = restored.snapshot;
      setTab('submit'); setResultsOpen(true); setJob(next); setMobilePane('editor');
      if (next.status === 'running' || next.status === 'queued') {
        resumedGrading.current = true;
        activeJob.current = next.job_id; activeMode.current = 'submit'; void poll(next.job_id, 'submit');
      } else {
        setSchemaRevision(count => count + 1);
        clearActiveSubmission(restored.snapshot.userId);
        if (next.status === 'completed' && next.result) { setFeedback(next.result); recordGrading(next.result); }
        else setNotice('The previous submission did not complete grading. Submit again when you are ready.');
      }
    }).catch(failure => {
      if (!disposed && mounted.current) {
        if (failure instanceof ApiError && [401, 404].includes(failure.status)) {
          clearActiveSubmission(restored.snapshot.userId);
          setNotice('The previous grading result is no longer available. Your SQL draft is saved; submit again when you are ready.');
        } else setNotice('The previous grading result could not be checked. Your SQL draft is saved; refresh to try again.');
      }
    }).finally(() => { if (!disposed && mounted.current) setPending(false); });
    return () => { disposed = true; if (mounted.current) setPending(false); };
  }, [account.user?.id, session, expired, challenge.id]);
  const activeResult = tab === 'run' ? result : feedback;
  const rows = result?.result_sets.reduce((sum, set) => sum + set.rows.length, 0);
  const editorSchema = Object.fromEntries((schema?.tables ?? []).map(table => [table.name, table.columns.map(column => column.name)]));
  const challengeViewActive = !focused && (narrowView ? mobilePane === 'brief' : !schemaOpen);
  const schemaViewActive = !focused && schemaOpen && (!narrowView || mobilePane === 'schema');
  return <>
    <div className="task-context"><span>{challenge.id}</span><span>{challenge.title}</span></div>
    <nav className={`mobile-tabs support-${focused ? 'none' : schemaOpen ? 'schema' : 'brief'}`} aria-label="Workspace panes">
      <button className={challengeViewActive ? 'active' : ''} aria-pressed={challengeViewActive} onClick={() => { if (focused) toggleFocus(); setMobilePane('brief'); setSchemaOpen(false); }}><BookOpen size={16}/>Challenge</button>
      <button className={mobilePane === 'editor' ? 'active' : ''} aria-pressed={mobilePane === 'editor'} onClick={() => { setMobilePane('editor'); setSchemaOpen(false); }}><Code2 size={16}/>Editor</button>
      <button className={schemaViewActive ? 'active' : ''} aria-pressed={schemaViewActive} onClick={() => { if (focused) toggleFocus(); setSchemaOpen(true); setMobilePane('schema'); }}><Database size={16}/>Schema</button>
    </nav>
    <main className={`workbench mobile-${mobilePane}${schemaOpen ? ' schema-open' : ''}${focused ? ' focus-mode' : ''}`}>
      <aside className="brief-pane" aria-label="Challenge brief">
        <div className="challenge-meta"><span>{challenge.id}</span><span>/</span><span>{challenge.dataset_name}</span></div>
        <h1>{challenge.title}</h1>
        <h2 className="overview-label">Overview</h2>
        <p className="scenario">{challenge.summary || challenge.scenario}</p>
        {!challenge.ready && <div className="planned-notice"><Clock3 size={18}/><div><strong>In development</strong><p>Try OS-Q01, OS-F01 or OS-P01 for an executable challenge.</p></div></div>}
        <details className="brief-disclosure requirements-section">
          <summary><ChevronRight size={17}/><span>Requirements</span><span className="rule-count">{challenge.requirements.length} rules</span></summary>
          {challenge.scenario && challenge.scenario !== challenge.summary && <p className="full-scenario">{challenge.scenario}</p>}
          <ol className="requirements-list">{challenge.requirements.map((requirement, index) => <li key={index}><span className="requirement-number">{index + 1}</span><p>{requirement}</p></li>)}</ol>
        </details>
        <details className="brief-disclosure output-contract">
          <summary><ChevronRight size={17}/><span>Expected output</span></summary>
          {challenge.expected_columns?.length > 0 ? <><p>Return these columns in the stated order. Follow the result-ordering rule in Requirements.</p><div className="column-chips">{challenge.expected_columns.map(column => <code key={column}>{column}</code>)}</div></> : <p>Follow the routine signature, return values and behavior specified in Requirements.</p>}
        </details>
        <div className="guidance">
          <div className="guidance-actions"><button className="text-action" aria-expanded={hintsOpen} aria-controls="challenge-hints" disabled={!challenge.hints.length} onClick={() => { setHintsOpen(value => !value); if (!hintCount) { setHintCount(1); rememberAssistance(storageKey, 1, solutionViewed.current); } }}><Lightbulb size={19}/>{hintsOpen ? 'Hide hints' : 'Get a hint'}</button>
          <details className="more-help"><summary>More help</summary><button className="text-action" disabled={!challenge.ready} onClick={() => { setSolutionDialog(true); setSolution(null); }}>View explained solution</button><button className="text-action" onClick={onHelp}>Workspace help</button>{challenge.objective && <p>{challenge.objective}</p>}</details></div>
          <div id="challenge-hints" hidden={!hintsOpen}>{challenge.hints.slice(0, hintCount).map((hint, index) => <div className="hint" key={index}><span>Hint {index + 1}</span><p>{hint}</p></div>)}{hintCount < challenge.hints.length && <button className="button hint-button" onClick={() => { setHintCount(count => count + 1); rememberAssistance(storageKey, hintCount + 1, solutionViewed.current); }}><Lightbulb size={17}/>Reveal hint {hintCount + 1} of {challenge.hints.length}</button>}</div>
        </div>
      </aside>
      <section className="center-pane" aria-label="SQL workspace">
        {expired && <div className="workspace-notice expiry-notice" role="alert"><Clock3 size={18}/><div><strong>{helperMode ? 'Your helper pairing has expired.' : 'Your practice workspace has expired.'}</strong><span>{helperMode ? 'Pair again to continue. ' : 'Start fresh to restore practice data. '}{saved ? 'Your browser draft is safe.' : 'Keep this tab open to retain your unsaved SQL.'}</span></div><button className="button small primary" onClick={onRenew} disabled={renewing}>{renewing ? 'Preparing…' : helperMode ? 'Pair helper' : 'Start fresh'}</button></div>}
        {helperMode && !session && !expired && <div className="workspace-notice" role="status"><Info size={17}/><span>Your helper is disconnected. Keep editing, then use Connection to reconnect and run your SQL.</span></div>}
        {challenge.ready && session && !expired && !schemaReady && !schemaError && <div className="workspace-notice" role="status"><LoaderCircle className="spin" size={17}/><span>Preparing your practice data. Your editor is ready while the database loads.</span></div>}
        {schemaError && <div className="workspace-notice" role="alert"><Info size={17}/><span>{schemaError}</span><button className="button" onClick={() => setSchemaRevision(count => count + 1)}>Retry schema</button></div>}
        {notice && <div className="workspace-notice" role="status"><CheckCircle2 size={17}/><span>{notice}</span><button className="icon-button" onClick={() => setNotice(null)} aria-label="Dismiss notice"><X size={15}/></button></div>}
        <div ref={queryPanels} className={`query-panels${resultsOpen ? ' results-expanded' : ''}`}>
        <div id="sql-editor-panel" className="editor-panel">
          <div className="editor-toolbar">
            <h2>SQL editor</h2>
            <div className="editor-actions">
              {focused && <button className="button" onClick={() => { toggleFocus(); setMobilePane('brief'); }}><BookOpen size={16}/>Challenge</button>}
              <button ref={schemaToggle} className="button schema-toggle" aria-expanded={schemaViewActive} aria-controls="schema-dock" disabled={focused} onClick={() => { setSchemaOpen(value => !value); setMobilePane(schemaOpen ? 'editor' : 'schema'); }}><Table2 size={17}/>Schema</button>
              <button ref={focusToggle} className="button" aria-pressed={focused} aria-expanded={!focused} onClick={toggleFocus}><Maximize2 size={16}/>{focused ? 'Exit focus' : 'Focus'}</button>
              <button id="run-sql" className="button run-button" disabled={!available || busy || !sqlText.trim()} onClick={() => void execute('run')} title="Run highlighted SQL, or the full script when nothing is selected (Ctrl/⌘ + Enter)"><Play size={17}/>Run</button>
              <button className="button primary submit-button" disabled={!available || busy || !sqlText.trim()} onClick={() => void execute('submit')} title="Submit answer (Ctrl/⌘ + Shift + Enter)"><Send size={16}/>Submit</button>
              <details className="workspace-menu"><summary aria-label="Workspace menu" title="Workspace menu"><MoreHorizontal size={20}/></summary><div className="workspace-menu-items"><button className="text-action" disabled={!available || busy} onClick={event => { const menu = event.currentTarget.closest('details'); menu?.removeAttribute('open'); menu?.querySelector('summary')?.focus(); setReset(true); }}><RotateCcw size={16}/>Reset workspace</button><button className="text-action" onClick={onHelp}><CircleHelp size={16}/>Workspace help</button></div></details>
              {busy && <button className="button cancel-button" disabled={pending || resetting || canceling} onClick={() => void cancel()}><Square size={13}/>{resetting ? 'Resetting…' : canceling ? 'Cancelling…' : 'Cancel'}</button>}
            </div>
          </div>
          <Suspense fallback={<div className="sql-editor empty-state"><LoaderCircle className="spin" size={20}/><p>Loading SQL editor…</p></div>}><SqlEditor ref={sqlEditor} value={sqlText} onChange={setSqlText} onRun={() => void execute('run')} onSubmit={() => void execute('submit')} onExit={() => resultsOpen ? document.getElementById(`${tab}-tab`)?.focus() : resultsToggle.current?.focus()} schema={editorSchema}/></Suspense>
          <div className="editor-status"><span id="editor-shortcuts" className="sr-only">Control or Command Enter runs highlighted SQL, or the full script when nothing is selected. Add Shift to submit the full script. Escape moves to results.</span><span className={saved ? 'draft-status' : 'storage-warning'} role={saved ? undefined : 'alert'}>{saved ? <Check size={14}/> : <Info size={15}/>} {saved ? 'Draft saved' : 'Browser storage unavailable · draft not saved'}</span></div>
        </div>
        {resultsOpen && !narrowView && <ResultsDivider panels={queryPanels} value={resultsHeight} onChange={setResultsHeight}/>}
        <section id="results-panel" className={`results-panel${resultsOpen ? ' results-open' : ''}`} aria-label="Results" style={resultsOpen ? { flexBasis: `calc(${resultsHeight}% - ${RESULTS_DIVIDER_HEIGHT * resultsHeight / 100}px)` } : undefined}>
          <div className="results-strip"><button ref={resultsToggle} className="results-toggle" aria-expanded={resultsOpen} aria-controls="result-body" onClick={() => { setResultsOpen(value => !value); resultsToggle.current?.focus(); }}>{resultsOpen ? <ChevronDown size={18}/> : <ChevronRight size={18}/>}Results</button><span className="results-summary" role="status">{executionError ? 'Execution error' : busy ? 'Running…' : tab === 'run' && result ? `${rows} rows · not graded` : tab === 'submit' && feedback?.grading ? feedback.grading.passed ? 'Submission passed' : 'Submission needs work' : 'Run your query to see results'}</span></div>
          <div id="result-body" className="result-body" hidden={!resultsOpen}>
          <div className="results-header"><div className="result-tabs" role="tablist" aria-label="SQL output"><button id="run-tab" role="tab" aria-selected={tab === 'run'} aria-controls="result-content" tabIndex={tab === 'run' ? 0 : -1} onClick={() => setTab('run')} onKeyDown={event => { if (event.key === 'ArrowRight' || event.key === 'ArrowLeft') { setTab('submit'); document.getElementById('submit-tab')?.focus(); } }}><Table2 size={15}/><span>Practice results</span></button><button id="submit-tab" role="tab" aria-selected={tab === 'submit'} aria-controls="result-content" tabIndex={tab === 'submit' ? 0 : -1} onClick={() => setTab('submit')} onKeyDown={event => { if (event.key === 'ArrowRight' || event.key === 'ArrowLeft') { setTab('run'); document.getElementById('run-tab')?.focus(); } }}><CheckCircle2 size={15}/><span>Submission feedback</span></button></div><span className="result-meta" role="status" aria-live="polite">{busy ? <><LoaderCircle className="spin" size={13}/>{job?.status === 'queued' ? 'Queued' : resetting ? 'Resetting' : 'Running'}</> : tab === 'run' && result ? `${rows} rows · not graded` : tab === 'submit' && feedback ? `${feedback.elapsed_ms} ms` : 'Ready when you are'}</span></div>
          <div id="result-content" role="tabpanel" aria-labelledby={`${tab}-tab`} className="result-content" aria-busy={busy}>
            {executionError?.mode === tab ? <div className="execution-error" role="alert"><XCircle size={20}/><div><h3>We couldn’t complete that {tab === 'run' ? 'run' : 'submission'}.</h3><p>{executionError.message}</p><span>Your SQL draft is unchanged.</span></div></div> : busy ? <div className="empty-state" role="status"><LoaderCircle className="spin" size={25}/><h3>{resetting ? 'Restoring practice data…' : tab === 'submit' ? 'Checking your SQL against fresh fixtures…' : job?.status === 'queued' ? 'Your SQL is in the queue…' : 'Running your SQL…'}</h3><p>{tab === 'submit' ? 'Your practice workspace stays unchanged.' : 'You can cancel execution from the toolbar.'}</p></div> : tab === 'submit' && feedback?.grading ? <div className="grading-results"><div role="status" className={`grading-banner ${feedback.grading.passed ? 'passed' : 'needs-work'}`}>{feedback.grading.passed ? <CheckCircle2 size={24}/> : <Info size={24}/>}<div><h3>{feedback.grading.passed ? 'Your answer passes all checks.' : 'A few things to revisit.'}</h3><p>{feedback.grading.passed ? 'Your SQL satisfies the tested challenge rules.' : 'Use the feedback below, adjust your SQL and submit again.'}</p></div></div><ul className="grading-checks">{feedback.grading.checks.map((check, index) => <li key={index}>{check.passed ? <CheckCircle2 size={16}/> : <XCircle size={16}/>}<div><strong>{check.name}</strong><p>{check.message}</p></div></li>)}</ul></div> : activeResult && activeResult.result_sets.length > 0 ? <><div className="result-set-controls">{activeResult.result_sets.length > 1 && <label>Result set <select value={resultIndex} onChange={event => setResultIndex(Number(event.target.value))}>{activeResult.result_sets.map((_, index) => <option key={index} value={index}>{index + 1} of {activeResult.result_sets.length}</option>)}</select></label>}<span><Clock3 size={12}/>{activeResult.elapsed_ms} ms</span></div><ResultsTable result={activeResult.result_sets[Math.min(resultIndex, activeResult.result_sets.length - 1)]}/></> : activeResult ? <p className="result-message">Script completed in {activeResult.elapsed_ms} ms. No result sets returned.</p> : <div className="empty-state"><p>{tab === 'run' ? 'Run SQL to explore practice data. Results are not graded.' : 'Submit SQL to check your answer against fresh fixtures.'}</p></div>}
          </div>
          </div>
        </section>
        </div>
      </section>
      <div id="schema-dock" className="schema-dock"><SchemaExplorer schema={schema} error={schemaError} challenge={challenge} disabled={!available || busy} onRetry={() => setSchemaRevision(count => count + 1)} onExpired={onExpired} onClose={closeSchema}/></div>
    </main>
    {reset && <Dialog title="Reset your practice workspace?" onClose={() => !resetting && setReset(false)}><div className="dialog-body"><p>This restores the {challenge.dataset_name.toLowerCase()} tables, data and routines to their starting state. Any practice changes will be removed.</p><div className="dialog-callout"><ShieldCheck size={19}/><span><strong>Your SQL draft stays exactly as it is.</strong><br/>Editor drafts are saved separately in this browser.</span></div><div className="dialog-actions"><button className="button" onClick={() => setReset(false)} disabled={resetting}>Keep practising</button><button className="button primary" onClick={() => void doReset()} disabled={resetting}>{resetting ? <LoaderCircle className="spin" size={16}/> : <RotateCcw size={16}/>}Reset workspace</button></div></div></Dialog>}
    {solutionDialog && <Dialog title={solution ? 'An explained solution' : 'Ready to see one approach?'} onClose={() => setSolutionDialog(false)} wide={Boolean(solution)}><div className="dialog-body">{solution ? <><p className="solution-intro">This is one valid approach. Other solutions can satisfy the same business rules.</p><pre className="solution-code"><code>{solution.sql}</code></pre><h3>Why it works</h3><p className="solution-explanation">{solution.explanation}</p></> : <><div className="solution-warning"><Lightbulb size={26}/><p>The solution reveals a complete working answer. You can explore the progressive hints first if you’d like a smaller nudge.</p></div>{solutionError && <p className="inline-error" role="alert">{solutionError}</p>}<div className="dialog-actions"><button className="button" onClick={() => setSolutionDialog(false)}>Keep working</button><button className="button primary" onClick={() => void revealSolution()} disabled={solutionLoading}>{solutionLoading ? <LoaderCircle className="spin" size={16}/> : <BookOpen size={16}/>}Reveal solution</button></div></>}</div></Dialog>}
  </>;
}

function SchemaExplorer({ schema, error, challenge, disabled, onRetry, onExpired, onClose }: { schema: Schema | null; error: string | null; challenge: Challenge; disabled: boolean; onRetry: () => void; onExpired: () => void; onClose: () => void }) {
  const [search, setSearch] = useState('');
  const [expanded, setExpanded] = useState<string[]>([]);
  const [sample, setSample] = useState<{ table: string; result: ResultSet | null } | null>(null);
  const [sampleError, setSampleError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const exportDataset = async () => {
    setDownloading(true); setDownloadError(null);
    try { await downloadDataset(challenge.dataset); }
    catch (failure) { setDownloadError(errorMessage(failure)); if (isExpired(failure)) onExpired(); }
    finally { setDownloading(false); }
  };
  const sampleRequest = useRef(0);
  const inspect = async (table: string) => {
    const requestId = ++sampleRequest.current;
    setSample({ table, result: null }); setSampleError(null);
    try { const result = await request<ResultSet>(`/schema/sample?challenge_id=${encodeURIComponent(challenge.id)}&table=${encodeURIComponent(table)}`); if (sampleRequest.current === requestId) setSample({ table, result }); }
    catch (failure) { if (sampleRequest.current === requestId) setSampleError(errorMessage(failure)); if (isExpired(failure)) onExpired(); }
  };
  const filtered = schema?.tables.filter(table => `${table.name} ${table.columns.map(column => column.name).join(' ')}`.toLowerCase().includes(search.toLowerCase())) ?? [];
  return <aside className="schema-pane" aria-label="Database schema"><div className="schema-title"><div><Database size={17}/><h2>Database schema</h2></div><button className="icon-button" onClick={onClose} aria-label="Close schema"><X size={20}/></button></div><p className="schema-dataset">{challenge.dataset_name}<span>{schema?.tables.length ?? '—'} tables</span></p><label className="search-field"><Search size={16}/><input aria-label="Search tables or columns" placeholder="Search tables or columns…" value={search} onChange={event => setSearch(event.target.value)}/><kbd>/</kbd></label><div className="schema-list">{error ? <div className="schema-empty"><Info size={20}/><p>{error}</p><button className="button small" onClick={onRetry}>Retry schema</button></div> : !challenge.ready ? <div className="schema-empty"><Database size={24}/><p>The schema preview will be available when this challenge is ready.</p></div> : !schema ? <div className="schema-empty"><LoaderCircle size={22} className="spin"/><p>Loading practice schema…</p></div> : filtered.length === 0 ? <div className="schema-empty"><Search size={23}/><p>No matching tables or columns.</p></div> : filtered.map(table => {
    const open = expanded.includes(table.name);
    return <section className="schema-table" key={table.name}><button className="schema-table-heading" aria-expanded={open} onClick={() => setExpanded(values => open ? values.filter(value => value !== table.name) : [...values, table.name])}><Table2 size={16}/><span>{table.name}</span>{open ? <ChevronDown size={14}/> : <ChevronRight size={14}/>}</button>{open && <><ul className="schema-columns">{table.columns.filter(column => table.name.toLowerCase().includes(search.toLowerCase()) || column.name.toLowerCase().includes(search.toLowerCase())).map(column => <li key={column.name} title={`${column.name}: ${column.type}${column.nullable ? ', nullable' : ', required'}${column.key ? `, ${column.key}` : ''}`}>{column.key === 'PRI' ? <KeyRound className="primary-key" size={13} aria-label="Primary key"/> : column.key === 'MUL' ? <KeyRound className="foreign-key" size={13} aria-label="Indexed or foreign key"/> : <span className="column-icon" aria-hidden="true"/>}<code>{column.name}</code><span className="column-type">{column.type}</span></li>)}</ul><button className="preview-rows" disabled={disabled} onClick={() => void inspect(table.name)}>Preview rows<ArrowRight size={12}/></button></>}</section>;
  })}</div><div className="schema-legend"><span><KeyRound size={12} className="primary-key"/>Primary key</span><span><KeyRound size={12} className="foreign-key"/>Index / relation</span></div>{schema?.relationships.length ? <details className="relationship-details"><summary>Table relationships<ChevronDown size={14}/></summary>{schema.relationships.map((relationship, index) => <p key={index}><code>{relationship.from_table}.{relationship.from_column}</code><ArrowDown size={12}/><code>{relationship.to_table}.{relationship.to_column}</code></p>)}</details> : null}
    {helperMode && <div className="dataset-export"><button className="button small" disabled={disabled || downloading} onClick={() => void exportDataset()}>{downloading ? <LoaderCircle size={15} className="spin"/> : <FileCode2 size={15}/>}Download dataset SQL</button><p>Starting data for your SQL client. Run this script only in its dedicated QueryLab database.</p>{downloadError && <p role="alert" className="inline-error">{downloadError}</p>}</div>}
    {sample && <Dialog title={`${sample.table} · practice data`} onClose={() => { sampleRequest.current += 1; setSample(null); }} wide><div className="dialog-body"><p className="muted">A small preview of your current practice workspace. Sample rows are not grading fixtures.</p>{sampleError ? <p className="inline-error" role="alert">{sampleError}</p> : sample.result ? <ResultsTable result={sample.result} label={`${sample.table} sample rows`}/> : <div className="empty-state"><LoaderCircle className="spin" size={24}/><p>Loading sample rows…</p></div>}</div></Dialog>}
  </aside>;
}

function ChallengeLibrary({ challenges, selected, onChoose, onClose }: { challenges: Challenge[]; selected?: string; onChoose: (id: string) => void; onClose: () => void }) {
  const [search, setSearch] = useState('');
  const [dataset, setDataset] = useState('all');
  const [type, setType] = useState('all');
  const filtered = challenges.filter(challenge => (dataset === 'all' || challenge.dataset === dataset) && (type === 'all' || challenge.type === type) && `${challenge.id} ${challenge.title} ${challenge.summary}`.toLowerCase().includes(search.toLowerCase()));
  const datasets = [...new Map(challenges.map(challenge => [challenge.dataset, challenge.dataset_name])).entries()];
  return <Dialog title="Find your next challenge" onClose={onClose} wide><div className="dialog-body library-body"><p className="library-intro">Real scenarios. Thoughtful SQL. Pick a problem worth solving.</p><label className="search-field library-search"><Search size={18}/><input autoFocus aria-label="Search challenges" placeholder="Search the challenge library…" value={search} onChange={event => setSearch(event.target.value)}/></label><div className="library-filters"><label>Dataset<select value={dataset} onChange={event => setDataset(event.target.value)}><option value="all">All datasets</option>{datasets.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label><label>Challenge type<select value={type} onChange={event => setType(event.target.value)}><option value="all">All types</option><option value="query">Queries</option><option value="function">Functions</option><option value="procedure">Procedures</option></select></label><span>{filtered.length} challenges</span></div><div className="challenge-grid">{filtered.map(challenge => <button className={`challenge-card ${challenge.id === selected ? 'selected' : ''}`} key={challenge.id} onClick={() => onChoose(challenge.id)}><div className="card-meta"><span>{challenge.id}</span><span className={`availability ${challenge.ready ? 'ready' : ''}`}>{challenge.ready ? 'Ready to practise' : 'In development'}</span></div><h3>{challenge.title}</h3><p>{challenge.summary || challenge.scenario}</p><div className="card-footer"><span className="type-tag">{titleCase(challenge.type)}</span><span>{challenge.dataset_name}</span><ArrowRight size={15}/></div></button>)}</div>{filtered.length === 0 && <div className="empty-state"><Search size={28}/><h3>No challenges found.</h3><p>Try a different search or filter.</p></div>}<p className="library-note"><Info size={14}/>12 challenges across two datasets: six queries, three functions and three procedures.</p></div></Dialog>;
}


