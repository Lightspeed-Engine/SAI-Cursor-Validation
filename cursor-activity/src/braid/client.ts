import * as vscode from 'vscode';

export type Verbosity = 'meta' | 'headers' | 'body-preview' | 'debug';

export interface RecordingStatus {
  recording: boolean;
  session: {
    active: boolean;
    verbosity?: string;
    sessionId?: string;
    agentKey?: string;
    logPath?: string;
  };
}

function braidBaseUrl(): string {
  return (
    vscode.workspace.getConfiguration('cursorActivity').get<string>('braidUrl') ||
    'http://127.0.0.1:4711'
  );
}

function aardvarkBaseUrl(): string {
  return (
    vscode.workspace
      .getConfiguration('cursorActivity')
      .get<string>('aardvarkUrl') || 'http://127.0.0.1:4712'
  );
}

async function request<T>(
  base: string,
  path: string,
  init?: RequestInit
): Promise<T> {
  const res = await fetch(`${base}${path}`, {
    ...init,
    headers: {
      'content-type': 'application/json',
      ...(init?.headers as Record<string, string>),
    },
  });
  if (res.status === 204) {
    return {} as T;
  }
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${path} → ${res.status}: ${text}`);
  }
  return (await res.json()) as T;
}

export async function getRecordingStatus(): Promise<RecordingStatus> {
  return request<RecordingStatus>(braidBaseUrl(), '/v1/recording/status');
}

export async function startRecording(opts: {
  logPath: string;
  sessionId?: string;
  agentKey?: string;
  verbosity?: Verbosity;
  streamSink?: boolean;
}): Promise<RecordingStatus> {
  return request<RecordingStatus>(braidBaseUrl(), '/v1/recording/start', {
    method: 'POST',
    body: JSON.stringify({
      logPath: opts.logPath,
      sessionId: opts.sessionId,
      agentKey: opts.agentKey || 'cursor.agent',
      verbosity: opts.verbosity || 'meta',
      sinks: { file: true, stream: opts.streamSink === true },
    }),
  });
}

export async function stopRecording(): Promise<RecordingStatus> {
  return request<RecordingStatus>(braidBaseUrl(), '/v1/recording/stop', {
    method: 'POST',
    body: '{}',
  });
}

export async function allocateProxyPort(
  agentKey: string,
  sessionId: string
): Promise<{ port: number; agentKey: string }> {
  return request<{ port: number; agentKey: string }>(
    aardvarkBaseUrl(),
    '/v1/ports',
    {
      method: 'POST',
      body: JSON.stringify({ agentKey, sessionId }),
    }
  );
}

export async function checkBraidHealth(): Promise<boolean> {
  try {
    const data = await request<{ ok: boolean }>(braidBaseUrl(), '/health');
    return Boolean(data.ok);
  } catch {
    return false;
  }
}

export function braidUrls() {
  return { braid: braidBaseUrl(), aardvark: aardvarkBaseUrl() };
}
