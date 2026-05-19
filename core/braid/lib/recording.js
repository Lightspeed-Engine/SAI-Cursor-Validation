'use strict';

/** @typedef {'off' | 'meta' | 'headers' | 'body-preview' | 'debug'} Verbosity */

/**
 * @typedef {object} RecordingSession
 * @property {boolean} active
 * @property {string|null} startedAt
 * @property {string|null} stoppedAt
 * @property {string} sessionId
 * @property {string} agentKey
 * @property {Verbosity} verbosity
 * @property {string} logPath
 * @property {{ file: boolean, stream: boolean }} sinks
 */

function defaultSession() {
  return {
    active: false,
    startedAt: null,
    stoppedAt: null,
    sessionId: 'unknown',
    agentKey: 'unknown',
    verbosity: 'meta',
    logPath: '',
    sinks: { file: true, stream: false },
  };
}

class RecordingController {
  constructor() {
    /** @type {RecordingSession} */
    this.session = defaultSession();
    /** @type {{ sessionId: string, agentKey: string, model?: string }} */
    this.context = { sessionId: 'unknown', agentKey: 'unknown' };
  }

  status() {
    return {
      recording: this.session.active,
      session: { ...this.session },
      context: { ...this.context },
    };
  }

  /**
   * @param {object} opts
   */
  start(opts = {}) {
    if (this.session.active) {
      return this.status();
    }
    this.session = {
      active: true,
      startedAt: new Date().toISOString(),
      stoppedAt: null,
      sessionId: opts.sessionId || this.context.sessionId || 'unknown',
      agentKey: opts.agentKey || this.context.agentKey || 'unknown',
      verbosity: opts.verbosity || 'meta',
      logPath: opts.logPath || this.session.logPath,
      sinks: {
        file: opts.sinks?.file !== false,
        stream: opts.sinks?.stream === true,
      },
    };
    if (opts.sessionId) this.context.sessionId = opts.sessionId;
    if (opts.agentKey) this.context.agentKey = opts.agentKey;
    return this.status();
  }

  stop() {
    if (!this.session.active) {
      return this.status();
    }
    this.session.active = false;
    this.session.stoppedAt = new Date().toISOString();
    return this.status();
  }

  setContext(ctx) {
    if (ctx.sessionId) this.context.sessionId = ctx.sessionId;
    if (ctx.agentKey) this.context.agentKey = ctx.agentKey;
    if (ctx.model) this.context.model = ctx.model;
    if (this.session.active) {
      if (ctx.sessionId) this.session.sessionId = ctx.sessionId;
      if (ctx.agentKey) this.session.agentKey = ctx.agentKey;
    }
    return this.context;
  }

  isRecording() {
    return this.session.active;
  }

  shouldRetainEvent(event) {
    if (!this.session.active) return false;
    const v = this.session.verbosity;
    if (v === 'off') return false;
    if (event.type?.startsWith('http.') && v === 'meta') return true;
    return true;
  }

  streamEnabled() {
    return this.session.active && this.session.sinks.stream === true;
  }

  fileEnabled() {
    return this.session.active && this.session.sinks.file === true;
  }
}

module.exports = { RecordingController, defaultSession };
