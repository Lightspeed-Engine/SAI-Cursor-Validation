const state = {
  config: null,
  currentPath: "",
  targets: [],
  compareRunId: null,
  lastRunId: null,
  lastRunPayload: null,
};

const COMPOSE_MERMAID_NAMES = new Set([
  "high_level_overview",
  "component_coupling",
  "coupling_summary",
]);
const TOPOLOGY_ARTIFACT_NAMES = new Set([
  "code_topology",
  "system_map",
  "filesystem_overview",
]);

const els = {
  bindAddress: document.getElementById("bind-address"),
  repoRoot: document.getElementById("repo-root"),
  dotAvailability: document.getElementById("dot-availability"),
  logsLink: document.getElementById("logs-link"),
  readmeLink: document.getElementById("readme-link"),
  pathInput: document.getElementById("path-input"),
  browseStatus: document.getElementById("browse-status"),
  browserList: document.getElementById("browser-list"),
  targetList: document.getElementById("target-list"),
  compareRunDisplay: document.getElementById("compare-run-display"),
  modeSelect: document.getElementById("mode-select"),
  formatSelect: document.getElementById("format-select"),
  diagramProfileSelect: document.getElementById("diagram-profile-select"),
  diagramFormatSelect: document.getElementById("diagram-format-select"),
  viewerSelect: document.getElementById("viewer-select"),
  generateDiagrams: document.getElementById("generate-diagrams"),
  renderSvg: document.getElementById("render-svg"),
  autoOpenDiagrams: document.getElementById("auto-open-diagrams"),
  maxFilesInput: document.getElementById("max-files-input"),
  maxLinesInput: document.getElementById("max-lines-input"),
  maxFileBytesInput: document.getElementById("max-file-bytes-input"),
  timeoutSecondsInput: document.getElementById("timeout-seconds-input"),
  runStatus: document.getElementById("run-status"),
  previewPath: document.getElementById("preview-path"),
  filePreview: document.getElementById("file-preview"),
  mapOutput: document.getElementById("map-output"),
  mapDownload: document.getElementById("map-download"),
  mapViewerLink: document.getElementById("map-viewer-link"),
  mapOutputLinks: document.getElementById("map-output-links"),
  artifactCount: document.getElementById("artifact-count"),
  artifactList: document.getElementById("artifact-list"),
  diffArtifactCount: document.getElementById("diff-artifact-count"),
  diffArtifactList: document.getElementById("diff-artifact-list"),
  runsList: document.getElementById("runs-list"),
};

async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  const contentType = response.headers.get("content-type") || "";
  if (!contentType.includes("application/json")) {
    const body = await response.text();
    throw new Error(`Expected JSON from ${url}, got ${response.status} ${contentType || "unknown"}: ${body.slice(0, 120)}`);
  }
  const payload = await response.json();
  if (!response.ok || payload.ok === false) {
    const recoveryHint = Array.isArray(payload.recovery_attempts) && payload.recovery_attempts.length
      ? ` Recovery tried: ${payload.recovery_attempts.map((a) => a.step).join(" → ")}.`
      : "";
    const failureLink = payload.failure_url ? ` Details: ${payload.failure_url}` : "";
    throw new Error(
      (payload.error || `Request failed: ${response.status}`)
      + recoveryHint
      + (payload.hint ? ` ${payload.hint}` : "")
      + failureLink
    );
  }
  return payload;
}

function setStatus(node, message, isError = false) {
  node.textContent = message;
  node.style.color = isError ? "var(--danger)" : "var(--muted)";
}

function updateTargetList() {
  if (!state.targets.length) {
    els.targetList.className = "target-list empty";
    els.targetList.textContent = "No targets selected.";
    return;
  }

  els.targetList.className = "target-list";
  els.targetList.innerHTML = "";
  for (const target of state.targets) {
    const chip = document.createElement("div");
    chip.className = "target-chip";
    chip.innerHTML = `
      <span>${target}</span>
      <button class="chip-remove" type="button" aria-label="Remove target">Remove</button>
    `;
    chip.querySelector("button").addEventListener("click", () => {
      state.targets = state.targets.filter((item) => item !== target);
      updateTargetList();
    });
    els.targetList.appendChild(chip);
  }
}

