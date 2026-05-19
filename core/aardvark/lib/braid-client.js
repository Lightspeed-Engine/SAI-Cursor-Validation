'use strict';

const DEFAULT_BRAID = 'http://127.0.0.1:4711';

function braidUrl() {
  return process.env.BRAID_URL || DEFAULT_BRAID;
}

async function braidFetch(path, opts = {}) {
  const url = `${braidUrl()}${path}`;
  const res = await fetch(url, {
    ...opts,
    headers: { 'content-type': 'application/json', ...(opts.headers || {}) },
    signal: AbortSignal.timeout(Number(process.env.BRAID_TIMEOUT_MS || 800)),
  });
  return res;
}

async function isRecording() {
  try {
    const res = await braidFetch('/v1/recording/status');
    if (!res.ok) return false;
    const data = await res.json();
    return Boolean(data.recording);
  } catch {
    return false;
  }
}

async function ingestObservation(event) {
  try {
    const res = await braidFetch('/v1/ingest', {
      method: 'POST',
      body: JSON.stringify({ event }),
    });
    return res.ok || res.status === 204;
  } catch {
    return false;
  }
}

module.exports = { braidUrl, isRecording, ingestObservation };
