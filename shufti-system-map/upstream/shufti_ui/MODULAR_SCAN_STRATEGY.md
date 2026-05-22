# Modular Scan Strategy for SHUFTI

**Document Version:** 1.0  
**Created:** 2026-04-02  
**Purpose:** Define a modular approach for scanning large codebases that exceed the default 100,000 line limit

---

## 1. Problem Statement

The SHUFTI code mapper has default limits:
- `MAX_LINES = 100,000` (default)
- `MAX_FILES = 250` (default)
- `MAX_FILE_BYTES = 1,000,000` per file

The Lightspeed Engine codebase contains approximately ~500,000+ lines of Python code across multiple top-level directories. Scanning the entire codebase in a single pass exceeds these limits, causing the mapper to fail with:

```
ValueError: target scope reached X lines, which exceeds the limit of 100000
```

---

## 2. Current Architecture Analysis

### 2.1 shufti_code_mapper.py

**Key Functions:**
- `iter_python_files(targets, mode, max_files)` - Resolves targets to Python files, enforces file limits
- `walk_python_files(root, max_files, existing_count)` - Recursively walks directory tree
- `FileAnalyzer(path, analysis_root, max_file_bytes).analyze()` - Parses single file with AST
- Line counting happens during `FileAnalyzer.analyze()` via `len(self.source.splitlines())`

**Current Flow:**
1. Resolve targets to file paths
2. Walk directory tree collecting `.py` files (respecting `IGNORED_DIR_NAMES`)
3. For each file, analyze with AST (imports, functions, classes, patterns)
4. Track cumulative line count during analysis
5. Fail fast if `lines_reviewed > max_lines`

### 2.2 shufti_ui_server.py

**Current API Endpoint:** `POST /api/map`

**Request Parameters:**
```json
{
  "targets": ["path/to/scan"],
  "mode": "auto|file|app",
  "format": "markdown|json",
  "max_files": 250,
  "max_lines": 100000,
  "max_file_bytes": 1000000,
  "timeout_seconds": 120,
  "generate_diagrams": true,
  "diagram_format": "dot|mermaid"
}
```

**Execution Model:**
- Spawns subprocess with mapper command
- Captures stdout/stderr
- Writes output to `runs/{run_id}/code-map.{md|json}`
- Generates diagram artifacts in `runs/{run_id}/diagrams/`

### 2.3 Frontend (app.js)

- Manages target selection and run execution
- Displays single map output at a time
- Shows run history with artifact links
- Supports baseline comparison for diffs

---

## 3. Partitioning Strategy

### 3.1 Recommended Area Definitions

Based on the repository structure, partition into the following scannable areas:

| Area | Path | Estimated Lines | Recommended max_lines | Justification |
|------|------|-----------------|---------------------|---------------|
| **Core Services** | `core/services/` | ~120,000 | 80,000 | Primary application logic, split into core/services-*.py if needed |
| **Core Configs** | `core/configs/` | ~15,000 | 20,000 | Small, low complexity |
| **Scripts** | `scripts/` | ~60,000 | 60,000 | Utility scripts, varied complexity |
| **Deployment** | `deployment/` | ~40,000 | 50,000 | Docker, kubernetes configs |
| **Containers** | `containers/` | ~20,000 | 25,000 | Container definitions |
| **Tests** | `tests/` | ~100,000 | 80,000 | Test suites, may need further split |
| **Src** | `src/` | ~50,000 | 60,000 | Source modules |
| **Configs** | `configs/` | ~10,000 | 15,000 | Configuration files |
| **Tools** | `tools/` | ~15,000 | 20,000 | Development tools |
| **Environments** | `environments/` | ~30,000 | 35,000 | Environment definitions |

**Total Estimated:** ~460,000 lines across 10 areas

### 3.2 Area Boundaries

Each area should be mutually exclusive to avoid duplicate scanning:

```
LSE-Core-2.0-2.1/
├── core/
│   ├── configs/      → Area: core_configs
│   └── services/     → Area: core_services
├── scripts/          → Area: scripts
├── deployment/       → Area: deployment
├── containers/       → Area: containers
├── tests/            → Area: tests
├── src/              → Area: src
├── configs/          → Area: configs
├── tools/            → Area: tools
├── environments/     → Area: environments
└── ...other dirs...
```

### 3.3 Fine-Grained Partitioning for Large Areas

For areas exceeding 80,000 lines, implement sub-partitioning:

**Core Services (120,000 lines):**
- `core/services/sigauth/` → ~30,000 lines
- `core/services/sigchain_adapter/` → ~25,000 lines
- `core/services/control_plane/` → ~20,000 lines
- `core/services/mcp/` → ~25,000 lines
- `core/services/sigfile/` → ~20,000 lines

**Tests (100,000 lines):**
- `tests/unit/` → ~40,000 lines
- `tests/integration/` → ~35,000 lines  
- `tests/agent_hub/` → ~25,000 lines

---

## 4. API Changes for Multi-Area Scanning

### 4.1 New Endpoint: POST /api/multi-map

**Purpose:** Execute modular scans across multiple areas with aggregation