function updateCompareBaseline() {
  if (!state.compareRunId) {
    els.compareRunDisplay.className = "target-list empty";
    els.compareRunDisplay.textContent = "No baseline selected.";
    return;
  }
  els.compareRunDisplay.className = "target-list";
  els.compareRunDisplay.textContent = `Baseline run: ${state.compareRunId}`;
}

function addTarget(path) {
  if (!path) return;
  if (!state.targets.includes(path)) {
    state.targets.push(path);
    updateTargetList();
  }
}

function getViewerMode() {
  return els.viewerSelect?.value || "auto";
}

function isComposeMode() {
  return els.modeSelect.value === "compose";
}

function resolveShuftiDiagramViewerUrl(artifact) {
  const useArchitectureViewer = COMPOSE_MERMAID_NAMES.has(artifact.name)
    || artifact.name === "filesystem_overview";
  const viewer = useArchitectureViewer
    ? "architecture-viewer.html"
    : "mermaid-viewer.html";
  return `/static/${viewer}?src=${encodeURIComponent(artifact.url)}&name=${encodeURIComponent(artifact.name)}`;
}

function resolveArtifactViewerUrl(artifact, runContext = {}) {
  const runId = runContext.runId || state.lastRunId;
  const payload = runContext.payload || state.lastRunPayload;
  const viewerMode = runContext.viewerMode || getViewerMode();
  const mode = runContext.mode || els.modeSelect.value;
  const aispyBase = state.config?.aispy_url || "";

  if (viewerMode === "aispy-live" && aispyBase) {
    return payload?.aispy_live_url || `${aispyBase}/?map=live`;
  }
  if (viewerMode === "aispy-architecture" && aispyBase) {
    return payload?.aispy_architecture_url || `${aispyBase}/?map=architecture`;
  }
  if (mode === "compose" && viewerMode === "auto" && aispyBase) {
    return payload?.aispy_architecture_url || `${aispyBase}/?map=architecture`;
  }

  if (
    viewerMode === "topology-map"
    || (viewerMode === "auto" && TOPOLOGY_ARTIFACT_NAMES.has(artifact.name) && runId)
    || (viewerMode === "auto" && payload?.topology_map_viewer_url && !COMPOSE_MERMAID_NAMES.has(artifact.name))
  ) {
    if (payload?.topology_map_viewer_url) {
      const aispyQuery = aispyBase ? `&aispy=${encodeURIComponent(aispyBase)}` : "";
      return `${payload.topology_map_viewer_url}${aispyQuery}`;
    }
  }

  if (artifact.format === "svg") {
    return artifact.url;
  }
  if (artifact.format === "mermaid") {
    if (viewerMode === "shufti-diagram" || viewerMode === "auto") {
      return resolveShuftiDiagramViewerUrl(artifact);
    }
  }
  return artifact.url;
}

function pickArtifactsToOpen(artifacts, payload) {
  const viewerMode = getViewerMode();
  if (viewerMode === "topology-map" && payload?.topology_map_viewer_url) {
    return [{ format: "topology", url: payload.topology_map_viewer_url, name: "filesystem_map" }];
  }
  if (viewerMode === "aispy-live" && state.config?.aispy_url) {
    return [{ format: "aispy", url: payload?.aispy_live_url || `${state.config.aispy_url}/?map=live`, name: "aispy_live" }];
  }
  if (viewerMode === "aispy-architecture" && state.config?.aispy_url) {
    return [{ format: "aispy", url: payload?.aispy_architecture_url || `${state.config.aispy_url}/?map=architecture`, name: "aispy_architecture" }];
  }
  if (viewerMode === "shufti-diagram") {
    return artifacts.filter((artifact) => ["mermaid", "svg"].includes(artifact.format));
  }
  // Auto + filesystem: open HQ viewer only — never raw .mmd (browser downloads it).
  if (payload?.topology_map_viewer_url && !isComposeMode()) {
    if (viewerMode === "auto" || viewerMode === "topology-map") {
      return [{ format: "topology", url: payload.topology_map_viewer_url, name: "filesystem_map" }];
    }
  }
  if (viewerMode === "auto" && isComposeMode()) {
    return artifacts.filter((artifact) => COMPOSE_MERMAID_NAMES.has(artifact.name));
  }
  return [];
}

