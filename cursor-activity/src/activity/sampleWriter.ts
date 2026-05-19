import * as fs from 'fs';
import * as path from 'path';
import { execFile } from 'child_process';
import { promisify } from 'util';
import * as vscode from 'vscode';
import { ActivityEvent } from './types';
import { resolveActivityLogPath } from './logPath';

const execFileAsync = promisify(execFile);

function appendEvent(logPath: string, event: ActivityEvent): void {
  const dir = path.dirname(logPath);
  fs.mkdirSync(dir, { recursive: true });
  fs.appendFileSync(logPath, `${JSON.stringify(event)}\n`, 'utf8');
}

function sessionIdFromStore(store: { currentSession?: string }): string {
  return store.currentSession ?? 'extension-manual';
}

export async function appendGitSample(
  folder: vscode.WorkspaceFolder,
  kind: 'status' | 'diff',
  store: { currentSession?: string }
): Promise<ActivityEvent> {
  const logPath = resolveActivityLogPath(folder);
  const args =
    kind === 'status'
      ? ['status', '--porcelain=v1', '-b']
      : ['diff', '--stat'];
  const { stdout, stderr } = await execFileAsync('git', args, {
    cwd: folder.uri.fsPath,
    maxBuffer: 4 * 1024 * 1024,
    timeout: 60_000,
  });

  const event: ActivityEvent = {
    v: 1,
    ts: new Date().toISOString(),
    source: 'extension.sample',
    sessionId: sessionIdFromStore(store),
    agentKey: 'extension.manual',
    type: kind === 'status' ? 'sample.git_status' : 'sample.git_diff',
    payload: {
      cwd: folder.uri.fsPath,
      stdout: stdout.slice(0, 200_000),
      stderr: stderr?.slice(0, 4000) ?? '',
    },
  };

  appendEvent(logPath, event);
  return event;
}
