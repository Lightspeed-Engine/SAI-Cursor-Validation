/**
 * S2 PASS/FAIL — buildTopologySectors merge (PLAN § S2, no network).
 * Run: npx tsx --test tests/shufti/s2/test_topology_merge_offline.ts
 */

import assert from 'node:assert/strict';
import { describe, it } from 'node:test';

import { buildTopologySectors } from '../../../core/topology/topology.ts';
import type {
  ShuftiAreaInfo,
  ShuftiDiscoveredArea,
  SystemArea,
} from '../../../core/topology/types.ts';
import { recordFail, recordPass, testStart } from '../../lib/test-log.ts';

const systemAreas: SystemArea[] = [
  {
    name: 'agent_enrollment',
    app_area: 'lse_core',
    feature_area: 'agent_enrollment',
    active_count: 2,
    verified_count: 1,
    observed_count: 1,
    tool_rate: 10,
    token_rate: 100,
    context_util: 0.4,
    performance_band: 'green',
    dominant_models: ['test'],
    latest_activity: 1,
    worst_band: 'green',
  },
  {
    name: 'mcp_server',
    app_area: 'mcp',
    feature_area: 'mcp_server',
    active_count: 1,
    verified_count: 0,
    observed_count: 1,
    tool_rate: 5,
    token_rate: 50,
    context_util: 0.2,
    performance_band: 'yellow',
    dominant_models: ['test'],
    latest_activity: 2,
    worst_band: 'yellow',
  },
];

const shuftiAreas: ShuftiAreaInfo[] = [
  {
    id: 'area-enrollment',
    path: 'core/services/agent_enrollment',
    estimated_files: 100,
    estimated_lines: 20_000,
    recommended_max_lines: 100_000,
    recommended_max_files: 500,
  },
];

const shuftiDiscovered: ShuftiDiscoveredArea[] = [
  {
    path: 'core/services/agent_enrollment',
    estimated_files: 95,
    estimated_lines: 18_000,
    sub_areas: [{ path: 'ai-spy', estimated_files: 20, estimated_lines: 4000 }],
  },
];

describe('S2 topology merge', { timeout: 5000 }, () => {
  it('returns two sectors for two system areas', () => {
    const id = 'returns two sectors for two system areas';
    testStart('S2', id);
    try {
      const sectors = buildTopologySectors(systemAreas, shuftiAreas, shuftiDiscovered);
      if (sectors.length !== 2) {
        recordFail('S2', id, 'SHUFTI-0200', `expected 2 sectors, got ${sectors.length}`);
      }
      recordPass('S2', id);
    } catch (err) {
      recordFail('S2', id, 'SAIV-TEST-0003', String(err));
    }
  });

  it('includes at least one hybrid overlay when paths align', () => {
    const id = 'includes at least one hybrid overlay when paths align';
    testStart('S2', id);
    try {
      const sectors = buildTopologySectors(systemAreas, shuftiAreas, shuftiDiscovered);
      const overlays = sectors.flatMap((s) => s.feature_areas.map((f) => f.overlay.source));
      if (!overlays.includes('hybrid')) {
        recordFail('S2', id, 'SHUFTI-0201', `overlays: ${overlays.join(',')}`);
      }
      recordPass('S2', id);
    } catch (err) {
      recordFail('S2', id, 'SAIV-TEST-0003', String(err));
    }
  });

  it('returns empty array when system_areas empty', () => {
    const id = 'returns empty array when system_areas empty';
    testStart('S2', id);
    try {
      const sectors = buildTopologySectors([], shuftiAreas, shuftiDiscovered);
      if (sectors.length !== 0) {
        recordFail('S2', id, 'SHUFTI-0200', `expected 0 sectors, got ${sectors.length}`);
      }
      recordPass('S2', id);
    } catch (err) {
      recordFail('S2', id, 'SAIV-TEST-0003', String(err));
    }
  });
});
