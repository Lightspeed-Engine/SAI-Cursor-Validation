import * as fs from 'fs';
import * as path from 'path';
import * as vscode from 'vscode';

export type ContextEntry =
  | { kind: 'file'; label: string; fsPath: string }
  | { kind: 'dir'; label: string; fsPath: string }
  | { kind: 'missing'; label: string };

const ROOT_FILES = [
  'CLAUDE.md',
  'AGENTS.md',
  'CONTRIBUTING.md',
  '.cursor/hooks.json',
];

const SCAN_DIRS = ['.cursor/rules', '.cursor/skills'];

export function discoverInstructionContext(
  root: string
): ContextEntry[] {
  const entries: ContextEntry[] = [];

  for (const rel of ROOT_FILES) {
    const fsPath = path.join(root, rel);
    entries.push(
      fs.existsSync(fsPath)
        ? { kind: 'file', label: rel, fsPath }
        : { kind: 'missing', label: `${rel} (not found)` }
    );
  }

  for (const rel of SCAN_DIRS) {
    const fsPath = path.join(root, rel);
    if (!fs.existsSync(fsPath)) {
      entries.push({ kind: 'missing', label: `${rel}/ (not found)` });
      continue;
    }
    entries.push({ kind: 'dir', label: rel, fsPath });
    try {
      const children = fs.readdirSync(fsPath, { withFileTypes: true });
      for (const child of children.slice(0, 40)) {
        const childPath = path.join(fsPath, child.name);
        const label = path.join(rel, child.name);
        if (child.isDirectory()) {
          entries.push({ kind: 'dir', label, fsPath: childPath });
        } else {
          entries.push({ kind: 'file', label, fsPath: childPath });
        }
      }
    } catch {
      /* ignore unreadable */
    }
  }

  return entries;
}

export class InstructionContextProvider
  implements vscode.TreeDataProvider<ContextEntry>
{
  private readonly _onDidChangeTreeData = new vscode.EventEmitter<void>();
  readonly onDidChangeTreeData = this._onDidChangeTreeData.event;

  private entries: ContextEntry[] = [];

  refresh(root: string): void {
    this.entries = discoverInstructionContext(root);
    this._onDidChangeTreeData.fire();
  }

  getTreeItem(element: ContextEntry): vscode.TreeItem {
    if (element.kind === 'missing') {
      const item = new vscode.TreeItem(element.label, vscode.TreeItemCollapsibleState.None);
      item.description = 'missing';
      return item;
    }
    const item = new vscode.TreeItem(
      element.label,
      element.kind === 'dir'
        ? vscode.TreeItemCollapsibleState.Collapsed
        : vscode.TreeItemCollapsibleState.None
    );
    item.resourceUri = vscode.Uri.file(element.fsPath);
    item.command = {
      command: 'vscode.open',
      title: 'Open',
      arguments: [vscode.Uri.file(element.fsPath)],
    };
    return item;
  }

  getChildren(element?: ContextEntry): ContextEntry[] {
    if (!element) {
      return this.entries;
    }
    if (element.kind !== 'dir') {
      return [];
    }
    try {
      return fs.readdirSync(element.fsPath, { withFileTypes: true }).map((d) => {
        const fsPath = path.join(element.fsPath, d.name);
        const label = path.join(element.label, d.name);
        return d.isDirectory()
          ? { kind: 'dir' as const, label, fsPath }
          : { kind: 'file' as const, label, fsPath };
      });
    } catch {
      return [];
    }
  }
}
