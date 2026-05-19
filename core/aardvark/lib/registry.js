'use strict';

const http = require('http');

class PortRegistry {
  constructor() {
    /** @type {Map<string, { agentKey: string, sessionId: string, port: number, server: import('http').Server }>} */
    this.ports = new Map();
    this.nextPort = Number(process.env.AARDVARK_PORT_BASE || 48200);
  }

  list() {
    return [...this.ports.values()].map(({ agentKey, sessionId, port }) => ({
      agentKey,
      sessionId,
      port,
    }));
  }

  get(agentKey) {
    return this.ports.get(agentKey) || null;
  }

  /**
   * @param {string} agentKey
   * @param {string} sessionId
   * @param {(port: number, req: import('http').IncomingMessage, res: import('http').ServerResponse) => void} onRequest
   */
  allocate(agentKey, sessionId, onRequest) {
    const existing = this.ports.get(agentKey);
    if (existing) {
      this.close(agentKey);
    }
    const port = this.nextPort++;
    const server = http.createServer((req, res) => onRequest(port, req, res));
    return new Promise((resolve, reject) => {
      server.listen(port, '127.0.0.1', () => {
        this.ports.set(agentKey, { agentKey, sessionId, port, server });
        resolve({ agentKey, sessionId, port });
      });
      server.on('error', reject);
    });
  }

  close(agentKey) {
    const entry = this.ports.get(agentKey);
    if (!entry) return false;
    entry.server.close();
    this.ports.delete(agentKey);
    return true;
  }

  closeAll() {
    for (const key of [...this.ports.keys()]) {
      this.close(key);
    }
  }
}

module.exports = { PortRegistry };
