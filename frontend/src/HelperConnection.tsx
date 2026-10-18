import { useEffect, useState } from 'react';
import { CheckCircle2, Copy, Database, Download, Info, LoaderCircle, Unplug } from 'lucide-react';
import { disconnectHelper, getHelperStatus, getHelperToken, getHelperUrl, pairHelper } from './api';
import type { HelperStatus } from './api';

interface HelperDownload { version: string; filename: string; sha256: string; bytes: number; platform: string; requires: string[] }
const downloadPath = `${import.meta.env.BASE_URL}downloads/querylab-helper-windows.zip`;
const formatDownloadSize = (bytes: number) => bytes >= 1024 * 1024
  ? `${(bytes / 1024 / 1024).toLocaleString(undefined, { maximumFractionDigits: 1 })} MB`
  : `${Math.max(1, Math.ceil(bytes / 1024)).toLocaleString()} KB`;

function WindowsHelperSetup() {
  const [download, setDownload] = useState<HelperDownload | null>(null);
  const [checking, setChecking] = useState(true);
  const [downloadError, setDownloadError] = useState(false);
  const [copyMessage, setCopyMessage] = useState('');
  const websiteOrigin = window.location.origin;
  const loadDownload = async (signal?: AbortSignal) => {
    setChecking(true); setDownloadError(false); setDownload(null);
    try {
      const response = await fetch(`${import.meta.env.BASE_URL}downloads/querylab-helper-windows.json`, { cache: 'no-store', signal });
      if (!response.ok) throw new Error('Manifest unavailable');
      const manifest: HelperDownload = await response.json();
      if (manifest.filename !== 'querylab-helper-windows.zip' || manifest.platform !== 'windows' ||
        typeof manifest.version !== 'string' || !manifest.version.trim() ||
        typeof manifest.sha256 !== 'string' || !/^[a-f\d]{64}$/i.test(manifest.sha256) ||
        !Number.isSafeInteger(manifest.bytes) || manifest.bytes <= 0 ||
        !Array.isArray(manifest.requires) || !manifest.requires.includes('Docker Desktop')) throw new Error('Invalid manifest');
      const archive = await fetch(downloadPath, { method: 'HEAD', cache: 'no-store', signal });
      const archiveType = archive.headers.get('content-type') ?? '';
      if (!archive.ok || !/application\/(?:zip|x-zip-compressed|octet-stream)/i.test(archiveType)) throw new Error('Archive unavailable');
      if (!signal?.aborted) setDownload(manifest);
    } catch {
      if (!signal?.aborted) setDownloadError(true);
    } finally { if (!signal?.aborted) setChecking(false); }
  };
  useEffect(() => {
    const controller = new AbortController();
    void loadDownload(controller.signal);
    return () => controller.abort();
  }, []);
  const copyAddress = async () => {
    try {
      await navigator.clipboard.writeText(websiteOrigin);
      setCopyMessage('Website address copied. Paste it into the launcher.');
    } catch { setCopyMessage('Copy was unavailable. Select and copy the website address shown below.'); }
  };
  return <>
    <section className="helper-download" aria-label="Windows helper download">
      <div><strong>Windows helper preview</strong><p>Requires <a href="https://docs.docker.com/desktop/setup/install/windows-install/" target="_blank" rel="noreferrer">Docker Desktop</a> running with Linux containers. Includes a private practice database.</p></div>
      {download && <><a className="button primary helper-download-link" href={downloadPath} download={download.filename}><Download size={17} aria-hidden="true"/>Download Windows helper</a><span className="muted">Windows ZIP · v{download.version} · {formatDownloadSize(download.bytes)}</span></>}
      {checking && <p className="helper-download-feedback" role="status"><LoaderCircle size={16} className="spin" aria-hidden="true"/>Checking the download…</p>}
      {downloadError && <div className="helper-download-feedback"><p role="status">The Windows download is temporarily unavailable. Retry the check, or return when it is available.</p><button className="button" type="button" onClick={() => void loadDownload()}>Retry download check</button></div>}
    </section>
    <details className="helper-setup" open>
      <summary>Set up your helper</summary>
      <ol className="helper-steps">
        <li><strong>Download and extract.</strong><span>Download the Windows ZIP above, choose <b>Extract All</b>, then open the extracted <code>QueryLab-Helper</code> folder.</span></li>
        <li><strong>Open the launcher.</strong><span>Double-click <code>Start-QueryLab-Helper.cmd</code>. It checks Docker Desktop and asks for this website address.</span><button className="button helper-copy-address" type="button" onClick={() => void copyAddress()}><Copy size={15} aria-hidden="true"/>Copy website address</button><label className="helper-address-label" htmlFor="helper-website-address">Website address for the launcher</label><input id="helper-website-address" className="helper-website-address" readOnly value={websiteOrigin} onFocus={event => event.target.select()}/><span className="helper-copy-feedback" role="status">{copyMessage}</span></li>
        <li><strong>Start the helper and copy its code.</strong><span>In the launcher, choose <b>Start helper</b>. The first start downloads the required components. When it is ready, choose <b>Copy pairing code</b>. Keep the helper running while you practise.</span></li>
        <li><strong>Return here and pair.</strong><span>Keep the prefilled Helper URL below. Paste your code into <b>Pairing code</b>, choose <b>Pair helper</b>, and allow local-network access if your browser asks.</span></li>
      </ol>
    </details>
    <details className="helper-setup"><summary>Already running? Find your pairing code</summary><p>Open <code>Start-QueryLab-Helper.cmd</code> from the extracted folder. When the helper is ready, choose <strong>Copy pairing code</strong>. It is separate from your MySQL password.</p></details>
    <details className="helper-setup"><summary>Advanced setup and troubleshooting</summary><p>This download supports Windows with Docker Desktop. A macOS or Linux download is not available yet. If Docker is still starting, wait until it is ready and retry in the launcher.</p><p>If you already use the QueryLab source folder, open PowerShell there and run:</p><pre><code>{`.\\scripts\\setup-helper.ps1 -WebsiteOrigin '${websiteOrigin.replace(/'/g, "''")}'\n.\\scripts\\start-helper.ps1`}</code></pre><p>To retrieve the code for an existing source-based setup:</p><pre><code>{'.\\scripts\\show-helper-code.ps1'}</code></pre></details>
  </>;
}

