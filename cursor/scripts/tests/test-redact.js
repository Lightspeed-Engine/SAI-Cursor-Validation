#!/usr/bin/env node
'use strict';

const { redact } = require('../hooks/redact');

let failed = 0;

function assert(name, cond) {
  if (!cond) {
    console.error('FAIL:', name);
    failed++;
  } else {
    console.log('PASS:', name);
  }
}

const out = redact({
  authorization: 'Bearer sk-live-secret',
  password: 'hunter2',
  tool_output: 'token Bearer abc.def.ghi in text',
  nested: { api_key: 'ghp_abcdefghijklmnopqrstuvwxyz1234567890' },
});

assert('authorization redacted', out.authorization === '[REDACTED]');
assert('password redacted', out.password === '[REDACTED]');
assert('bearer in string', out.tool_output.includes('[REDACTED]'));
assert('nested api_key', out.nested.api_key === '[REDACTED]');

process.exit(failed ? 1 : 0);