**Request:**
```json
{
  "areas": [
    {
      "id": "core_services",
      "path": "core/services",
      "max_lines": 80000,
      "max_files": 200
    },
    {
      "id": "scripts",
      "path": "scripts",
      "max_lines": 60000,
      "max_files": 150
    }
  ],
  "aggregate": true,
  "merge_patterns": true,
  "merge_dependencies": true,
  "format": "json"
}
```

**Response:**
```json
{
  "ok": true,
  "run_id": "20260402T120000Z-abc123",
  "area_results": [
    {
      "area_id": "core_services",
      "status": "success",
      "files_included": 180,
      "lines_reviewed": 78500,
      "stubs_detected": 42,
      "snapshot_path": "runs/.../core_services/snapshot.json",
      "map_path": "runs/.../core_services/code-map.json"
    },
    {
      "area_id": "scripts",
      "status": "success",
      "files_included": 145,
      "lines_reviewed": 58200,
      "stubs_detected": 28,
      "snapshot_path": "runs/.../scripts/snapshot.json",
      "map_path": "runs/.../scripts/code-map.json"
    }
  ],
  "aggregated": {
    "total_files": 325,
    "total_lines": 136700,
    "total_stubs": 70,
    "merged_patterns": [...],
    "merged_dependency_edges": [...],
    "cross_area_dependencies": [...]
  }
}
```

### 4.2 Modified Endpoint: GET /api/areas

**Purpose:** Query available areas and their current sizes

**Response:**
```json
{
  "ok": true,
  "areas": [
    {
      "id": "core_services",
      "path": "core/services",
      "estimated_files": 195,
      "estimated_lines": 120000,
      "recommended_max_lines": 80000,
      "last_scanned": "2026-04-01T10:30:00Z",
      "scan_count": 5
    }
  ]
}
```

### 4.3 Area Discovery Endpoint: POST /api/scan/discover

**Purpose:** Scan repository structure and propose area partitions

**Request:**
```json
{
  "root": "LSE-Core-2.0-2.1",
  "max_areas": 12,
  "max_lines_per_area": 80000
}
```

**Response:**
```json
{
  "ok": true,
  "proposed_areas": [
    {
      "path": "core/services",
      "estimated_files": 195,
      "estimated_lines": 120000,
      "sub_areas": [
        {"path": "core/services/sigauth", "estimated_lines": 30000},
        {"path": "core/services/sigchain_adapter", "estimated_lines": 25000}
      ]
    }
  ],
  "total_estimated_lines": 460000
}
```

---

## 5. Backend Implementation Details

### 5.1 Area Scanner Class

```python
@dataclass
class AreaScanConfig:
    area_id: str
    target_path: str
    max_lines: int = 80_000
    max_files: int = 200
    max_file_bytes: int = 1_000_000
    mode: str = "app"
    generate_diagrams: bool = False
    diagram_format: str = "dot"

@dataclass  
class AreaScanResult:
    area_id: str
    status: str  # "success", "partial", "failed"
    files_included: int
    lines_reviewed: int
    stubs_detected: int
    analysis_errors: list[str]
    snapshot_path: Path
    map_path: Path
    error_message: Optional[str] = None
```

### 5.2 Multi-Area Scanner Orchestrator

```python
class MultiAreaScanner:
    def __init__(self, repo_root: Path, runs_dir: Path):
        self.repo_root = repo_root
        self.runs_dir = runs_dir
        
    def scan_areas(
        self,
        area_configs: list[AreaScanConfig],
        aggregate: bool = True
    ) -> MultiAreaResult:
        results = []
        for config in area_configs:
            result = self._scan_single_area(config)
            results.append(result)
            
        if aggregate:
            return self._aggregate_results(results)
        return MultiAreaResult(area_results=results)
        
    def _scan_single_area(self, config: AreaScanConfig) -> AreaScanResult:
        # Execute mapper with area-specific limits
        # Write results to runs/{run_id}/{area_id}/
        pass
        
    def _aggregate_results(
        self,
        results: list[AreaScanResult]
    ) -> AggregatedResult:
        # Merge patterns across areas
        # Resolve cross-area dependencies
        # Generate unified report
        pass
```

### 5.3 Cross-Area Dependency Resolution

When scanning multiple areas, dependencies between areas must be tracked:

1. **Intra-area dependencies:** Already captured by single-scan mapper
2. **Cross-area dependencies:** Need to track when file in Area A imports from Area B

**Resolution Algorithm:**
```python
def resolve_cross_area_dependencies(
    area_results: list[AreaScanResult],
    area_configs: list[AreaScanConfig]
) -> list[CrossAreaEdge]:
    edges = []
    for result in area_results:
        for file in result.files:
            for import_target in file.imports:
                target_area = find_area_for_module(import_target, area_configs)
                if target_area and target_area != result.area_id:
                    edges.append(CrossAreaEdge(
                        source_area=result.area_id,
                        target_area=target_area,
                        source_file=file.path,
                        target_module=import_target
                    ))
    return edges
```

---

## 6. Frontend Rendering Approach

### 6.1 Multi-Area Results Display