function topologyViewerUrl(payload) {
  if (!payload?.topology_map_viewer_url) return null;
  const aispyBase = state.config?.aispy_url || "";
  const aispyQuery = aispyBase ? `&aispy=${encodeURIComponent(aispyBase)}` : "";
  return `${payload.topology_map_viewer_url}${aispyQuery}`;
}

function updateMapOutputLinks(payload) {
  const viewerUrl = topologyViewerUrl(payload);
  if (viewerUrl && els.mapViewerLink) {
    els.mapViewerLink.href = viewerUrl;
    els.mapViewerLink.classList.remove("hidden");
  } else if (els.mapViewerLink) {
    els.mapViewerLink.classList.add("hidden");
  }
  if (payload?.map_url && els.mapDownload) {
    els.mapDownload.href = payload.map_url;
    els.mapDownload.classList.remove("hidden");
  } else if (els.mapDownload) {
    els.mapDownload.classList.add("hidden");
  }
}

async function loadConfig() {
  const config = await fetchJson("/api/config");
  state.config = config;
  els.bindAddress.textContent = `${config.host}:${config.port}`;
  els.repoRoot.textContent = config.repo_root;
  els.dotAvailability.textContent = config.dot_available ? "available" : "missing";
  els.logsLink.href = config.log_url;
  els.logsLink.title = config.log_path;
  els.readmeLink.href = config.readme_url;
  els.readmeLink.title = config.readme_path;
  els.pathInput.value = config.repo_root;
  els.maxFilesInput.value = config.default_max_files;
  els.maxLinesInput.value = config.default_max_lines;
  els.maxFileBytesInput.value = config.default_max_file_bytes;
  els.timeoutSecondsInput.value = config.default_mapper_timeout_seconds;
}

async function browse(path = "") {
  setStatus(els.browseStatus, "Loading directory…");
  const payload = await fetchJson(`/api/browse?path=${encodeURIComponent(path)}`);
  state.currentPath = payload.path;
  els.pathInput.value = payload.path;
  els.browserList.innerHTML = "";

  for (const entry of payload.entries) {
    const item = document.createElement("div");
    item.className = "browser-entry";
    const sizeText = entry.size == null ? "" : `${entry.size.toLocaleString()} bytes`;
    item.innerHTML = `
      <div class="entry-meta">
        <div class="entry-name">${entry.name}</div>
        <div class="entry-kind">${entry.kind}${sizeText ? ` • ${sizeText}` : ""}</div>
      </div>
      <div class="entry-actions"></div>
    `;
    const actions = item.querySelector(".entry-actions");

    if (entry.kind === "directory") {
      const openButton = document.createElement("button");
      openButton.type = "button";
      openButton.textContent = "Open";
      openButton.addEventListener("click", () => browse(entry.path));
      actions.appendChild(openButton);
    } else {
      const previewButton = document.createElement("button");
      previewButton.type = "button";
      previewButton.textContent = "Preview";
      previewButton.addEventListener("click", () => loadFile(entry.path));
      actions.appendChild(previewButton);
    }

    const addButton = document.createElement("button");
    addButton.type = "button";
    addButton.textContent = "Add";
    addButton.addEventListener("click", () => addTarget(entry.path));
    actions.appendChild(addButton);

    els.browserList.appendChild(item);
  }
  const truncated = payload.truncated ? `, truncated at ${payload.max_entries}` : "";
  setStatus(els.browseStatus, `${payload.entries.length} entries${truncated}`);
}

async function loadFile(path) {
  setStatus(els.browseStatus, "Loading file preview…");
  const payload = await fetchJson(`/api/file?path=${encodeURIComponent(path)}`);
  els.previewPath.textContent = payload.path;
  if (payload.binary) {
    els.filePreview.textContent = "Binary file preview is disabled.";
  } else {
    els.filePreview.textContent = payload.content || "";
  }
  setStatus(
    els.browseStatus,
    payload.truncated ? `Preview truncated at ${payload.content.length} characters` : "Preview loaded"
  );
}

