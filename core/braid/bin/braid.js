#!/usr/bin/env node
'use strict';

const path = require('path');
const { RecordingController } = require('../lib/recording');
const { BraidStore } = require('../lib/store');
const { createBraidServer } = require('../lib/server');

const host = process.env.BRAID_HOST || '127.0.0.1';
const port = Number(process.env.BRAID_PORT || 4711);
const defaultLog =
  process.env.BRAID_LOG_PATH ||
  path.join(process.cwd(), '.cursor/activity/activity.jsonl');

const recording = new RecordingController();
recording.session.logPath = defaultLog;

const store = new BraidStore(recording);
const server = createBraidServer(recording, store);

server.listen(port, host, () => {
  console.log(`[sai-braid] http://${host}:${port} (recording default: off)`);
  console.log(`[sai-braid] log path when recording: ${defaultLog}`);
});

function shutdown() {
  server.close(() => process.exit(0));
}
process.on('SIGINT', shutdown);
process.on('SIGTERM', shutdown);