export default function HelperConnection({ busy, onPaired, onDisconnect, onStatus }: { busy: boolean; onPaired: () => Promise<boolean>; onDisconnect: () => void; onStatus: (status: HelperStatus) => void }) {
  const [url, setUrl] = useState(getHelperUrl);
  const [code, setCode] = useState('');
  const [paired, setPaired] = useState(() => Boolean(getHelperToken()));
  const [status, setStatus] = useState<HelperStatus | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const check = async () => {
    setPending(true); setError(null);
    try { const next = await getHelperStatus(url); setStatus(next); onStatus(next); }
    catch (failure) { setStatus(null); setError(failure instanceof Error ? failure.message : 'Unable to check the helper.'); }
    finally { setPending(false); }
  };
  useEffect(() => { if (paired) void check(); }, []);
  const pair = async (event: React.FormEvent) => {
    event.preventDefault(); if (busy || pending) return;
    setPending(true); setError(null);
    try {
      const next = await getHelperStatus(url); setStatus(next); onStatus(next);
      await pairHelper(url, code.trim()); setPaired(true); setCode('');
      if (!await onPaired()) setError('The helper is paired, but the workspace could not load. Check the MySQL connection below, then retry.');
    } catch (failure) { setError(failure instanceof Error ? failure.message : 'Unable to pair the helper.'); }
    finally { setPending(false); }
  };
  const reconnect = async () => {
    setPending(true); setError(null);
    try { const next = await getHelperStatus(url); setStatus(next); onStatus(next); if (!await onPaired()) setError('Workspace connection failed. Check MySQL locally or disconnect and pair again.'); }
    catch (failure) { setError(failure instanceof Error ? failure.message : 'Unable to reconnect.'); }
    finally { setPending(false); }
  };
  return <div className="helper-content">
    <p>Connect this browser to the helper on your computer. Your SQL runs against a local practice database.</p>
    {!paired && <WindowsHelperSetup/>}
    <form onSubmit={event => void pair(event)} className="helper-form" aria-busy={pending}>
      <label htmlFor="helper-url">Helper URL</label><input id="helper-url" type="url" value={url} onChange={event => { setUrl(event.target.value); setStatus(null); }} disabled={paired || pending || busy} required spellCheck={false} autoComplete="off" aria-describedby="helper-url-description"/><span id="helper-url-description" className="muted">Leave this prefilled address unchanged unless you configured a different helper address. Check connection tests whether it is running.</span>
      {!paired && <><label htmlFor="helper-code">Pairing code</label><input id="helper-code" type="password" value={code} onChange={event => setCode(event.target.value)} disabled={pending || busy} required autoComplete="off" aria-describedby="helper-code-description" placeholder="Paste the code from the launcher"/><span id="helper-code-description" className="muted">Choose Copy pairing code in the helper launcher, then paste it here.</span></>}
      {status && <div className={`helper-status ${status.database.connected ? 'connected' : ''}`} role="status">{status.database.connected ? <CheckCircle2 size={18}/> : <Info size={18}/>}<div><strong>{status.database.connected ? `MySQL connected${status.database.version ? ` · ${status.database.version}` : ''}` : 'MySQL needs attention'}</strong><p>{status.database.message ?? (status.database.connected ? 'Practice databases are managed by your local helper.' : 'Check the MySQL settings in your local environment file, then check again.')}</p></div></div>}
      {error && <p className="inline-error" role="alert">{error}</p>}
      {pending && <p className="muted" role="status">Connecting to your local helper…</p>}
      {busy && <p className="muted">Finish or cancel the active SQL job before changing the connection.</p>}
      <div className="helper-actions">{paired ? <><button className="button primary" type="button" disabled={pending || busy} onClick={() => void reconnect()}>{pending ? <LoaderCircle className="spin" size={16}/> : <Database size={16}/>}Reconnect workspace</button><button className="button" type="button" disabled={pending || busy} onClick={() => { disconnectHelper(); setPaired(false); setStatus(null); setError(null); onDisconnect(); }}><Unplug size={16}/>Disconnect helper</button></> : <button className="button primary" type="submit" disabled={pending || busy || !code.trim()}>{pending ? <LoaderCircle className="spin" size={16}/> : <Database size={16}/>}Pair helper</button>}<button className="button" type="button" disabled={pending || busy} onClick={() => void check()}>Check connection</button></div>
    </form>
    <p className="helper-privacy">Pairing stays in this browser tab. Disconnecting keeps your SQL drafts. Your database password is never entered on this website.</p>
  </div>;
}