function renderArtifactCollection(artifacts, listNode, countNode, emptyMessage) {
  countNode.textContent = `${artifacts.length} files`;
  if (!artifacts.length) {
    listNode.className = "artifact-list empty";
    listNode.textContent = emptyMessage;
    return;
  }

  listNode.className = "artifact-list";
  listNode.innerHTML = "";
  const mapViewer = topologyViewerUrl(state.lastRunPayload);
  for (const artifact of artifacts) {
    const card = document.createElement("div");
    card.className = "artifact-card";
    const links = [];
    const viewerUrl = resolveArtifactViewerUrl(artifact, {
      runId: state.lastRunId,
      payload: state.lastRunPayload,
    });
    const isTopologyJson = artifact.name === "code_topology" || artifact.name === "system_map";
    const isMermaidExport = artifact.format === "mermaid";
    const isPrimaryMap = isTopologyJson || artifact.name === "filesystem_overview";

    if (isPrimaryMap && mapViewer) {
      links.push(`<a href="${mapViewer}" target="_blank" rel="noopener"><strong>system map</strong></a>`);
    } else if (artifact.format === "mermaid" || artifact.format === "svg") {
      links.push(`<a href="${viewerUrl}" target="_blank" rel="noopener">diagram viewer</a>`);
    }

    if (isMermaidExport) {
      links.push(`<a href="${artifact.url}" target="_blank" rel="noopener" download>export .mmd</a>`);
    } else if (isTopologyJson) {
      links.push(`<a href="${artifact.url}" target="_blank" rel="noopener">raw .json</a>`);
    } else {
      links.push(`<a href="${artifact.url}" target="_blank" rel="noopener">raw file</a>`);
    }

    if (artifact.name === "code_topology" || artifact.name === "system_map") {
      const apiUrl = artifact.url.replace(/^\/artifacts\/([^/]+)\/diagrams\/.*$/, "/api/topology/latest?run_id=$1");
      links.push(`<a href="${apiUrl}" target="_blank" rel="noopener">api</a>`);
    }

    const viewerHint = isPrimaryMap && mapViewer
      ? "Opens in browser (HTML viewer) — not a download"
      : isMermaidExport
        ? "Optional export only — use system map link for the product UI"
        : "";

    card.innerHTML = `
      <div class="artifact-title">${artifact.name}</div>
      <div class="artifact-meta">${artifact.kind} • ${artifact.format}</div>
      <div class="artifact-meta">${artifact.description}</div>
      ${viewerHint ? `<div class="artifact-meta">${viewerHint}</div>` : ""}
      <div class="artifact-links">${links.join("")}</div>
    `;
    listNode.appendChild(card);
  }
}

function renderArtifacts(artifacts) {
  renderArtifactCollection(artifacts, els.artifactList, els.artifactCount, "No generated artifacts yet.");
}

function renderDiffArtifacts(artifacts) {
  renderArtifactCollection(artifacts, els.diffArtifactList, els.diffArtifactCount, "No diff artifacts yet.");
}

function loadRunIntoView(run) {
  if (Array.isArray(run.targets)) {
    state.targets = [...run.targets];
    updateTargetList();
  }
  if (run.mode) els.modeSelect.value = run.mode;
  if (run.format) els.formatSelect.value = run.format;
  if (run.map_url) {
    els.mapDownload.href = run.map_url;
    els.mapDownload.classList.remove("hidden");
  }
  if (run.limits) {
    if (run.limits.max_files) els.maxFilesInput.value = run.limits.max_files;
    if (run.limits.max_lines) els.maxLinesInput.value = run.limits.max_lines;
    if (run.limits.max_file_bytes) els.maxFileBytesInput.value = run.limits.max_file_bytes;
  }
  if (run.timeout_seconds) {
    els.timeoutSecondsInput.value = run.timeout_seconds;
  }
  renderArtifacts(run.artifacts || []);
  renderDiffArtifacts(run.diff_artifacts || []);
  state.compareRunId = run.compared_to_run_id || null;
  updateCompareBaseline();
  const suffix = run.diff_error ? ` Diff warning: ${run.diff_error}` : "";
  setStatus(els.runStatus, `Loaded run ${run.run_id}${run.reused ? " (reused)" : ""}.${suffix}`);
}

