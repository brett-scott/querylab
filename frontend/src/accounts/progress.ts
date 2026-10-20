import type { Challenge, ExecutionResult } from '../api';

export interface Attempt {
  id: string;
  user_id: string;
  challenge_id: string;
  challenge_version: string;
  challenge_title: string;
  challenge_type: Challenge['type'];
  dataset: string;
  passed: boolean;
  hints_used: number;
  solution_viewed: boolean;
  completed_at: string;
}

export interface ChallengeProgress {
  user_id: string;
  challenge_id: string;
  challenge_version: string;
  challenge_title: string;
  challenge_type: Challenge['type'];
  attempt_count: number;
  passed_count: number;
  unassisted_pass_count: number;
  last_attempt_at: string;
}

export interface SubmissionSnapshot {
  id: string;
  userId: string;
  challenge: Pick<Challenge, 'id' | 'version' | 'title' | 'type' | 'dataset'>;
  hintsUsed: number;
  solutionViewed: boolean;
}

const activeKey = (userId: string) => `querylab:progress:active:${userId}`;
export function saveActiveSubmission(jobId: string, target: string, snapshot: SubmissionSnapshot) {
  try { sessionStorage.setItem(activeKey(snapshot.userId), JSON.stringify({ jobId, target, snapshot })); } catch { /* Current-tab grading still works. */ }
}
export function clearActiveSubmission(userId: string) {
  try { sessionStorage.removeItem(activeKey(userId)); } catch { /* No persisted job to clear. */ }
}
export function readActiveSubmission(userId: string, target: string, challenge: Pick<Challenge, 'id' | 'version'>): { jobId: string; snapshot: SubmissionSnapshot } | null {
  try {
    const value = JSON.parse(sessionStorage.getItem(activeKey(userId)) ?? 'null');
    const snapshot = value?.snapshot;
    if (value?.target !== target || typeof value?.jobId !== 'string' || value.jobId.length > 128 ||
      snapshot?.userId !== userId || typeof snapshot?.id !== 'string' ||
      snapshot?.challenge?.id !== challenge.id || snapshot?.challenge?.version !== challenge.version ||
      !Number.isInteger(snapshot?.hintsUsed) || snapshot.hintsUsed < 0 || snapshot.hintsUsed > 3 || typeof snapshot?.solutionViewed !== 'boolean') return null;
    return { jobId: value.jobId, snapshot };
  } catch { return null; }
}

export function completedAttempt(snapshot: SubmissionSnapshot, result: ExecutionResult, completedAt = new Date().toISOString()): Attempt | null {
  if (result.mode !== 'submit' || !result.grading) return null;
  return {
    id: snapshot.id, user_id: snapshot.userId,
    challenge_id: snapshot.challenge.id, challenge_version: snapshot.challenge.version,
    challenge_title: snapshot.challenge.title, challenge_type: snapshot.challenge.type, dataset: snapshot.challenge.dataset,
    passed: result.grading.passed, hints_used: snapshot.hintsUsed,
    solution_viewed: snapshot.solutionViewed, completed_at: completedAt,
  };
}

export function progressSummary(progress: ChallengeProgress[]) {
  const attempts = progress.reduce((count, item) => count + Number(item.attempt_count), 0);
  const passes = progress.reduce((count, item) => count + Number(item.passed_count), 0);
  return {
    completed: new Set(progress.filter(item => Number(item.passed_count) > 0).map(item => item.challenge_id)).size,
    attempts, passes, passRate: attempts ? Math.round(passes / attempts * 100) : null,
    unassisted: new Set(progress.filter(item => Number(item.unassisted_pass_count) > 0).map(item => item.challenge_id)).size,
  };
}

export const pendingKey = (userId: string) => `querylab:progress:pending:${userId}`;

export function readAssistance(storageKey: string): { hintsUsed: number; solutionViewed: boolean } {
  try {
    const value = JSON.parse(localStorage.getItem(`${storageKey}:assistance`) ?? '{}');
    return { hintsUsed: Number.isInteger(value.hintsUsed) ? Math.min(3, Math.max(0, value.hintsUsed)) : 0, solutionViewed: value.solutionViewed === true };
  } catch { return { hintsUsed: 0, solutionViewed: false }; }
}
export function rememberAssistance(storageKey: string, hintsUsed: number, solutionViewed: boolean) {
  const previous = readAssistance(storageKey);
  const next = { hintsUsed: Math.max(previous.hintsUsed, hintsUsed), solutionViewed: previous.solutionViewed || solutionViewed };
  try { localStorage.setItem(`${storageKey}:assistance`, JSON.stringify(next)); } catch { /* In-memory tracking still applies to the current challenge. */ }
}

// Only these fields can leave the computer. In particular, never serialize a
// job, SQL script, result rows, helper bearer token or database credentials.
export function readPending(value: string | null, userId: string): Attempt[] {
  try {
    const parsed: unknown = JSON.parse(value ?? '[]');
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((item): item is Attempt => Boolean(item && typeof item === 'object' &&
      item.user_id === userId && typeof item.id === 'string' &&
      typeof item.challenge_id === 'string' && typeof item.challenge_version === 'string' &&
      typeof item.challenge_title === 'string' && ['query', 'function', 'procedure'].includes(item.challenge_type) &&
      ['online-store', 'inventory'].includes(item.dataset) && typeof item.passed === 'boolean' &&
      Number.isInteger(item.hints_used) && item.hints_used >= 0 && item.hints_used <= 3 &&
      typeof item.solution_viewed === 'boolean' && typeof item.completed_at === 'string' &&
      Number.isFinite(Date.parse(item.completed_at)))).map(item => ({
        id: item.id, user_id: item.user_id, challenge_id: item.challenge_id,
        challenge_version: item.challenge_version, challenge_title: item.challenge_title,
        challenge_type: item.challenge_type, dataset: item.dataset, passed: item.passed,
        hints_used: item.hints_used, solution_viewed: item.solution_viewed, completed_at: item.completed_at,
      }));
  } catch { return []; }
}
