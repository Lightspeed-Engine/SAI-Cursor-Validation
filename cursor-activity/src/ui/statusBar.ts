import * as vscode from 'vscode';
import { ActivityStore } from '../activity/store';
import { shortSessionId } from '../activity/types';

export class ActivityStatusBar implements vscode.Disposable {
  private readonly sessionItem: vscode.StatusBarItem;
  private readonly countItem: vscode.StatusBarItem;
  private readonly logItem: vscode.StatusBarItem;
  private readonly recordItem: vscode.StatusBarItem;
  private recordingOn = false;

  constructor(
    private readonly store: ActivityStore,
    private logPath: string
  ) {
    this.sessionItem = vscode.window.createStatusBarItem(
      vscode.StatusBarAlignment.Left,
      90
    );
    this.countItem = vscode.window.createStatusBarItem(
      vscode.StatusBarAlignment.Left,
      89
    );
    this.logItem = vscode.window.createStatusBarItem(
      vscode.StatusBarAlignment.Left,
      88
    );
    this.recordItem = vscode.window.createStatusBarItem(
      vscode.StatusBarAlignment.Left,
      91
    );

    this.sessionItem.command = 'cursorActivity.refresh';
    this.countItem.command = 'cursorActivity.refresh';
    this.logItem.command = 'cursorActivity.openLog';
    this.recordItem.command = 'cursorActivity.recordingStatus';

    this.render();
    this.sessionItem.show();
    this.countItem.show();
    this.logItem.show();
    this.recordItem.show();
  }

  setRecording(active: boolean): void {
    this.recordingOn = active;
    this.recordItem.command = active
      ? 'cursorActivity.stopRecording'
      : 'cursorActivity.startRecording';
    this.render();
  }

  updateLogPath(logPath: string): void {
    this.logPath = logPath;
    this.render();
  }

  render(): void {
    const session = this.store.currentSession;
    this.sessionItem.text = `$(pulse) ${shortSessionId(session ?? '')}`;
    this.sessionItem.tooltip = session
      ? `Activity session: ${session}`
      : 'No session.start yet in log';
    this.countItem.text = `$(history) ${this.store.eventCount}`;
    this.countItem.tooltip = 'Events in memory (ring buffer)';
    const shortLog =
      this.logPath.length > 48
        ? `…${this.logPath.slice(-44)}`
        : this.logPath;
    this.logItem.text = `$(file-text) ${shortLog}`;
    this.logItem.tooltip = this.logPath;
    this.recordItem.text = this.recordingOn
      ? '$(debug-stop) Rec ON'
      : '$(record) Rec OFF';
    this.recordItem.tooltip = this.recordingOn
      ? 'Stop recording (braid)'
      : 'Start recording (braid)';
    this.recordItem.backgroundColor = this.recordingOn
      ? new vscode.ThemeColor('statusBarItem.warningBackground')
      : undefined;
  }

  dispose(): void {
    this.sessionItem.dispose();
    this.countItem.dispose();
    this.logItem.dispose();
    this.recordItem.dispose();
  }
}
