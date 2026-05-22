/**
 * Topology + Shufti types (adapted from Lightspeed ai-spy UI).
 * Upstream: LSE-Core-2.0-2.1/core/services/agent_enrollment/ai-spy/src/types.ts
 */

export type PerformanceBand = 'green' | 'yellow' | 'orange' | 'red';

export interface SystemArea {
  name: string;
  app_area: string;
  feature_area?: string;
  active_count: number;
  verified_count: number;
  observed_count: number;
  tool_rate: number;
  token_rate: number;
  context_util: number;
  performance_band: PerformanceBand;
  dominant_models: string[];
  latest_activity: number | string | null;
  worst_band: PerformanceBand;
}

export interface ShuftiAreaInfo {
  id: string;
  path: string;
  estimated_files: number;
  estimated_lines: number;
  recommended_max_lines: number;
  recommended_max_files: number;
}

export interface ShuftiSubArea {
  path: string;
  estimated_files: number;
  estimated_lines: number;
}

export interface ShuftiDiscoveredArea {
  path: string;
  estimated_files: number;
  estimated_lines: number;
  sub_areas: ShuftiSubArea[];
}

export type TopologyOverlaySource =
  | 'daemon_only'
  | 'shufti_available'
  | 'shufti_discovered'
  | 'hybrid';

export interface TopologyOverlay {
  source: TopologyOverlaySource;
  coverage_path: string | null;
  estimated_files: number | null;
  estimated_lines: number | null;
  recommended_max_files: number | null;
  recommended_max_lines: number | null;
  sub_area_count: number;
}

export interface TopologyFeatureArea {
  area: SystemArea;
  overlay: TopologyOverlay;
}

export interface TopologySector {
  app_area: string;
  active_count: number;
  verified_count: number;
  observed_count: number;
  estimated_files: number;
  estimated_lines: number;
  feature_areas: TopologyFeatureArea[];
}

/** Minimal agent row for area drill-down (from AI-Spy daemon). */
export interface AgentSummary {
  id: string;
  agent_id?: string;
  display_name?: string;
  provider?: string;
  model_name?: string;
  current_path?: string;
  application_area?: string;
  feature_area?: string;
  service_area?: string;
  tool_call_count?: number;
  chat_tokens?: number;
  reasoning_tokens?: number;
  performance_band?: PerformanceBand;
}

export interface AreaStats {
  area_name: string;
  active_agents: number;
  verified_agents: number;
  observed_agents: number;
  tool_call_volume: number;
  token_volume: number;
  avg_context_utilization: number;
  performance_band_distribution: Record<PerformanceBand, number>;
  top_tools: Array<{ name: string; count: number }>;
  top_models: Array<{ name: string; count: number }>;
  hottest_paths: string[];
}
