/**
 * S5 PASS/FAIL — sectional stitch (PLAN § S5, no network).
 * Run: npx tsx --test tests/shufti/s5/test_sectional_stitch_offline.ts
 */

import assert from 'node:assert/strict';
import { describe, it } from 'node:test';

import { stitchSections } from '../../../core/topology/sectionalStitch.ts';
import type { SectionResult } from '../../../core/topology/sectionalTypes.ts';
import { recordFail, recordPass, testStart } from '../../lib/test-log.ts';

describe('S5 sectional stitch', { timeout: 5000 }, () => {
  it('stitches two section results into one map', () => {
    const id = 'stitches two section results into one map';
    testStart('S5', id);
    try {
    const sections: SectionResult[] = [
      {
        task_id: 'area-a',
        run_id: 'run-aaa',
        artifact_manifest: [
          { name: 'dependency_graph', format: 'mermaid', path: '/tmp/a/dependency_graph.mmd' },
        ],
        line_count: 12_000,
        file_count: 40,
      },
      {
        task_id: 'area-b',
        run_id: 'run-bbb',
        artifact_manifest: [
          { name: 'dependency_graph', format: 'mermaid', path: '/tmp/b/dependency_graph.mmd' },
        ],
        line_count: 8_000,
        file_count: 22,
      },
    ];

      const stitched = stitchSections('/workspace', sections, '2026-05-21T12:00:00Z');

      if (stitched.sections.length !== 2) {
        recordFail('S5', id, 'SHUFTI-0300', `sections ${stitched.sections.length}`);
      }
      if (stitched.merged_diagrams.length < 1) {
        recordFail('S5', id, 'SHUFTI-0300', 'no merged_diagrams');
      }
      if (stitched.workspace_root !== '/workspace') {
        recordFail('S5', id, 'SHUFTI-0300', 'workspace_root mismatch');
      }
      if (!/^\d{4}-\d{2}-\d{2}T/.test(stitched.generated_at_utc)) {
        recordFail('S5', id, 'SHUFTI-0300', 'invalid generated_at_utc');
      }
      recordPass('S5', id);
    } catch (err) {
      recordFail('S5', id, 'SAIV-TEST-0003', String(err));
    }
  });
});
