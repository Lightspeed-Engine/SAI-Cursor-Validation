#!/usr/bin/env node
'use strict';

const { PortRegistry } = require('../lib/registry');
const { createControlServer } = require('../lib/server');

const host = process.env.AARDVARK_HOST || '127.0.0.1';
const port = Number(process.env.AARDVARK_PORT || 4712);

const registry = new PortRegistry();
const server = createControlServer(registry);

server.listen(port, host, () => {
  console.log(`[sai-aardvark] control http://${host}:${port}`);
  console.log('[sai-aardvark] POST /v1/ports to allocate proxy (recording must be on in braid)');
});

function shutdown() {
  registry.closeAll();
  server.close(() => process.exit(0));
}
process.on('SIGINT', shutdown);
process.on('SIGTERM', shutdown);
