export interface Challenge {
  id: string; title: string; dataset: string; dataset_name: string; type: 'query' | 'function' | 'procedure'; difficulty: string;
  summary: string; scenario: string; objective: string; requirements: string[]; hints: string[]; starter_sql: string; expected_columns: string[]; ready: boolean; version: string;
}
export interface SchemaColumn { name: string; type: string; nullable: boolean; key: string }
export interface SchemaTable { name: string; columns: SchemaColumn[]; row_count: number }
export interface Schema { dataset: string; tables: SchemaTable[]; relationships: { from_table: string; from_column: string; to_table: string; to_column: string }[] }
export interface ResultSet { columns: string[]; rows: unknown[][]; truncated?: boolean; affected_rows?: number }
export interface ExecutionResult { mode: 'run' | 'submit'; result_sets: ResultSet[]; elapsed_ms: number; grading?: { passed: boolean; checks: { name: string; passed: boolean; message: string }[] } }
export interface Job { job_id: string; status: 'queued' | 'running' | 'completed' | 'failed' | 'cancelled'; result: ExecutionResult | null; error: { code: string; message: string } | null }
export interface Session { expires_at: string; created: boolean; ttl_seconds: number }
export class ApiError extends Error {
  constructor(public code: string, message: string, public status = 0) { super(message); this.name = 'ApiError'; }
}
export const helperMode = import.meta.env.MODE === 'helper' || new URLSearchParams(window.location.search).get('helper') === '1';
const tokenKey = 'querylab:helper:token';
const urlKey = 'querylab:helper:url';
export function validateHelperUrl(value: string): string {
  let url: URL;
  try { url = new URL(value); } catch { throw new ApiError('invalid_helper_url', 'Enter a local helper URL, such as http://127.0.0.1:8765.'); }
  if (url.protocol !== 'http:' || !['localhost', '127.0.0.1', '[::1]'].includes(url.hostname) || url.username || url.password || url.search || url.hash || url.pathname !== '/') {
    throw new ApiError('invalid_helper_url', 'The helper URL must use HTTP on localhost, 127.0.0.1 or [::1], with an optional port and no path.');
  }
  return url.origin;
}
export function getHelperUrl(): string {
  if (activeHelperUrl) return activeHelperUrl;
  try { return validateHelperUrl(localStorage.getItem(urlKey) ?? 'http://127.0.0.1:8765'); } catch { return 'http://127.0.0.1:8765'; }
}
export function getHelperToken(): string | null { try { return sessionStorage.getItem(tokenKey); } catch { return null; } }
export function disconnectHelper() { try { sessionStorage.removeItem(tokenKey); } catch { /* Nothing persisted. */ } }
export interface HelperStatus { mode: string; protocol_version: number; version?: string; database: { connected: boolean; version?: string; message?: string } }
async function fetchApi(path: string, body?: unknown, signal?: AbortSignal, helperUrl?: string, publicRequest = false): Promise<Response> {
  const local = helperUrl !== undefined || helperMode;
  const headers: Record<string, string> = {};
  const base = local ? validateHelperUrl(helperUrl ?? getHelperUrl()) : '';
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  if (local && !publicRequest && getHelperToken()) headers.Authorization = `Bearer ${getHelperToken()}`;
  try { return await fetch(`${base}/api${path}`, { method: body === undefined ? 'GET' : 'POST', credentials: local ? 'omit' : 'same-origin', headers, body: body === undefined ? undefined : JSON.stringify(body), signal }); }
  catch (error) { if (error instanceof Error && error.name === 'AbortError') throw error; throw new ApiError('connection_error', local ? 'Unable to reach your local helper. Check it is running and allow this website to access your local network if your browser asks. Your SQL stays in the editor.' : 'Unable to reach the SQL service. Your SQL remains in the editor. Try again when the service is available.'); }
}
async function readResponse<T>(response: Response): Promise<T> {
  let data: unknown;
  try { data = await response.json(); } catch { throw new ApiError('service_unavailable', 'The SQL service is unavailable. Please try again shortly.', response.status); }
  if (!response.ok) {
    const failure = data as { error?: { code: string; message: string }; detail?: string };
    throw new ApiError(failure.error?.code ?? 'request_failed', failure.error?.message ?? failure.detail ?? `Request failed (${response.status}). Please try again.`, response.status);
  }
  return data as T;
}
export async function request<T>(path: string, body?: unknown, signal?: AbortSignal): Promise<T> {
  return readResponse<T>(await fetchApi(path, body, signal));
}
export async function getHelperStatus(url = getHelperUrl()): Promise<HelperStatus> {
  const status = await readResponse<HelperStatus>(await fetchApi('/helper/status', undefined, undefined, url, true));
  if (status.mode !== 'helper' || status.protocol_version !== 1) {
    throw new ApiError('unsupported_helper', 'This website requires a QueryLab helper supporting protocol version 1. Update or restart your local helper, then check the connection again.');
  }
  return status;
}
export async function pairHelper(url: string, code: string): Promise<Session> {
  const origin = validateHelperUrl(url);
  const result = await readResponse<Session & { token: string }>(await fetchApi('/helper/pair', { pairing_code: code }, undefined, origin, true));
  try { sessionStorage.setItem(tokenKey, result.token); } catch { throw new ApiError('storage_unavailable', 'Allow session storage in this browser to pair the helper.'); }
  try { localStorage.setItem(urlKey, origin); } catch { /* The default URL still works without persistence. */ }
  activeHelperUrl = origin;
  return result;
}
let activeHelperUrl: string | undefined;
export async function downloadDataset(dataset: string): Promise<void> {
  const response = await fetchApi(`/datasets/${encodeURIComponent(dataset)}/setup.sql`);
  if (!response.ok) { await readResponse(response); return; }
  const url = URL.createObjectURL(await response.blob());
  const link = document.createElement('a'); link.href = url; link.download = `querylab-${dataset}-setup.sql`; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
