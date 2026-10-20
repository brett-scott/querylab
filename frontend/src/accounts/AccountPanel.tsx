import { useState } from 'react';
import { BarChart3, CheckCircle2, LoaderCircle, LogIn, LogOut } from 'lucide-react';
import Dialog from '../Dialog';
import { useAccount } from './AccountProvider';
import { progressSummary } from './progress';

export default function AccountPanel({ disabled }: { disabled: boolean }) {
  const account = useAccount();
  const [open, setOpen] = useState(false);
  const [working, setWorking] = useState(false);
  if (!account.configured) return null;
  const summary = progressSummary(account.progress);
  const unknown = !account.progress.length && (account.loading || Boolean(account.error));
  const action = async (work: () => Promise<void>) => { setWorking(true); try { await work(); } finally { setWorking(false); } };
  return <>
    <button className="account-button" onClick={() => setOpen(true)} disabled={disabled || account.initializing}>
      {account.user ? <BarChart3 size={17}/> : <LogIn size={17}/>}<span>{account.user ? 'Progress' : 'Sign in'}</span>
    </button>
    {open && <Dialog title={account.user ? 'Your progress' : 'Save your progress'} onClose={() => setOpen(false)} wide={Boolean(account.user)}>
      <div className="dialog-body account-panel">
        {account.error && <p className="inline-error" role="alert">{account.error}</p>}
        {!account.user ? <>
          <p>Keep your challenge results across visits and devices. Signing in is optional; you can always practise as a guest.</p>
          <button className="button primary google-sign-in" disabled={working} onClick={() => void action(account.signIn)}>{working ? <LoaderCircle size={17} className="spin"/> : <LogIn size={17}/>}Continue with Google</button>
          <p className="account-privacy">Only challenge results and hint/solution use are synced. Your SQL, query results and database credentials stay on your computer. Guest attempts are not added to your account.</p>
        </> : <>
          <div className="account-identity"><span>{account.user.email ?? 'Signed in with Google'}</span><button className="text-button" disabled={working} onClick={() => void action(account.signOut)}><LogOut size={15}/>Sign out</button></div>
          <div className="progress-stats">
            <div><strong>{unknown ? '—' : summary.completed}</strong><span>Challenges completed</span></div>
            <div><strong>{unknown ? '—' : summary.attempts}</strong><span>Graded submissions</span></div>
            <div><strong>{unknown || summary.passRate === null ? '—' : `${summary.passRate}%`}</strong><span>Submission pass rate</span></div>
            <div><strong>{unknown ? '—' : summary.unassisted}</strong><span>Passed without hints or solution</span></div>
          </div>
          <div className="progress-sync"><span role="status">{account.loading ? 'Loading saved progress…' : account.pending ? `${account.pending} ${account.pending === 1 ? 'result' : 'results'} waiting to sync` : account.error ? 'Sync unavailable' : 'Progress saved across devices'}</span><button className="text-button" disabled={working || account.loading} onClick={() => void action(account.retry)}>Retry sync</button></div>
          {!account.progress.length && !account.loading ? <p className="progress-empty">Your first graded submission starts your record. Connect your helper and submit a challenge when you are ready.</p> : <>
            <h3>Challenge progress</h3>
            <ul className="progress-list">{account.progress.map(item => <li key={`${item.challenge_id}:${item.challenge_version}`}><div><strong>{item.challenge_id} · {item.challenge_title}</strong><span>v{item.challenge_version} · {item.attempt_count} {Number(item.attempt_count) === 1 ? 'submission' : 'submissions'}</span></div><span className={Number(item.passed_count) ? 'progress-pass' : 'muted'}>{Number(item.passed_count) ? <><CheckCircle2 size={15}/>Completed</> : 'In progress'}</span></li>)}</ul>
            <h3>Recent submissions</h3>
            <ul className="progress-list">{account.recent.map(item => <li key={item.id}><div><strong>{item.challenge_id} · {item.passed ? 'Passed' : 'Needs work'}</strong><span>{new Date(item.completed_at).toLocaleString()} · {item.solution_viewed ? 'Solution viewed' : item.hints_used ? `${item.hints_used} hints used` : 'No hints or solution recorded'}</span></div></li>)}</ul>
          </>}
          <p className="account-privacy">Counts include your saved challenge versions. Only completed grading is counted; Run, errors and cancelled submissions do not affect your pass rate. Results come from your local practice helper.</p>
        </>}
      </div>
    </Dialog>}
  </>;
}
