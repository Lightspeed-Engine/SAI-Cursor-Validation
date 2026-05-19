/** Normalized activity log event (schema v0). */
export interface ActivityEvent {
  v: number;
  ts: string;
  source: string;
  sessionId: string;
  agentKey: string;
  type: string;
  payload: Record<string, unknown>;
  receivedAt?: string;
}

export interface ActivityFilters {
  sessionId?: string;
  type?: string;
  source?: string;
}

export function isActivityEvent(value: unknown): value is ActivityEvent {
  if (!value || typeof value !== 'object') {
    return false;
  }
  const e = value as Record<string, unknown>;
  return (
    e.v === 1 &&
    typeof e.ts === 'string' &&
    typeof e.source === 'string' &&
    typeof e.sessionId === 'string' &&
    typeof e.agentKey === 'string' &&
    typeof e.type === 'string' &&
    typeof e.payload === 'object' &&
    e.payload !== null
  );
}

export function parseActivityLine(line: string): ActivityEvent | null {
  const trimmed = line.trim();
  if (!trimmed) {
    return null;
  }
  try {
    const parsed: unknown = JSON.parse(trimmed);
    if (!isActivityEvent(parsed)) {
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
}

export function shortSessionId(sessionId: string): string {
  if (!sessionId || sessionId === 'unknown') {
    return '—';
  }
  return sessionId.length > 8 ? `${sessionId.slice(0, 8)}…` : sessionId;
}
