import * as vscode from 'vscode';
import { getPrimaryWorkspaceFolder, resolveActivityLogPath } from './activity/logPath';
import { appendGitSample } from './activity/sampleWriter';
import { ActivityStore } from './activity/store';
import { ActivityLogTailer } from './activity/tailer';
import { InstructionContextProvider } from './ui/contextPanel';
import { ActivityStatusBar } from './ui/statusBar';
import { TimelineWebviewProvider } from './ui/timelinePanel';

let store: ActivityStore;
let tailer: ActivityLogTailer | undefined;
let timelineProvider: TimelineWebviewProvider;
let contextProvider: InstructionContextProvider;
let statusBar: ActivityStatusBar;

export function activate(context: vscode.ExtensionContext): void {
  store = new ActivityStore();
  timelineProvider = new TimelineWebviewProvider(store);
  contextProvider = new InstructionContextProvider();

  const folder = getPrimaryWorkspaceFolder();
  const initialLog = folder
    ? resolveActivityLogPath(folder)
    : '(no workspace)';

  statusBar = new ActivityStatusBar(store, initialLog);

  context.subscriptions.push(
    statusBar,
    store.onDidChange(() => {
      statusBar.render();
      timelineProvider.render();
    }),
    vscode.window.registerWebviewViewProvider(
      'cursorActivity.timeline',
      timelineProvider
    ),
    vscode.window.registerTreeDataProvider(
      'cursorActivity.context',
      contextProvider
    )
  );

  if (folder) {
    startTailer(folder);
    contextProvider.refresh(folder.uri.fsPath);
  }

  context.subscriptions.push(
    vscode.workspace.onDidChangeWorkspaceFolders(() => {
      restartTailer();
    }),
    vscode.workspace.onDidChangeConfiguration((e) => {
      if (e.affectsConfiguration('cursorActivity')) {
        store.setMaxEvents(
          vscode.workspace
            .getConfiguration('cursorActivity')
            .get<number>('maxEvents', 5000)
        );
        restartTailer();
      }
    }),
    vscode.commands.registerCommand('cursorActivity.refresh', () => {
      tailer?.reload();
      const f = getPrimaryWorkspaceFolder();
      if (f) {
        contextProvider.refresh(f.uri.fsPath);
      }
      timelineProvider.render();
      void vscode.window.showInformationMessage(
        `Activity log reloaded (${store.eventCount} events).`
      );
    }),
    vscode.commands.registerCommand('cursorActivity.openLog', async () => {
      const f = getPrimaryWorkspaceFolder();
      if (!f) {
        return;
      }
      const uri = vscode.Uri.file(resolveActivityLogPath(f));
      const doc = await vscode.workspace.openTextDocument(uri);
      await vscode.window.showTextDocument(doc, { preview: false });
    }),
    vscode.commands.registerCommand('cursorActivity.sampleGitStatus', () =>
      runGitSample('status')
    ),
    vscode.commands.registerCommand('cursorActivity.sampleGitDiff', () =>
      runGitSample('diff')
    ),
    vscode.commands.registerCommand('cursorActivity.filterSession', async () => {
      const sessions = store.getSessionIds();
      if (!sessions.length) {
        void vscode.window.showWarningMessage('No sessions in activity log yet.');
        return;
      }
      const items = sessions.map((id) => ({
        label: id.length > 12 ? `${id.slice(0, 12)}…` : id,
        description: id,
        id,
      }));
      const pick = await vscode.window.showQuickPick(items, {
        placeHolder: 'Filter timeline by session',
        matchOnDescription: true,
      });
      if (pick) {
        timelineProvider.setFilters({ sessionId: pick.id });
        await vscode.commands.executeCommand(
          'workbench.view.extension.cursor-activity'
        );
      }
    }),
    vscode.commands.registerCommand('cursorActivity.clearFilters', () => {
      timelineProvider.clearFilters();
    })
  );
}

function startTailer(folder: vscode.WorkspaceFolder): void {
  tailer?.dispose();
  const logPath = resolveActivityLogPath(folder);
  statusBar.updateLogPath(logPath);
  tailer = new ActivityLogTailer(logPath, store);
  tailer.start();
}

function restartTailer(): void {
  const folder = getPrimaryWorkspaceFolder();
  if (!folder) {
    tailer?.dispose();
    tailer = undefined;
    return;
  }
  startTailer(folder);
  const f = folder;
  contextProvider.refresh(f.uri.fsPath);
}

async function runGitSample(kind: 'status' | 'diff'): Promise<void> {
  const folder = getPrimaryWorkspaceFolder();
  if (!folder) {
    void vscode.window.showErrorMessage('Open a workspace folder first.');
    return;
  }
  try {
    const event = await appendGitSample(folder, kind, store);
    tailer?.sync();
    void vscode.window.showInformationMessage(
      `Appended ${event.type} to activity log.`
    );
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    void vscode.window.showErrorMessage(`Git sample failed: ${msg}`);
  }
}

export function deactivate(): void {
  tailer?.dispose();
}
