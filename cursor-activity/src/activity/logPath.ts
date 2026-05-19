import * as path from 'path';
import * as vscode from 'vscode';

const DEFAULT_REL = path.join('.cursor', 'activity', 'activity.jsonl');

/** Resolve activity log path for a workspace folder. */
export function resolveActivityLogPath(
  folder: vscode.WorkspaceFolder
): string {
  const override = vscode.workspace
    .getConfiguration('cursorActivity')
    .get<string>('logPath', '')
    .trim();
  if (override) {
    return path.isAbsolute(override)
      ? override
      : path.join(folder.uri.fsPath, override);
  }
  return path.join(folder.uri.fsPath, DEFAULT_REL);
}

export function getPrimaryWorkspaceFolder():
  | vscode.WorkspaceFolder
  | undefined {
  const folders = vscode.workspace.workspaceFolders;
  if (!folders?.length) {
    return undefined;
  }
  return folders[0];
}