function maybeOpenGeneratedDiagrams(artifacts, payload) {
  if (!els.autoOpenDiagrams.checked) return;

  const toOpen = pickArtifactsToOpen(artifacts, payload);
  const opened = new Set();
  for (const artifact of toOpen) {
    const url = artifact.format === "topology" || artifact.format === "aispy"
      ? artifact.url
      : resolveArtifactViewerUrl(artifact, { runId: payload?.run_id, payload });
    if (!url || opened.has(url)) continue;
    opened.add(url);
    window.open(url, "_blank", "noopener");
  }
}

async function refreshRuns() {
  const payload = await fetchJson("/api/runs");
  if (!payload.runs.length) {
    els.runsList.className = "runs-list empty";
    els.runsList.textContent = "No runs loaded.";
    return;
  }

  els.runsList.className = "runs-list";
  els.runsList.innerHTML = "";
  for (const run of payload.runs) {
    const card = document.createElement("div");
    card.className = "run-card";
    const combinedArtifacts = [...(run.artifacts || []), ...(run.diff_artifacts || [])];
    const artifactLinks = combinedArtifacts.slice(0, 6).map((artifact) => {
      const href = (artifact.format === "mermaid" || artifact.format === "svg" || TOPOLOGY_ARTIFACT_NAMES.has(artifact.name))
        ? resolveArtifactViewerUrl(artifact, { runId: run.run_id })
        : artifact.url;
      return `<a href="${href}" target="_blank" rel="noopener">${artifact.name}</a>`;
    }).join("");
    card.innerHTML = `
      <div class="run-title">${run.run_id}</div>
      <div class="run-meta">${run.created_at_utc || "unknown"} • ${run.mode} • ${run.format}${run.reused ? " • reused" : ""}</div>
      <div class="run-meta">${(run.targets || []).join(", ")}</div>
      <div class="run-meta">${run.compared_to_run_id ? `Compared to ${run.compared_to_run_id}` : "No baseline"}</div>
      <div class="run-actions"></div>
      <div class="run-artifacts">${artifactLinks || "No artifacts listed."}</div>
    `;
    const actions = card.querySelector(".run-actions");
    const loadButton = document.createElement("button");
    loadButton.type = "button";
    loadButton.textContent = "Load";
    loadButton.addEventListener("click", async () => {
      try {
        loadRunIntoView(run);
        if (run.map_url) {
          const response = await fetch(run.map_url);
          if (!response.ok) {
            throw new Error(`Failed to load map artifact: ${response.status}`);
          }
          const text = await response.text();
          els.mapOutput.textContent = text;
        }
      } catch (error) {
        setStatus(els.runStatus, String(error), true);
      }
    });
    actions.appendChild(loadButton);

    const compareButton = document.createElement("button");
    compareButton.type = "button";
    compareButton.textContent = "Use As Baseline";
    compareButton.addEventListener("click", () => {
      state.compareRunId = run.run_id;
      updateCompareBaseline();
      if (Array.isArray(run.targets)) {
        state.targets = [...run.targets];
        updateTargetList();
      }
      if (run.mode) els.modeSelect.value = run.mode;
      if (run.format) els.formatSelect.value = run.format;
      setStatus(els.runStatus, `Selected baseline ${run.run_id}`);
    });
    actions.appendChild(compareButton);

    if (run.map_url) {
      const openMap = document.createElement("a");
      openMap.href = run.map_url;
      openMap.target = "_blank";
      openMap.rel = "noopener";
      openMap.textContent = "Open Map";
      actions.appendChild(openMap);
    }

    const deleteButton = document.createElement("button");
    deleteButton.type = "button";
    deleteButton.textContent = "Delete";
    deleteButton.addEventListener("click", async () => {
      if (!window.confirm(`Delete run ${run.run_id}?`)) return;
      await fetchJson("/api/runs/delete", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ run_id: run.run_id }),
      });
      if (els.mapDownload.href.includes(run.run_id)) {
        els.mapDownload.classList.add("hidden");
        els.mapDownload.removeAttribute("href");
        els.mapOutput.textContent = "No run yet.";
        renderArtifacts([]);
        renderDiffArtifacts([]);
      }
      if (state.compareRunId === run.run_id) {
        state.compareRunId = null;
        updateCompareBaseline();
      }
      setStatus(els.runStatus, `Deleted run ${run.run_id}`);
      await refreshRuns();
    });
    actions.appendChild(deleteButton);
    els.runsList.appendChild(card);
  }
}

