/**
 * Sectional Shufti scan contract (PLAN slice S5).
 */

export interface ArtifactRef {
  name: string;
  format: string;
  path: string;
  kind?: string;
}

export interface SectionTask {
  id: string;
  root: string;
  paths: string[];
  max_lines: number;
  max_files: number;
  reason?: string;
}

export interface SectionResult {
  task_id: string;
  run_id: string;
  artifact_manifest: ArtifactRef[];
  line_count: number;
  file_count: number;
  topology_fingerprint?: string;
  code_topology_path?: string;
  system_map_path?: string;
  updated_at_utc?: string;
}

export interface MergedDiagram {
  name: string;
  format: string;
  path: string;
}

export interface StitchedMap {
  workspace_root: string;
  sections: SectionResult[];
  merged_diagrams: MergedDiagram[];
  validation_view: ValidationViewPackage;
  generated_at_utc: string;
}

export interface ValidationViewSegment {
  id: string;
  run_id: string;
  code_topology_path: string | null;
  system_map_path: string | null;
  topology_fingerprint: string | null;
  line_count: number;
  file_count: number;
  updated_at_utc: string | null;
}

export interface ValidationViewPackage {
  schema_version: string;
  workspace_root: string;
  view_kind: 'agentic_system_validation';
  segments: ValidationViewSegment[];
  stitched_system_map_path: string | null;
  incremental_update: {
    strategy: 'segment_fingerprint';
    changed_segments: string[];
    stale_segments: string[];
  };
  webview_contract: {
    entry_view: 'system_overview';
    component_drilldown: 'component_detail';
    agent_drilldown: 'agent_card';
    live_streams: string[];
  };
}
