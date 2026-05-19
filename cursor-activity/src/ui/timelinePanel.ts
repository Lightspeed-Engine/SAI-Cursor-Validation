import * as vscode from 'vscode';
import { ActivityStore } from '../activity/store';
import { ActivityEvent, ActivityFilters } from '../activity/types';

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function summarizePayload(event: ActivityEvent): string {
  const p = event.payload;
  if (event.type === 'tool.result' || event.type === 'tool.failure') {
    return String(p.tool_name ?? 'tool');
  }
  if (event.type === 'shell.after' || event.type === 'shell.before') {
    const cmd = String(p.command ?? '').slice(0, 120);
    return cmd || 'shell';
  }
  if (event.type.startsWith('sample.')) {
    return event.type;
  }
  if (event.type === 'session.start') {
    return `model=${String(p.model ?? '?')} mode=${String(p.composer_mode ?? '?')}`;
  }
  return event.type;
}

function buildTimelineHtml(
  events: ActivityEvent[],
  filters: ActivityFilters,
  sessions: string[],
  types: string[],
  sources: string[]
): string {
  const rows = events
    .map((e) => {
      const detail = escapeHtml(JSON.stringify(e.payload).slice(0, 500));
      return `<tr class="row" data-type="${escapeHtml(e.type)}">
        <td class="ts">${escapeHtml(e.ts)}</td>
        <td class="type">${escapeHtml(e.type)}</td>
        <td class="src">${escapeHtml(e.source.replace('cursor.hook.', ''))}</td>
        <td class="sum">${escapeHtml(summarizePayload(e))}</td>
        <td class="sess" title="${escapeHtml(e.sessionId)}">${escapeHtml(e.sessionId.slice(0, 8))}</td>
      </tr>
      <tr class="detail"><td colspan="5"><pre>${detail}</pre></td></tr>`;
    })
    .join('');

  const sessionOpts = [
    `<option value="">All sessions</option>`,
    ...sessions.map(
      (s) =>
        `<option value="${escapeHtml(s)}"${filters.sessionId === s ? ' selected' : ''}>${escapeHtml(s.slice(0, 12))}…</option>`
    ),
  ].join('');

  const typeOpts = [
    `<option value="">All types</option>`,
    ...types.map(
      (t) =>
        `<option value="${escapeHtml(t)}"${filters.type === t ? ' selected' : ''}>${escapeHtml(t)}</option>`
    ),
  ].join('');

  const sourceOpts = [
    `<option value="">All sources</option>`,
    ...sources.map(
      (s) =>
        `<option value="${escapeHtml(s)}"${filters.source === s ? ' selected' : ''}>${escapeHtml(s)}</option>`
    ),
  ].join('');

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline';" />
  <style>
    body { font-family: var(--vscode-font-family); font-size: 12px; color: var(--vscode-foreground); background: var(--vscode-editor-background); margin: 0; padding: 8px; }
    .toolbar { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 8px; align-items: center; }
    select { background: var(--vscode-input-background); color: var(--vscode-input-foreground); border: 1px solid var(--vscode-input-border); padding: 2px 4px; }
    table { width: 100%; border-collapse: collapse; }
    th { text-align: left; border-bottom: 1px solid var(--vscode-panel-border); padding: 4px; position: sticky; top: 0; background: var(--vscode-editor-background); }
    td { padding: 3px 4px; border-bottom: 1px solid var(--vscode-widget-border); vertical-align: top; }
    tr.row { cursor: pointer; }
    tr.row:hover { background: var(--vscode-list-hoverBackground); }
    tr.detail { display: none; }
    tr.detail.open { display: table-row; }
    tr.detail pre { margin: 0; white-space: pre-wrap; word-break: break-word; font-size: 11px; opacity: 0.9; }
    .ts { white-space: nowrap; font-size: 11px; opacity: 0.85; }
    .type { font-weight: 600; }
    .empty { opacity: 0.7; padding: 16px; }
  </style>
</head>
<body>
  <div class="toolbar">
    <label>Session <select id="fSession">${sessionOpts}</select></label>
    <label>Type <select id="fType">${typeOpts}</select></label>
    <label>Source <select id="fSource">${sourceOpts}</select></label>
    <span id="count">${events.length} events</span>
  </div>
  ${
    events.length === 0
      ? '<p class="empty">No events match filters. Run an Agent session with hooks installed, or refresh.</p>'
      : `<table>
    <thead><tr><th>Time</th><th>Type</th><th>Source</th><th>Summary</th><th>Session</th></tr></thead>
    <tbody>${rows}</tbody>
  </table>`
  }
  <script>
    const vscode = acquireVsCodeApi();
    document.querySelectorAll('select').forEach((el) => {
      el.addEventListener('change', () => {
        vscode.postMessage({
          type: 'filter',
          sessionId: document.getElementById('fSession').value,
          filterType: document.getElementById('fType').value,
          source: document.getElementById('fSource').value,
        });
      });
    });
    document.querySelectorAll('tr.row').forEach((row) => {
      row.addEventListener('click', () => row.nextElementSibling?.classList.toggle('open'));
    });
  </script>
</body>
</html>`;
}

export class TimelineWebviewProvider implements vscode.WebviewViewProvider {
  private view?: vscode.WebviewView;
  private filters: ActivityFilters = {};

  constructor(private readonly store: ActivityStore) {}

  resolveWebviewView(
    webviewView: vscode.WebviewView,
    _context: vscode.WebviewViewResolveContext,
    _token: vscode.CancellationToken
  ): void {
    this.view = webviewView;
    webviewView.webview.options = { enableScripts: true };
    webviewView.webview.onDidReceiveMessage((msg) => {
      if (msg.type === 'filter') {
        this.filters = {
          sessionId: msg.sessionId || undefined,
          type: msg.filterType || undefined,
          source: msg.source || undefined,
        };
        this.render();
      }
    });
    this.render();
  }

  render(): void {
    if (!this.view) {
      return;
    }
    const events = this.store.timeline(this.filters, 400);
    const html = buildTimelineHtml(
      events,
      this.filters,
      this.store.getSessionIds(),
      this.store.getTypes(),
      this.store.getSources()
    );
    this.view.webview.html = html;
  }
}
