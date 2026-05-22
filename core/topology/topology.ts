/**
 * Merge Shufti codebase areas with AI-Spy live system_areas into map sectors.
 * Upstream: ai-spy/src/topology.ts
 */

import type {
  ShuftiAreaInfo,
  ShuftiDiscoveredArea,
  SystemArea,
  TopologyOverlay,
  TopologySector,
} from './types';

const APP_AREA_HINTS: Record<string, string[]> = {
  lse_core: ['core', 'services', 'lse'],
  standalone_deployment: ['deployment', 'standalone'],
  mcp: ['mcp', 'server'],
  mcp_jackpot: ['mcp', 'dashboard', 'jackpot'],
  lightspeed_engine: ['workspace', 'engine'],
};

function normalize(value: string | null | undefined): string {
  return (value ?? '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
}

function tokenize(value: string | null | undefined): string[] {
  return normalize(value)
    .split(/\s+/)
    .filter(Boolean);
}

function scoreTextMatch(area: SystemArea, target: string, candidateId?: string): number {
  const haystack = normalize([target, candidateId].filter(Boolean).join(' '));
  const areaTokens = new Set([
    ...tokenize(area.name),
    ...tokenize(area.feature_area),
    ...tokenize(area.app_area),
  ]);

  let score = 0;

  for (const token of areaTokens) {
    if (haystack.includes(token)) {
      score += token.length > 5 ? 5 : 3;
    }
  }

  const exactFeature = normalize(area.feature_area || area.name);
  if (exactFeature && haystack.includes(exactFeature)) {
    score += 10;
  }

  for (const hint of APP_AREA_HINTS[area.app_area] ?? []) {
    if (haystack.includes(hint)) {
      score += 2;
    }
  }

  return score;
}

function pickBestAvailableArea(
  area: SystemArea,
  availableAreas: ShuftiAreaInfo[],
): ShuftiAreaInfo | null {
  let bestMatch: ShuftiAreaInfo | null = null;
  let bestScore = -1;

  for (const candidate of availableAreas) {
    const score = scoreTextMatch(area, candidate.path, candidate.id);
    if (score > bestScore) {
      bestScore = score;
      bestMatch = candidate;
    }
  }

  return bestScore > 0 ? bestMatch : null;
}

function pickBestDiscoveredArea(
  area: SystemArea,
  discoveredAreas: ShuftiDiscoveredArea[],
): ShuftiDiscoveredArea | null {
  let bestMatch: ShuftiDiscoveredArea | null = null;
  let bestScore = -1;

  for (const candidate of discoveredAreas) {
    const score = scoreTextMatch(area, candidate.path);
    if (score > bestScore) {
      bestScore = score;
      bestMatch = candidate;
    }
  }

  return bestScore > 0 ? bestMatch : null;
}

function buildOverlay(
  area: SystemArea,
  availableAreas: ShuftiAreaInfo[],
  discoveredAreas: ShuftiDiscoveredArea[],
): TopologyOverlay {
  const available = pickBestAvailableArea(area, availableAreas);
  const discovered = pickBestDiscoveredArea(area, discoveredAreas);

  if (available && discovered) {
    return {
      source: 'hybrid',
      coverage_path: discovered.path,
      estimated_files: discovered.estimated_files,
      estimated_lines: discovered.estimated_lines,
      recommended_max_files: available.recommended_max_files,
      recommended_max_lines: available.recommended_max_lines,
      sub_area_count: discovered.sub_areas.length,
    };
  }

  if (discovered) {
    return {
      source: 'shufti_discovered',
      coverage_path: discovered.path,
      estimated_files: discovered.estimated_files,
      estimated_lines: discovered.estimated_lines,
      recommended_max_files: null,
      recommended_max_lines: null,
      sub_area_count: discovered.sub_areas.length,
    };
  }

  if (available) {
    return {
      source: 'shufti_available',
      coverage_path: available.path,
      estimated_files: available.estimated_files,
      estimated_lines: available.estimated_lines,
      recommended_max_files: available.recommended_max_files,
      recommended_max_lines: available.recommended_max_lines,
      sub_area_count: 0,
    };
  }

  return {
    source: 'daemon_only',
    coverage_path: null,
    estimated_files: null,
    estimated_lines: null,
    recommended_max_files: null,
    recommended_max_lines: null,
    sub_area_count: 0,
  };
}

function bandSeverity(value: string): number {
  return { green: 0, yellow: 1, orange: 2, red: 3 }[value] ?? 0;
}

/**
 * Build sector map for UI: group Spy system_areas by app_area, attach Shufti path overlay.
 */
export function buildTopologySectors(
  systemAreas: SystemArea[],
  availableAreas: ShuftiAreaInfo[],
  discoveredAreas: ShuftiDiscoveredArea[],
): TopologySector[] {
  if (systemAreas.length === 0) {
    return [];
  }

  const sectorMap = new Map<string, TopologySector>();

  for (const area of systemAreas) {
    const appArea = area.app_area || 'unclassified';
    const overlay = buildOverlay(area, availableAreas, discoveredAreas);

    if (!sectorMap.has(appArea)) {
      sectorMap.set(appArea, {
        app_area: appArea,
        active_count: 0,
        verified_count: 0,
        observed_count: 0,
        estimated_files: 0,
        estimated_lines: 0,
        feature_areas: [],
      });
    }

    const sector = sectorMap.get(appArea)!;
    sector.active_count += area.active_count;
    sector.verified_count += area.verified_count;
    sector.observed_count += area.observed_count;
    sector.estimated_files += overlay.estimated_files ?? 0;
    sector.estimated_lines += overlay.estimated_lines ?? 0;
    sector.feature_areas.push({ area, overlay });
  }

  return Array.from(sectorMap.values())
    .map((sector) => ({
      ...sector,
      feature_areas: sector.feature_areas.sort((left, right) => {
        const bandDelta =
          bandSeverity(right.area.performance_band) -
          bandSeverity(left.area.performance_band);
        if (bandDelta !== 0) {
          return bandDelta;
        }
        return right.area.active_count - left.area.active_count;
      }),
    }))
    .sort((left, right) => right.active_count - left.active_count);
}
