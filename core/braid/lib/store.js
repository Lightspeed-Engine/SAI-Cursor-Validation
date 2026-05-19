'use strict';

const fs = require('fs');
const path = require('path');
const { normalizeEvent } = require('./schema');

class BraidStore {
  /**
   * @param {import('./recording').RecordingController} recording
   */
  constructor(recording) {
    this.recording = recording;
    /** @type {import('./schema').BraidEvent[]} */
    this.buffer = [];
    this.maxBuffer = 5000;
    /** @type {Set<(event: object) => void>} */
    this.streamListeners = new Set();
  }

  setLogPath(logPath) {
    this.recording.session.logPath = logPath;
  }

  /**
   * @param {object} raw
   * @returns {{ retained: boolean, event?: object, reason?: string }}
   */
  ingest(raw) {
    if (!this.recording.isRecording()) {
      return { retained: false, reason: 'not_recording' };
    }
    const event = normalizeEvent(raw, this.recording.context);
    if (!this.recording.shouldRetainEvent(event)) {
      return { retained: false, reason: 'verbosity' };
    }

    event.braid = {
      seq: this.buffer.length + 1,
      ingestedAt: new Date().toISOString(),
    };

    this.buffer.push(event);
    while (this.buffer.length > this.maxBuffer) {
      this.buffer.shift();
    }

    if (this.recording.fileEnabled() && this.recording.session.logPath) {
      this.appendFile(event);
    }

    if (this.recording.streamEnabled()) {
      for (const fn of this.streamListeners) {
        try {
          fn(event);
        } catch {
          /* ignore listener errors */
        }
      }
    }

    return { retained: true, event };
  }

  appendFile(event) {
    const file = this.recording.session.logPath;
    const dir = path.dirname(file);
    fs.mkdirSync(dir, { recursive: true });
    fs.appendFileSync(file, `${JSON.stringify(event)}\n`, 'utf8');
  }

  onStream(listener) {
    this.streamListeners.add(listener);
    return () => this.streamListeners.delete(listener);
  }

  query(opts = {}) {
    let list = [...this.buffer];
    if (opts.sessionId) {
      list = list.filter((e) => e.sessionId === opts.sessionId);
    }
    if (opts.source) {
      list = list.filter((e) => e.source.startsWith(opts.source));
    }
    if (opts.type) {
      list = list.filter((e) => e.type === opts.type);
    }
    const limit = Math.min(Number(opts.limit) || 200, 1000);
    return list.slice(-limit);
  }
}

module.exports = { BraidStore };
