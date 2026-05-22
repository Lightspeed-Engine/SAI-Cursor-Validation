/**
 * Shufti Socket.IO client — codebase topology feed (areas:list, discover:areas).
 * Adapted from ai-spy/src/services/shuftiClient.ts (Vite env → explicit config).
 *
 * Upstream server: LSE-Core-2.0-2.1/scripts/shufti_ui_server.py (default :3005)
 */

import { io, type Socket } from 'socket.io-client';
import type { ShuftiAreaInfo, ShuftiDiscoveredArea } from './types';

export interface ShuftiClientConfig {
  /** e.g. http://127.0.0.1:3005 */
  url?: string;
  socketPath?: string;
  /** Called for connect/disconnect/errors; defaults to console. */
  log?: (level: 'info' | 'warn' | 'error', message: string, meta?: Record<string, unknown>) => void;
}

type Listener<T> = (payload: T) => void;

const DEFAULT_URL = 'http://127.0.0.1:3005';
const DEFAULT_PATH = '/socket.io';

function defaultLog(level: 'info' | 'warn' | 'error', message: string, meta?: Record<string, unknown>) {
  const line = meta ? `${message} ${JSON.stringify(meta)}` : message;
  if (level === 'error') {
    console.error('[shufti]', line);
  } else if (level === 'warn') {
    console.warn('[shufti]', line);
  } else {
    console.info('[shufti]', line);
  }
}

export function resolveShuftiUrl(config?: ShuftiClientConfig): string {
  return config?.url ?? process.env.SHUFTI_URL ?? process.env.VITE_SHUFTI_URL ?? DEFAULT_URL;
}

export class ShuftiTopologyClient {
  private socket: Socket | null = null;
  private readonly url: string;
  private readonly path: string;
  private readonly log: NonNullable<ShuftiClientConfig['log']>;

  constructor(config: ShuftiClientConfig = {}) {
    this.url = resolveShuftiUrl(config);
    this.path = config.socketPath ?? process.env.SHUFTI_SOCKET_PATH ?? DEFAULT_PATH;
    this.log = config.log ?? defaultLog;
  }

  getUrl(): string {
    return this.url;
  }

  private safeListener<T>(eventName: string, listener: Listener<T>) {
    return (payload: T) => {
      try {
        listener(payload);
      } catch (error) {
        this.log('error', 'SHUFTI listener failure', {
          eventName,
          error: error instanceof Error ? error.message : String(error),
        });
      }
    };
  }

  connect(): Socket {
    if (this.socket) {
      return this.socket;
    }

    this.socket = io(this.url, {
      path: this.path,
      transports: ['polling'],
      upgrade: false,
      reconnection: true,
      reconnectionDelay: 2000,
      reconnectionDelayMax: 15000,
      randomizationFactor: 0.5,
      timeout: 5000,
      autoConnect: true,
    });

    this.log('info', 'SHUFTI client connecting', { url: this.url, path: this.path });
    return this.socket;
  }

  disconnect(): void {
    this.socket?.disconnect();
    this.socket = null;
  }

  onConnect(listener: () => void): () => void {
    const handler = () => {
      this.log('info', 'SHUFTI connected', { url: this.url });
      listener();
    };
    this.connect().on('connect', handler);
    return () => this.socket?.off('connect', handler);
  }

  onDisconnect(listener: () => void): () => void {
    const handler = () => listener();
    this.connect().on('disconnect', handler);
    return () => this.socket?.off('disconnect', handler);
  }

  onConnectError(listener: (error: Error) => void): () => void {
    const handler = (error: Error) => {
      this.log('error', 'SHUFTI connect_error', {
        url: this.url,
        error: error.message,
      });
      listener(error);
    };
    this.connect().on('connect_error', handler);
    return () => this.socket?.off('connect_error', handler);
  }

  onAvailableAreas(listener: Listener<ShuftiAreaInfo[]>): () => void {
    const handler = this.safeListener(
      'areas:list:response',
      (payload: { ok?: boolean; areas?: ShuftiAreaInfo[] }) => {
        if (payload.ok === false) {
          listener([]);
          return;
        }
        listener(payload.areas ?? []);
      },
    );
    this.connect().on('areas:list:response', handler);
    return () => this.socket?.off('areas:list:response', handler);
  }

  onDiscoveredAreas(listener: Listener<ShuftiDiscoveredArea[]>): () => void {
    const handler = this.safeListener(
      'discover:areas:response',
      (payload: { ok?: boolean; proposed_areas?: ShuftiDiscoveredArea[] }) => {
        if (payload.ok === false) {
          listener([]);
          return;
        }
        listener(payload.proposed_areas ?? []);
      },
    );
    this.connect().on('discover:areas:response', handler);
    return () => this.socket?.off('discover:areas:response', handler);
  }

  /** Request static budgets + discovered repo areas (async discover may queue). */
  requestTopology(root = ''): void {
    this.log('info', 'SHUFTI requestTopology', { root: root || null });
    this.connect().emit('areas:list', {});
    this.connect().emit('discover:areas', { root });
  }
}
