import type {
  MergedDiagram,
  SectionResult,
  StitchedMap,
  ValidationViewPackage,
} from './sectionalTypes';

/**
 * Merge sectional Shufti run manifests into one stitched map (no HTTP).
 */
export function stitchSections(
  workspaceRoot: string,
  sections: SectionResult[],
  generatedAtUtc: string,
): StitchedMap {
  const merged_diagrams: MergedDiagram[] = [];
  const seen = new Set<string>();

  for (const section of sections) {
    for (const artifact of section.artifact_manifest) {
      const key = `${artifact.name}:${artifact.path}`;
      if (seen.has(key)) {
        continue;
      }
      seen.add(key);
      merged_diagrams.push({
        name: `${section.task_id}__${artifact.name}`,
        format: artifact.format,
        path: artifact.path,
      });
    }
  }

  const validation_view: ValidationViewPackage = {
    schema_version: '1.0.0',
    workspace_root: workspaceRoot,
    view_kind: 'agentic_system_validation',
    segments: sections.map((section) => {
      const codeTopology =
        section.code_topology_path ??
        section.artifact_manifest.find((artifact) => artifact.name === 'code_topology')?.path ??
        null;
      const systemMap =
        section.system_map_path ??
        section.artifact_manifest.find((artifact) => artifact.name === 'system_map')?.path ??
        null;

      return {
        id: section.task_id,
        run_id: section.run_id,
        code_topology_path: codeTopology,
        system_map_path: systemMap,
        topology_fingerprint: section.topology_fingerprint ?? null,
        line_count: section.line_count,
        file_count: section.file_count,
        updated_at_utc: section.updated_at_utc ?? null,
      };
    }),
    stitched_system_map_path:
      merged_diagrams.find((diagram) => diagram.name.endsWith('__system_map'))?.path ?? null,
    incremental_update: {
      strategy: 'segment_fingerprint',
      changed_segments: [],
      stale_segments: [],
    },
    webview_contract: {
      entry_view: 'system_overview',
      component_drilldown: 'component_detail',
      agent_drilldown: 'agent_card',
      live_streams: ['braid.events', 'aispy.agents', 'aispy.area_update'],
    },
  };

  return {
    workspace_root: workspaceRoot,
    sections,
    merged_diagrams,
    validation_view,
    generated_at_utc: generatedAtUtc,
  };
}
