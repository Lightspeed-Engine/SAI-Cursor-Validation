'use strict';

const http = require('http');
const { URL } = require('url');
const { isBraidEvent, normalizeEvent } = require('./schema');

/**
 * @param {import('./recording').RecordingController} recording
 * @param {import('./store').BraidStore} store
 */
function createBraidServer(recording, store) {
  /** @type {import('http').ServerResponse[]} */
  const sseClients = [];

  function broadcastSse(event) {
    const data = `data: ${JSON.stringify(event)}\n\n`;
    for (const res of sseClients) {
      res.write(data);
    }
  }

  store.onStream((event) => broadcastSse(event));

  function json(res, status, body) {
    res.writeHead(status, {
      'content-type': 'application/json',
      'access-control-allow-origin': '*',
    });
    res.end(JSON.stringify(body));
  }

  async function readBody(req) {
    const chunks = [];
    for await (const chunk of req) {
      chunks.push(chunk);
    }
    const text = Buffer.concat(chunks).toString('utf8').trim();
    if (!text) return null;
    return JSON.parse(text);
  }

  const server = http.createServer(async (req, res) => {
    const url = new URL(req.url || '/', `http://${req.headers.host || 'localhost'}`);
    const pathname = url.pathname;

    if (req.method === 'OPTIONS') {
      res.writeHead(204, {
        'access-control-allow-origin': '*',
        'access-control-allow-methods': 'GET,POST,PUT,OPTIONS',
        'access-control-allow-headers': 'content-type',
      });
      res.end();
      return;
    }

    try {
      if (pathname === '/health' && req.method === 'GET') {
        return json(res, 200, { ok: true, service: 'braid', recording: recording.isRecording() });
      }

      if (pathname === '/v1/recording/status' && req.method === 'GET') {
        return json(res, 200, recording.status());
      }

      if (pathname === '/v1/recording/start' && req.method === 'POST') {
        const body = (await readBody(req)) || {};
        if (body.logPath) store.setLogPath(body.logPath);
        const status = recording.start(body);
        return json(res, 200, status);
      }

      if (pathname === '/v1/recording/stop' && req.method === 'POST') {
        return json(res, 200, recording.stop());
      }

      if (pathname === '/v1/context' && req.method === 'PUT') {
        const body = (await readBody(req)) || {};
        return json(res, 200, { context: recording.setContext(body) });
      }

      if (pathname === '/v1/log/path' && req.method === 'GET') {
        return json(res, 200, { logPath: recording.session.logPath || null });
      }

      if (pathname === '/v1/ingest' && req.method === 'POST') {
        const body = (await readBody(req)) || {};
        const events = body.events || (body.event ? [body.event] : []);
        const results = [];
        for (const raw of events) {
          if (!raw || typeof raw !== 'object') continue;
          const candidate = normalizeEvent(raw, recording.context);
          if (!isBraidEvent(candidate)) {
            results.push({ retained: false, reason: 'invalid_schema' });
            continue;
          }
          results.push(store.ingest(candidate));
        }
        if (!recording.isRecording()) {
          res.writeHead(204, {
            'content-type': 'application/json',
            'access-control-allow-origin': '*',
          });
          res.end(JSON.stringify({ retained: false, results }));
          return;
        }
        return json(res, 200, { retained: true, results });
      }

      if (pathname === '/v1/events' && req.method === 'GET') {
        return json(res, 200, {
          events: store.query({
            sessionId: url.searchParams.get('sessionId') || undefined,
            source: url.searchParams.get('source') || undefined,
            type: url.searchParams.get('type') || undefined,
            limit: url.searchParams.get('limit') || undefined,
          }),
        });
      }

      if (pathname === '/v1/events/stream' && req.method === 'GET') {
        res.writeHead(200, {
          'content-type': 'text/event-stream',
          'cache-control': 'no-cache',
          connection: 'keep-alive',
          'access-control-allow-origin': '*',
        });
        res.write(': connected\n\n');
        sseClients.push(res);
        req.on('close', () => {
          const i = sseClients.indexOf(res);
          if (i >= 0) sseClients.splice(i, 1);
        });
        return;
      }

      json(res, 404, { error: 'not_found' });
    } catch (err) {
      json(res, 500, { error: err instanceof Error ? err.message : String(err) });
    }
  });

  return server;
}

module.exports = { createBraidServer };
