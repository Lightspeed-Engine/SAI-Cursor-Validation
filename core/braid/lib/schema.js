'use strict';

const SCHEMA_VERSION = 1;

function isBraidEvent(value) {
  if (!value || typeof value !== 'object') return false;
  const e = value;
  return (
    e.v === SCHEMA_VERSION &&
    typeof e.ts === 'string' &&
    typeof e.source === 'string' &&
    typeof e.sessionId === 'string' &&
    typeof e.agentKey === 'string' &&
    typeof e.type === 'string' &&
    typeof e.payload === 'object' &&
    e.payload !== null
  );
}

function normalizeEvent(raw, context = {}) {
  const event = { ...raw };
  event.v = SCHEMA_VERSION;
  if (!event.ts) event.ts = new Date().toISOString();
  if (!event.sessionId) event.sessionId = context.sessionId || 'unknown';
  if (!event.agentKey) event.agentKey = context.agentKey || 'unknown';
  if (!event.payload || typeof event.payload !== 'object') event.payload = {};
  return event;
}

module.exports = { SCHEMA_VERSION, isBraidEvent, normalizeEvent };
