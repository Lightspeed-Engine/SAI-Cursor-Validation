'use strict';

const http = require('http');
const https = require('https');
const { URL } = require('url');
const { isRecording, ingestObservation } = require('./braid-client');

/**
 * @param {'meta' | 'headers' | 'body-preview' | 'debug'} verbosity
 */
function buildObservation(port, req, res, started, verbosity) {
  const host = req.headers.host || 'unknown';
  const path = req.url || '/';
  const obs = {
    v: 1,
    ts: new Date().toISOString(),
    source: 'aardvark.http',
    sessionId: 'unknown',
    agentKey: 'unknown',
    type: 'http.request',
    payload: {
      listenPort: port,
      method: req.method,
      host,
      path,
      verbosity,
    },
  };
  if (verbosity === 'headers' || verbosity === 'debug') {
    obs.payload.headers = { ...req.headers };
    delete obs.payload.headers.authorization;
    delete obs.payload.headers['x-api-key'];
  }
  return obs;
}

function forwardHttp(req, res, targetUrl, verbosity, port) {
  const started = Date.now();
  const url = new URL(targetUrl);
  const lib = url.protocol === 'https:' ? https : http;

  const proxyReq = lib.request(
    {
      hostname: url.hostname,
      port: url.port || (url.protocol === 'https:' ? 443 : 80),
      path: url.pathname + url.search,
      method: req.method,
      headers: { ...req.headers, host: url.host },
    },
    (proxyRes) => {
      void (async () => {
        if (await isRecording()) {
          await ingestObservation({
            v: 1,
            ts: new Date().toISOString(),
            source: 'aardvark.http',
            sessionId: 'unknown',
            agentKey: 'unknown',
            type: 'http.response',
            payload: {
              listenPort: port,
              status: proxyRes.statusCode,
              durationMs: Date.now() - started,
              host: url.host,
              path: url.pathname,
              verbosity,
            },
          });
        }
      })();
      res.writeHead(proxyRes.statusCode || 502, proxyRes.headers);
      proxyRes.pipe(res);
    }
  );

  proxyReq.on('error', () => {
    res.writeHead(502);
    res.end('bad gateway');
  });

  req.pipe(proxyReq);

  void (async () => {
    if (await isRecording()) {
      await ingestObservation(buildObservation(port, req, res, started, verbosity));
    }
  })();
}

function handleProxyRequest(port, req, res, verbosity) {
  if (req.method === 'CONNECT') {
    res.writeHead(200, 'Connection Established');
    res.end();
    void (async () => {
      if (await isRecording()) {
        await ingestObservation({
          v: 1,
          ts: new Date().toISOString(),
          source: 'aardvark.http',
          sessionId: 'unknown',
          agentKey: 'unknown',
          type: 'http.connect',
          payload: { listenPort: port, target: req.url, verbosity },
        });
      }
    })();
    return;
  }

  const target = process.env.AARDVARK_UPSTREAM;
  if (!target) {
    res.writeHead(200, { 'content-type': 'application/json' });
    res.end(
      JSON.stringify({
        ok: true,
        service: 'aardvark-proxy',
        port,
        hint: 'Set AARDVARK_UPSTREAM or use as forward proxy with full URL',
      })
    );
    return;
  }

  try {
    const base = target.replace(/\/$/, '');
    const path = req.url?.startsWith('/') ? req.url : `/${req.url || ''}`;
    forwardHttp(req, res, `${base}${path}`, verbosity, port);
  } catch {
    res.writeHead(400);
    res.end('bad request');
  }
}

module.exports = { handleProxyRequest };
