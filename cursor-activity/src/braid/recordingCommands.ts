import * as vscode from 'vscode';
import {
  getPrimaryWorkspaceFolder,
  resolveActivityLogPath,
} from '../activity/logPath';
import {
  allocateProxyPort,
  checkBraidHealth,
  getRecordingStatus,
  startRecording,
  stopRecording,
  Verbosity,
  braidUrls,
} from './client';

export function registerRecordingCommands(
  context: vscode.ExtensionContext,
  onStatusChange: () => void
): void {
  context.subscriptions.push(
    vscode.commands.registerCommand('cursorActivity.startRecording', () =>
      runStartRecording(onStatusChange)
    ),
    vscode.commands.registerCommand('cursorActivity.stopRecording', () =>
      runStopRecording(onStatusChange)
    ),
    vscode.commands.registerCommand('cursorActivity.recordingStatus', async () => {
      await showRecordingStatus();
    })
  );
}

async function runStartRecording(onStatusChange: () => void): Promise<void> {
  const folder = getPrimaryWorkspaceFolder();
  if (!folder) {
    void vscode.window.showErrorMessage('Open a workspace folder first.');
    return;
  }

  const up = await checkBraidHealth();
  if (!up) {
    const urls = braidUrls();
    const pick = await vscode.window.showWarningMessage(
      'Braid daemon is not running. Start it with: bash cursor/scripts/start-core-daemons.sh',
      'Copy start command',
      'Start anyway (will fail)'
    );
    if (pick === 'Copy start command') {
      await vscode.env.clipboard.writeText('bash cursor/scripts/start-core-daemons.sh');
      return;
    }
    if (pick !== 'Start anyway (will fail)') {
      return;
    }
  }

  const verbosity = await vscode.window.showQuickPick(
    [
      { label: 'meta', description: 'Host, path, status, timing (default)' },
      { label: 'headers', description: 'meta + allowlisted headers' },
      { label: 'body-preview', description: 'meta + truncated redacted body' },
      { label: 'debug', description: 'Most detail (dev only)' },
    ],
    { placeHolder: 'Recording verbosity' }
  );
  if (!verbosity) {
    return;
  }

  const allocateProxy = await vscode.window.showQuickPick(
    ['No', 'Yes'],
    { placeHolder: 'Allocate Aardvark proxy port for this session?' }
  );

  const logPath = resolveActivityLogPath(folder);
  const sessionId =
    vscode.env.machineId.slice(0, 12) + '-' + Date.now().toString(36);

  try {
    const status = await startRecording({
      logPath,
      sessionId,
      agentKey: 'cursor.agent',
      verbosity: verbosity.label as Verbosity,
    });

    if (allocateProxy === 'Yes') {
      try {
        const port = await allocateProxyPort('cursor.agent', sessionId);
        void vscode.window.showInformationMessage(
          `Recording on. Proxy: 127.0.0.1:${port.port} (route HTTP_PROXY if needed).`
        );
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        void vscode.window.showWarningMessage(
          `Recording on; proxy allocation failed: ${msg}`
        );
      }
    } else {
      void vscode.window.showInformationMessage(
        `Recording started → ${logPath}`
      );
    }

    onStatusChange();
    if (!status.recording) {
      void vscode.window.showWarningMessage('Braid did not confirm recording active.');
    }
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    void vscode.window.showErrorMessage(`Start recording failed: ${msg}`);
  }
}

async function runStopRecording(onStatusChange: () => void): Promise<void> {
  try {
    await stopRecording();
    onStatusChange();
    void vscode.window.showInformationMessage('Recording stopped (nothing retained until next start).');
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    void vscode.window.showErrorMessage(`Stop recording failed: ${msg}`);
  }
}

async function showRecordingStatus(): Promise<void> {
  try {
    const status = await getRecordingStatus();
    void vscode.window.showInformationMessage(
      status.recording
        ? `Recording: ON (${status.session.verbosity}) → ${status.session.logPath || 'log'}`
        : 'Recording: OFF (default — no data retained)'
    );
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    void vscode.window.showErrorMessage(`Braid unreachable: ${msg}`);
  }
}
