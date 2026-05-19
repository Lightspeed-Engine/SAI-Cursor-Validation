'use strict';

/**
 * Redact secrets from hook payloads before writing activity.jsonl.
 */

const BEARER_RE = /\bBearer\s+[A-Za-z0-9._~+/=-]+/gi;
const API_KEY_RE =
  /\b(sk-[A-Za-z0-9]{10,}|ghp_[A-Za-z0-9]{20,}|glpat-[A-Za-z0-9_-]{10,}|xox[baprs]-[A-Za-z0-9-]{10,})\b/g;
const ENV_SECRET_KEYS = new Set([
  'password',
  'secret',
  'token',
  'api_key',
  'apikey',
  'authorization',
  'auth',
  'private_key',
  'access_token',
  'refresh_token',
]);

function redactString(value) {
  if (typeof value !== 'string') return value;
  return value
    .replace(BEARER_RE, 'Bearer [REDACTED]')
    .replace(API_KEY_RE, '[REDACTED_TOKEN]');
}

function shouldRedactKey(key) {
  const lower = String(key).toLowerCase();
  if (ENV_SECRET_KEYS.has(lower)) return true;
  return (
    lower.includes('password') ||
    lower.includes('secret') ||
    lower.includes('token') ||
    lower.includes('authorization')
  );
}

function redactValue(key, value) {
  if (value == null) return value;
  if (typeof value === 'string') {
    if (shouldRedactKey(key)) return '[REDACTED]';
    return redactString(value);
  }
  if (Array.isArray(value)) return value.map((item, index) => redactValue(String(index), item));
  if (typeof value === 'object') return redactObject(value);
  return value;
}

function redactObject(obj) {
  if (obj == null || typeof obj !== 'object') return obj;
  if (Array.isArray(obj)) return obj.map((item, index) => redactValue(String(index), item));

  const out = {};
  for (const [key, value] of Object.entries(obj)) {
    if (key === 'env' && value && typeof value === 'object') {
      out[key] = '[REDACTED_ENV]';
      continue;
    }
    out[key] = redactValue(key, value);
  }
  return out;
}

function redact(input) {
  return redactObject(input);
}

module.exports = { redact, redactString, redactObject };
