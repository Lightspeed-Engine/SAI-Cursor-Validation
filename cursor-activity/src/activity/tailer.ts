import * as fs from 'fs';
import * as vscode from 'vscode';
import { ActivityStore } from './store';

/**
 * Tails a single activity.jsonl file (no workspace tree watchers).
 */
export class ActivityLogTailer implements vscode.Disposable {
  private offset = 0;
  private watcher: fs.FSWatcher | undefined;
  private pollTimer: NodeJS.Timeout | undefined;
  private partialLine = '';
  private disposed = false;

  constructor(
    private readonly logPath: string,
    private readonly store: ActivityStore
  ) {}

  start(): void {
    this.ensureLogFile();
    this.readFromStart();
    this.startWatching();
  }

  reload(): void {
    this.offset = 0;
    this.partialLine = '';
    this.store.clear();
    this.readFromStart();
  }

  /** Read any bytes appended since last offset (e.g. after extension sample commands). */
  sync(): void {
    this.readIncremental();
  }

  dispose(): void {
    this.disposed = true;
    this.watcher?.close();
    this.watcher = undefined;
    if (this.pollTimer) {
      clearInterval(this.pollTimer);
      this.pollTimer = undefined;
    }
  }

  private ensureLogFile(): void {
    const dir = require('path').dirname(this.logPath);
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }
    if (!fs.existsSync(this.logPath)) {
      fs.writeFileSync(this.logPath, '', 'utf8');
    }
  }

  private readFromStart(): void {
    if (!fs.existsSync(this.logPath)) {
      return;
    }
    const content = fs.readFileSync(this.logPath, 'utf8');
    this.offset = Buffer.byteLength(content, 'utf8');
    this.ingestText(content, false);
  }

  private startWatching(): void {
    try {
      this.watcher = fs.watch(this.logPath, () => {
        if (!this.disposed) {
          this.readIncremental();
        }
      });
    } catch {
      // fs.watch can fail on some FS; fall back to polling.
    }
    this.pollTimer = setInterval(() => {
      if (!this.disposed) {
        this.readIncremental();
      }
    }, 2000);
  }

  private readIncremental(): void {
    if (!fs.existsSync(this.logPath)) {
      return;
    }
    const stat = fs.statSync(this.logPath);
    if (stat.size < this.offset) {
      this.reload();
      return;
    }
    if (stat.size === this.offset) {
      return;
    }
    const fd = fs.openSync(this.logPath, 'r');
    try {
      const length = stat.size - this.offset;
      const buffer = Buffer.alloc(length);
      fs.readSync(fd, buffer, 0, length, this.offset);
      this.offset = stat.size;
      this.ingestText(buffer.toString('utf8'), true);
    } finally {
      fs.closeSync(fd);
    }
  }

  private ingestText(text: string, markReceived: boolean): void {
    const combined = this.partialLine + text;
    const lines = combined.split('\n');
    this.partialLine = lines.pop() ?? '';
    if (lines.length > 0) {
      this.store.ingestChunk(lines.join('\n'), markReceived);
    }
  }
}
