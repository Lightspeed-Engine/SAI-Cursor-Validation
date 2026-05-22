(() => {
  const vscode = typeof acquireVsCodeApi === 'function' ? acquireVsCodeApi() : null;
  const state = {
    baseUrl: document.body.dataset.shuftiUrl || 'http://127.0.0.1:3005',
    selectedComponent: null,
    payload: null,
  };

  const $ = (id) => document.getElementById(id);
  const fmt = (value) => Number(value || 0).toLocaleString();

  function heatColor(value) {
    if (value >= 0.75) return '#f97316';
    if (value >= 0.45) return '#38bdf8';
    if (value >= 0.18) return '#2563eb';
    return '#1e3a5f';
  }

  function status(message, isError = false) {
    $('status').textContent = message;
    $('status').className = isError ? 'status error' : 'status';
  }

  async function loadTopology() {
    status('Loading Shufti topology...');
    const url = `${state.baseUrl.replace(/\/$/, '')}/api/topology/latest`;
    const response = await fetch(url);
    const payload = await response.json();
    if (!response.ok || !payload.ok) {
      throw new Error(payload.error || `Topology request failed: ${response.status}`);
    }
    state.payload = payload;
    state.selectedComponent = null;
    render();
    status(`Run ${payload.run_id} · ${payload.summary?.sector_count || 0} components · ${payload.topology_fingerprint || 'no fingerprint'}`);
  }

  function render() {
    const systemMap = state.payload?.system_map || {};
    const nodes = systemMap.nodes || [];
    const edges = systemMap.edges || [];
    const lanes = systemMap.lanes || [];
    const maxY = Math.max(720, ...nodes.map((node) => (node.layout?.y || 0) + (node.layout?.height || 120) + 120));
    const maxX = Math.max(1200, ...nodes.map((node) => (node.layout?.x || 0) + (node.layout?.width || 220) + 120));

    $('canvas').setAttribute('viewBox', `0 0 ${maxX} ${maxY}`);
    $('canvas').innerHTML = `
      <defs>
        <filter id="glow"><feGaussianBlur stdDeviation="3" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
      </defs>
      ${lanes.map((lane) => `<text class="lane-label" x="${92 + lane.order * 320}" y="38">${lane.label}</text>`).join('')}
      ${edges.map(edgePath).join('')}
      ${nodes.map(componentNode).join('')}
    `;
    $('canvas').querySelectorAll('[data-component]').forEach((node) => {
      node.addEventListener('click', () => selectComponent(node.getAttribute('data-component')));
    });
    renderSidebar();
  }

  function edgePath(edge) {
    const nodes = state.payload.system_map.nodes || [];
    const source = nodes.find((node) => node.id === edge.source);
    const target = nodes.find((node) => node.id === edge.target);
    if (!source || !target) return '';
    const sx = source.layout.x + source.layout.width;
    const sy = source.layout.y + source.layout.height / 2;
    const tx = target.layout.x;
    const ty = target.layout.y + target.layout.height / 2;
    const mid = sx + Math.max(70, (tx - sx) / 2);
    return `<path class="edge" d="M ${sx} ${sy} C ${mid} ${sy}, ${mid} ${ty}, ${tx} ${ty}" />
      <text class="edge-label" x="${(sx + tx) / 2}" y="${(sy + ty) / 2 - 6}">${edge.weight || 1}</text>`;
  }

  function componentNode(node) {
    const layout = node.layout || {};
    const metrics = node.metrics || {};
    const fill = heatColor(metrics.static_heat || 0);
    const active = state.selectedComponent === node.drilldown_id ? ' selected' : '';
    return `<g class="component${active}" data-component="${node.drilldown_id}" filter="url(#glow)">
      <rect x="${layout.x}" y="${layout.y}" width="${layout.width}" height="${layout.height}" rx="8" fill="${fill}" />
      <text class="component-title" x="${layout.x + 16}" y="${layout.y + 28}">${escapeXml(node.label)}</text>
      <text class="component-meta" x="${layout.x + 16}" y="${layout.y + 52}">${node.role} · ${fmt(metrics.files)} files</text>
      <text class="component-meta" x="${layout.x + 16}" y="${layout.y + 74}">${fmt(metrics.lines)} lines · ${fmt(metrics.stubs)} stubs</text>
      <circle cx="${layout.x + layout.width - 22}" cy="${layout.y + 24}" r="7" fill="#020617" stroke="#93c5fd" />
    </g>`;
  }

  function selectComponent(id) {
    state.selectedComponent = id;
    render();
    vscode?.postMessage({ type: 'component:selected', id });
  }

  function renderSidebar() {
    const topology = state.payload?.topology || {};
    const drilldowns = topology.views?.component_drilldowns || {};
    const selected = state.selectedComponent
      ? drilldowns[state.selectedComponent]
      : Object.values(drilldowns)[0];
    if (!selected) {
      $('sidebar').innerHTML = '<h2>No component selected</h2>';
      return;
    }
    const files = selected.files || [];
    $('sidebar').innerHTML = `
      <h2>${escapeXml(selected.label || selected.component_id)}</h2>
      <div class="pill-row">
        <span>${selected.role || 'component'}</span>
        <span>${fmt(selected.summary?.lines)} lines</span>
        <span>${fmt(selected.summary?.files)} files</span>
      </div>
      <section>
        <h3>Live Slots</h3>
        <div class="stream-box">Braid streams, AISpy agents, xterm/log panes attach here by component id.</div>
      </section>
      <section>
        <h3>Files</h3>
        <div class="file-list">${files.slice(0, 24).map((file) => `
          <div class="file-row">
            <strong>${escapeXml(file.path || '')}</strong>
            <span>${fmt(file.lines)} lines · ${fmt(file.dependency_touch_count)} links</span>
          </div>`).join('')}</div>
      </section>
    `;
  }

  function escapeXml(value) {
    return String(value ?? '').replace(/[<>&"]/g, (char) => ({
      '<': '&lt;', '>': '&gt;', '&': '&amp;', '"': '&quot;',
    })[char]);
  }

  $('refresh').addEventListener('click', () => loadTopology().catch((error) => status(error.message, true)));
  loadTopology().catch((error) => status(error.message, true));
})();