async function runMap() {
  if (!state.targets.length) {
    setStatus(els.runStatus, "Select at least one target first.", true);
    return;
  }

  const request = {
    targets: state.targets,
    mode: els.modeSelect.value,
    format: els.formatSelect.value,
    generate_diagrams: els.generateDiagrams.checked,
    diagram_profile: isComposeMode() ? "demo" : els.diagramProfileSelect.value,
    diagram_format: els.diagramFormatSelect.value,
    render_svg: els.renderSvg.checked,
    max_files: Number(els.maxFilesInput.value),
    max_lines: Number(els.maxLinesInput.value),
    max_file_bytes: Number(els.maxFileBytesInput.value),
    timeout_seconds: Number(els.timeoutSecondsInput.value),
    compare_to_run_id: state.compareRunId,
  };

  setStatus(els.runStatus, "Generating map…");
  els.mapOutput.textContent = "";
  try {
    const payload = await fetchJson("/api/map", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    });

    els.mapOutput.textContent = payload.map_text || "";
    state.lastRunId = payload.run_id;
    state.lastRunPayload = payload;
    updateMapOutputLinks(payload);
    renderArtifacts(payload.artifacts || []);
    renderDiffArtifacts(payload.diff_artifacts || []);
    maybeOpenGeneratedDiagrams(payload.artifacts || [], payload);
    const truncated = payload.map_truncated ? " Output preview truncated." : "";
    const diffWarning = payload.diff_error ? ` Diff warning: ${payload.diff_error}` : "";
    const recoveryNote = payload.recovered
      ? ` Recovered (${payload.recovery_step || "degraded"}).${payload.warning ? ` ${payload.warning}` : ""}`
      : "";
    const viewerUrl = topologyViewerUrl(payload);
    const topologyNote = payload.topology_api_url ? ` Topology: ${payload.topology_fingerprint || "generated"}.` : "";
    const mapHint = viewerUrl
      ? ` Open the HQ map: use “Open system map” above (not .mmd — that file downloads).`
      : "";
    setStatus(
      els.runStatus,
      `${payload.reused ? "Reused" : "Completed"} run ${payload.run_id} in ${payload.timeout_seconds}s budget.${truncated}${diffWarning}${recoveryNote}${topologyNote}${mapHint}`
    );
    await refreshRuns();
  } catch (error) {
    els.mapOutput.textContent = String(error);
    setStatus(els.runStatus, String(error), true);
  }
}

function wireEvents() {
  document.getElementById("browse-go").addEventListener("click", () => browse(els.pathInput.value));
  document.getElementById("browse-up").addEventListener("click", () => {
    const current = els.pathInput.value;
    const parent = current.includes("/") ? current.replace(/\/+$/, "").replace(/\/[^/]*$/, "") || "/" : current;
    browse(parent);
  });
  document.getElementById("add-manual-target").addEventListener("click", () => addTarget(els.pathInput.value));
  document.getElementById("clear-targets").addEventListener("click", () => {
    state.targets = [];
    updateTargetList();
  });
  document.getElementById("clear-compare-run").addEventListener("click", () => {
    state.compareRunId = null;
    updateCompareBaseline();
  });
  document.getElementById("run-map").addEventListener("click", runMap);
  document.getElementById("refresh-runs").addEventListener("click", refreshRuns);
  els.diagramFormatSelect.addEventListener("change", () => {
    const isDot = els.diagramFormatSelect.value === "dot";
    els.renderSvg.disabled = !isDot;
    if (!isDot) {
      els.renderSvg.checked = false;
    }
  });
  els.modeSelect.addEventListener("change", () => {
    const compose = isComposeMode();
    els.diagramProfileSelect.disabled = compose;
    if (compose) {
      els.viewerSelect.value = "aispy-architecture";
    }
  });
}

async function boot() {
  wireEvents();
  await loadConfig();
  await browse(state.config.repo_root);
  await refreshRuns();
  updateTargetList();
  updateCompareBaseline();
}

boot().catch((error) => {
  console.error(error);
  setStatus(els.runStatus, String(error), true);
});