**New UI Components:**

1. **Area Selector Panel**
   - Checkbox list of available areas
   - Show estimated line count per area
   - "Select All" / "Deselect All" buttons
   - Custom max_lines override per area

2. **Area Results Tabs**
   - Tabbed interface: "Overview" | "Area 1" | "Area 2" | ...
   - Each tab shows that area's map output
   - "Overview" shows aggregated summary

3. **Cross-Area Dependency View**
   - Mermaid diagram showing area-to-area dependencies
   - Nodes = areas, edges = cross-area imports
   - Click to drill down into specific dependency

### 6.2 Aggregation Display

**Overview Tab Content:**
```
## Modular Scan Summary

Total Areas Scanned: 8
Total Files: 342
Total Lines: 425,000
Total Stubs: 87

## Area Breakdown
| Area | Files | Lines | Stubs | Status |
|------|-------|-------|-------|--------|
| core_services | 195 | 118,000 | 42 | ✓ |
| scripts | 87 | 58,200 | 18 | ✓ |
| ... |

## Cross-Area Dependencies
- core_services → scripts (12 imports)
- scripts → deployment (3 imports)
...
```

### 6.3 Interactive Features

1. **Area Drill-Down**
   - Click area row → switch to area tab with full map
   - Each file clickable to show file-level details

2. **Dependency Navigation**
   - Click cross-area edge → show which files depend on which
   - Filter: "Show only cross-area imports"

3. **Pattern Aggregation**
   - Pattern count aggregated across all areas
   - Click pattern → show evidence from all areas

---

## 7. Configuration File Format

### 7.1 Area Configuration Schema (areas.yaml)

```yaml
version: "1.0"
areas:
  - id: core_services
    path: core/services
    max_lines: 80000
    max_files: 200
    description: "Core LSE services (SigAuth, SigChain, Control Plane)"
    sub_areas:
      - id: core_services_sigauth
        path: core/services/sigauth
        max_lines: 35000
        
  - id: scripts
    path: scripts
    max_lines: 60000
    max_files: 150
    description: "Utility and maintenance scripts"

defaults:
  max_lines: 80000
  max_files: 200
  max_file_bytes: 1000000
  timeout_seconds: 120
```

### 7.2 Loading Area Config

The server should load area definitions from:
1. **Default:** Built-in area definitions based on repo structure
2. **User config:** `shufti_areas.yaml` in repo root
3. **API discovery:** Query repo and auto-partition

---

## 8. Execution Strategy

### 8.1 Sequential Execution (Default)

For reliability, scan areas sequentially:

```python
for area_config in area_configs:
    result = scan_area(area_config)
    if result.status == "failed":
        logger.warning(f"Area {area_config.area_id} failed: {result.error}")
        # Continue to next area or abort based on policy
```

**Pros:** Simple, predictable, low memory pressure  
**Cons:** Slow for many areas

### 8.2 Parallel Execution (Optional)

For speed, scan independent areas in parallel:

```python
with ThreadPoolExecutor(max_workers=4) as executor:
    futures = [executor.submit(scan_area, config) for config in area_configs]
    results = [f.result() for f in as_completed(futures)]
```

**Pros:** Faster for large repos  
**Cons:** Higher memory, potential file locks

**Constraint:** Limit parallel scans to avoid overwhelming system

### 8.3 Caching Strategy

- **Area-level caching:** If Area X scanned with same limits, reuse results
- **Cache key:** `SHA256(area_id + max_lines + max_files + target_mtime)`
- **Invalidation:** If any file in area modified after scan, invalidate cache

---

## 9. Error Handling

### 9.1 Area-Specific Errors

| Error | Handling |
|-------|----------|
| Area exceeds limits even with increased max_lines | Suggest sub-partitioning, scan with warning |
| Area has 0 Python files | Skip with warning, continue to next |
| Area scan times out | Mark as "timeout", include partial results if available |
| AST parse error in file | Skip file, record in analysis_errors, continue |

### 9.2 Aggregation Errors

| Error | Handling |
|-------|----------|
| No areas successfully scanned | Return error, no aggregated output |
| Some areas failed | Return partial aggregation with failed area list |
| Cross-area resolution fails | Skip cross-area deps, note in output |

---

## 10. Migration Path

### Phase 1: Backend-Only (Non-Breaking)
- Implement `POST /api/multi-map` endpoint
- No changes to frontend
- Users can call new API directly

### Phase 2: Frontend Integration
- Add area selector to UI
- Add "Scan All Areas" button
- Display aggregated results

### Phase 3: Optimization
- Add area discovery endpoint
- Implement caching
- Add parallel execution option

---

## 11. Summary

This modular scan strategy addresses the 100,000 line limit by:

1. **Partitioning** the codebase into 10+ scannable areas based on directory structure
2. **API extension** with multi-area scanning and aggregation endpoints
3. **Cross-area dependency tracking** to understand inter-area relationships
4. **Frontend enhancements** for viewing multi-area results
5. **Caching and optimization** for repeated scans

The approach is backward-compatible, allowing single-area scans to continue working while enabling full-repo analysis through the new modular endpoints.