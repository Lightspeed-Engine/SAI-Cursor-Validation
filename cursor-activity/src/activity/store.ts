import * as vscode from 'vscode';
import {
  ActivityEvent,
  ActivityFilters,
  parseActivityLine,
} from './types';

export class ActivityStore {
  private readonly events: ActivityEvent[] = [];
  private maxEvents: number;
  private currentSessionId: string | undefined;

  private readonly _onDidChange = new vscode.EventEmitter<void>();
  readonly onDidChange = this._onDidChange.event;

  constructor() {
    this.maxEvents = vscode.workspace
      .getConfiguration('cursorActivity')
      .get<number>('maxEvents', 5000);
  }

  get eventCount(): number {
    return this.events.length;
  }

  get currentSession(): string | undefined {
    return this.currentSessionId;
  }

  setMaxEvents(max: number): void {
    this.maxEvents = Math.max(100, max);
    this.trim();
  }

  clear(): void {
    this.events.length = 0;
    this.currentSessionId = undefined;
    this._onDidChange.fire();
  }

  /** Ingest raw file bytes (full or incremental). */
  ingestChunk(text: string, markReceived = false): number {
    let added = 0;
    const lines = text.split('\n');
    for (const line of lines) {
      const event = parseActivityLine(line);
      if (!event) {
        continue;
      }
      if (markReceived) {
        event.receivedAt = new Date().toISOString();
      }
      this.push(event);
      added++;
    }
    if (added > 0) {
      this._onDidChange.fire();
    }
    return added;
  }

  private push(event: ActivityEvent): void {
    this.events.push(event);
    if (event.type === 'session.start') {
      this.currentSessionId = event.sessionId;
    }
    this.trim();
  }

  private trim(): void {
    while (this.events.length > this.maxEvents) {
      this.events.shift();
    }
  }

  getAll(): readonly ActivityEvent[] {
    return this.events;
  }

  getSessionIds(): string[] {
    const ids = new Set<string>();
    for (const e of this.events) {
      if (e.sessionId && e.sessionId !== 'unknown') {
        ids.add(e.sessionId);
      }
    }
    return [...ids].sort((a, b) => {
      const aLast = this.lastTsForSession(a);
      const bLast = this.lastTsForSession(b);
      return bLast.localeCompare(aLast);
    });
  }

  private lastTsForSession(sessionId: string): string {
    for (let i = this.events.length - 1; i >= 0; i--) {
      if (this.events[i].sessionId === sessionId) {
        return this.events[i].ts;
      }
    }
    return '';
  }

  getTypes(): string[] {
    return [...new Set(this.events.map((e) => e.type))].sort();
  }

  getSources(): string[] {
    return [...new Set(this.events.map((e) => e.source))].sort();
  }

  query(filters: ActivityFilters = {}): ActivityEvent[] {
    return this.events.filter((e) => {
      if (filters.sessionId && e.sessionId !== filters.sessionId) {
        return false;
      }
      if (filters.type && e.type !== filters.type) {
        return false;
      }
      if (filters.source && e.source !== filters.source) {
        return false;
      }
      return true;
    });
  }

  /** Newest-first timeline slice. */
  timeline(filters: ActivityFilters = {}, limit = 500): ActivityEvent[] {
    const matched = this.query(filters);
    return matched.slice(-limit).reverse();
  }
}
