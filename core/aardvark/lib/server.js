'use strict';

const http = require('http');
const { URL } = require('url');
const { handleProxyRequest } = require('./proxy');

/**
 * @param {import('./registry').PortRegistry} registry
 */
function createControlServer(registry) {
  const verbosity =
    /** @type {'meta' | 'headers' | 'body-preview' | 'debug'} */ (
      process.env.AARDVARK_VERBOSITY || 'meta'
    );

  async function readBody(req) {
    const chunks = [];
    for await (const chunk of req) {
      chunks.push(chunk);
    }
    const text = Buffer.concat(chunks).toString('utf8').trim();
    if (!text) return {};
    return JSON.parse(text);
  }

  function json(res, status, body) {
    res.writeHead(status, {
      'content-type': 'application/json',
      'access-control-allow-origin': '*',
    });
    res.end(JSON.stringify(body));
  }

  return http.createServer(async (req, res) => {
    const url = new URL(req.url || '/', `http://${req.headers.host || 'localhost'}`);

    if (req.method === 'OPTIONS') {
      res.writeHead(204, {
        'access-control-allow-origin': '*',
        'access-control-allow-methods': 'GET,POST,DELETE,OPTIONS',
        'access-control-allow-headers': 'content-type',
      });
      res.end();
      return;
    }

    try {
      if (url.pathname === '/health' && req.method === 'GET') {
        return json(res, 200, { ok: true, service: 'aardvark', ports: registry.list() });
      }

      if (url.pathname === '/v1/ports' && req.method === 'GET') {
        return json(res, 200, { ports: registry.list() });
      }

      if (url.pathname === '/v1/ports' && req.method === 'POST') {
        const body = await readBody(req);
        const agentKey = body.agentKey || 'default';
        const sessionId = body.sessionId || 'unknown';
        const entry = await registry.allocate(agentKey, sessionId, (port, req, res) =>
          handleProxyRequest(port, req, res, verbosity)
        );
        return json(res, 200, entry);
      }

      const delMatch = url.pathname.match(/^\/v1\/ports\/([^/]+)$/);
      if (delMatch && req.method === 'DELETE') {
        const closed = registry.close(decodeURIComponent(delMatch[1]));
        return json(res, 200, { closed });
      }

      if (url.pathname === '/v1/config' && req.method === 'GET') {
        return json(res, 200, {
          verbosity: process.env.AARDVARK_VERBOSITY || 'meta',
          upstream: process.env.AARDVARK_UPSTREAM || null,
          braidUrl: process.env.BRAID_URL || 'http://127.0.0.1:4711',
        });
      }

      json(res, 404, { error: 'not_found' });
    } catch (err) {
      json(res, 500, { error: err instanceof Error ? err.message : String(err) });
    }
  });
}

module.exports = { createControlServer };
