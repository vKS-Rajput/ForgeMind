"""Graph visualization route -- premium interactive knowledge graph.

Routes:
  GET /graph         -- Serves the interactive D3.js visualization page.
  GET /api/v1/graph/data  -- Already exists in graph.py (D3.js JSON).
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["Visualization"])


@router.get(
    "/graph",
    response_class=HTMLResponse,
    summary="Interactive Knowledge Graph Visualization",
    description="Renders an interactive D3.js force-directed graph of ForgeMind's knowledge.",
)
async def graph_visualization(request: Request) -> HTMLResponse:
    """Serve the interactive D3.js knowledge graph page."""
    return HTMLResponse(content=_GRAPH_HTML, status_code=200)


# ── Inline HTML (no template engine needed) ──────────────────────

_GRAPH_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ForgeMind — Knowledge Graph</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', 'Segoe UI', system-ui, sans-serif;
            background: #080810;
            color: #e0e0e6;
            overflow: hidden;
        }

        /* ── Top Bar ──────────────────────────────── */
        #topbar {
            position: fixed; top: 0; left: 0; right: 0; z-index: 100;
            background: rgba(8, 8, 16, 0.92);
            backdrop-filter: blur(16px);
            border-bottom: 1px solid rgba(99, 102, 241, 0.15);
            padding: 0 24px;
            display: flex; align-items: center; height: 52px; gap: 20px;
        }
        #topbar h1 {
            font-size: 17px; font-weight: 800; letter-spacing: -0.3px;
            background: linear-gradient(135deg, #818cf8, #a78bfa, #c084fc);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            white-space: nowrap;
        }
        .tab-bar {
            display: flex; gap: 2px; margin-left: 12px;
        }
        .tab {
            padding: 6px 14px; border-radius: 6px; font-size: 12px;
            font-weight: 600; cursor: pointer; color: #6b6b80;
            transition: all 0.2s;
        }
        .tab:hover { color: #a78bfa; background: rgba(99, 102, 241, 0.08); }
        .tab.active {
            color: #e0e0f0; background: rgba(99, 102, 241, 0.15);
            border: 1px solid rgba(99, 102, 241, 0.2);
        }
        .stats-bar {
            display: flex; gap: 16px; margin-left: auto;
            font-size: 12px; color: #6b6b80;
        }
        .stats-bar .val { color: #a78bfa; font-weight: 700; }

        /* ── Left Sidebar (Filters) ──────────────── */
        #sidebar {
            position: fixed; left: 0; top: 52px; bottom: 0; width: 220px;
            background: rgba(10, 10, 18, 0.95);
            border-right: 1px solid rgba(99, 102, 241, 0.1);
            padding: 16px; overflow-y: auto; z-index: 90;
            backdrop-filter: blur(12px);
        }
        .sidebar-section {
            margin-bottom: 20px;
        }
        .sidebar-title {
            font-size: 10px; text-transform: uppercase; letter-spacing: 1.2px;
            color: #5a5a6e; font-weight: 700; margin-bottom: 10px;
        }
        .filter-item {
            display: flex; align-items: center; gap: 8px;
            font-size: 12px; color: #b0b0c0; margin-bottom: 7px;
            cursor: pointer; transition: color 0.15s;
        }
        .filter-item:hover { color: #e0e0f0; }
        .filter-item input[type="checkbox"] {
            accent-color: #6366f1; width: 14px; height: 14px;
        }
        .filter-dot {
            width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0;
        }
        .filter-count {
            margin-left: auto; color: #5a5a6e; font-size: 11px;
        }

        /* ── Search ───────────────────────────────── */
        #search-box {
            padding: 0 0 12px 0;
        }
        #search-box input {
            width: 100%; background: rgba(20, 20, 35, 0.9);
            border: 1px solid rgba(99, 102, 241, 0.2);
            border-radius: 8px; padding: 8px 12px;
            color: #e0e0f0; font-size: 12px; outline: none;
        }
        #search-box input:focus {
            border-color: #6366f1;
            box-shadow: 0 0 12px rgba(99, 102, 241, 0.15);
        }
        #search-box input::placeholder { color: #4a4a5e; }

        /* ── Right Inspector Panel ────────────────── */
        #inspector {
            position: fixed; right: 0; top: 52px; bottom: 0; width: 320px;
            background: rgba(10, 10, 18, 0.97);
            border-left: 1px solid rgba(99, 102, 241, 0.1);
            padding: 20px; overflow-y: auto; z-index: 90;
            transform: translateX(100%); transition: transform 0.3s ease;
            backdrop-filter: blur(16px);
        }
        #inspector.open { transform: translateX(0); }
        #inspector-close {
            position: absolute; top: 12px; right: 14px;
            background: none; border: none; color: #6b6b80;
            font-size: 18px; cursor: pointer;
        }
        #inspector-close:hover { color: #e0e0f0; }
        .inspector-name {
            font-size: 18px; font-weight: 700; color: #e0e0f0;
            margin-bottom: 4px;
        }
        .inspector-type {
            font-size: 11px; text-transform: uppercase; letter-spacing: 0.8px;
            font-weight: 600; margin-bottom: 16px; padding: 3px 10px;
            border-radius: 4px; display: inline-block;
        }
        .inspector-section {
            margin-bottom: 16px;
        }
        .inspector-section-title {
            font-size: 10px; text-transform: uppercase; letter-spacing: 1px;
            color: #5a5a6e; font-weight: 700; margin-bottom: 8px;
            border-bottom: 1px solid rgba(99, 102, 241, 0.08);
            padding-bottom: 4px;
        }
        .inspector-stat {
            display: flex; justify-content: space-between;
            font-size: 13px; margin-bottom: 5px;
        }
        .inspector-stat .label { color: #8b8b9e; }
        .inspector-stat .value { color: #e0e0f0; font-weight: 600; }
        .inspector-connection {
            font-size: 12px; color: #b0b0c0; margin-bottom: 4px;
            padding: 4px 8px; border-radius: 4px;
            background: rgba(99, 102, 241, 0.05);
        }
        .inspector-connection .rel {
            color: #7c7cff; font-size: 10px; text-transform: uppercase;
        }

        /* ── Graph Canvas ─────────────────────────── */
        svg { position: fixed; left: 220px; top: 52px; }
        .link { stroke-opacity: 0.4; stroke-width: 1.2; }
        .link.highlighted {
            stroke-opacity: 1; stroke-width: 3;
            filter: drop-shadow(0 0 6px currentColor);
        }
        .link-label {
            font-size: 8px; fill: #4a4a5e; pointer-events: none;
        }
        .node circle {
            stroke-width: 2; cursor: pointer;
            transition: r 0.3s ease, filter 0.2s ease;
        }
        .node circle:hover { filter: brightness(1.4) drop-shadow(0 0 8px currentColor); }
        .node.dimmed circle { opacity: 0.12; }
        .node.dimmed text { opacity: 0.08; }
        .node-label {
            fill: #c0c0d0; pointer-events: none; text-anchor: middle;
        }
        .node.dimmed .node-label { fill: #3a3a4a; }

        /* ── Reasoning animation ──────────────────── */
        .reasoning-pulse {
            animation: pulse-glow 0.6s ease-in-out;
        }
        @keyframes pulse-glow {
            0% { filter: brightness(1); }
            50% { filter: brightness(2) drop-shadow(0 0 16px currentColor); }
            100% { filter: brightness(1.3) drop-shadow(0 0 8px currentColor); }
        }

        /* ── Landing narrative ────────────────────── */
        #narrative {
            position: fixed; top: 52px; left: 220px; right: 0; bottom: 0;
            display: flex; align-items: center; justify-content: center;
            z-index: 80; background: rgba(8, 8, 16, 0.98);
            transition: opacity 0.5s ease;
        }
        #narrative.hidden { opacity: 0; pointer-events: none; }
        .narrative-box {
            text-align: center; max-width: 640px; padding: 40px;
        }
        .narrative-box h2 {
            font-size: 28px; font-weight: 800; line-height: 1.3;
            background: linear-gradient(135deg, #818cf8, #a78bfa, #c084fc);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            margin-bottom: 20px;
        }
        .narrative-box p {
            font-size: 15px; color: #8b8b9e; line-height: 1.7;
            margin-bottom: 28px;
        }
        .demo-flow {
            display: flex; align-items: center; justify-content: center;
            gap: 8px; flex-wrap: wrap; margin-bottom: 32px;
        }
        .demo-step {
            padding: 8px 16px; border-radius: 8px; font-size: 13px;
            font-weight: 600; background: rgba(99, 102, 241, 0.1);
            border: 1px solid rgba(99, 102, 241, 0.15); color: #a78bfa;
        }
        .demo-arrow { color: #4a4a5e; font-size: 18px; }
        .narrative-btn {
            padding: 12px 32px; border-radius: 10px; border: none;
            background: linear-gradient(135deg, #6366f1, #8b5cf6);
            color: white; font-size: 14px; font-weight: 700;
            cursor: pointer; transition: transform 0.2s, box-shadow 0.2s;
        }
        .narrative-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 24px rgba(99, 102, 241, 0.3);
        }
    </style>
</head>
<body>
    <!-- Top Bar -->
    <div id="topbar">
        <h1>ForgeMind</h1>
        <div class="tab-bar">
            <div class="tab active" data-view="all">Graph</div>
            <div class="tab" data-view="asset">Assets</div>
            <div class="tab" data-view="failure">Failures</div>
            <div class="tab" data-view="maintenance">Maintenance</div>
        </div>
        <div class="stats-bar">
            <div>Entities <span class="val" id="stat-nodes">0</span></div>
            <div>Edges <span class="val" id="stat-edges">0</span></div>
            <div>Density <span class="val" id="stat-density">0</span></div>
            <div>Documents <span class="val" id="stat-docs">0</span></div>
        </div>
    </div>

    <!-- Left Sidebar -->
    <div id="sidebar">
        <div id="search-box">
            <input type="text" id="search" placeholder="Search entities..." />
        </div>
        <div class="sidebar-section">
            <div class="sidebar-title">Entity Types</div>
            <div id="filter-list"></div>
        </div>
        <div class="sidebar-section" id="reason-section" style="display:none">
            <div class="sidebar-title">Reasoning</div>
            <button id="reason-btn" style="width:100%;padding:8px;border-radius:8px;border:1px solid rgba(99,102,241,0.2);background:rgba(99,102,241,0.1);color:#a78bfa;font-size:12px;font-weight:600;cursor:pointer;">
                Animate Reasoning Path
            </button>
        </div>
    </div>

    <!-- Right Inspector -->
    <div id="inspector">
        <button id="inspector-close">&times;</button>
        <div class="inspector-name" id="insp-name"></div>
        <div class="inspector-type" id="insp-type"></div>
        <div id="insp-body"></div>
    </div>

    <!-- Landing Narrative -->
    <div id="narrative">
        <div class="narrative-box">
            <h2>ForgeMind transforms maintenance documents into living organizational memory</h2>
            <p>Upload manuals, incident reports, and inspection records. Watch knowledge evolve with each document. Ask questions and get evidence-backed, explainable decisions.</p>
            <div class="demo-flow">
                <div class="demo-step">📄 Manual</div>
                <div class="demo-arrow">→</div>
                <div class="demo-step">⚠️ Incident</div>
                <div class="demo-arrow">→</div>
                <div class="demo-step">🔍 Inspection</div>
                <div class="demo-arrow">→</div>
                <div class="demo-step">🧠 Memory Updated</div>
                <div class="demo-arrow">→</div>
                <div class="demo-step">📊 Decision</div>
            </div>
            <button class="narrative-btn" onclick="dismissNarrative()">Explore Knowledge Graph →</button>
        </div>
    </div>

    <!-- Graph SVG -->
    <svg id="graph"></svg>

    <script>
    // ── Config ──────────────────────────────────────────
    const nodeColors = {
        asset: '#6366f1', component: '#8b5cf6', failure_mode: '#ef4444',
        symptom: '#f59e0b', action: '#10b981', condition: '#06b6d4',
        location: '#ec4899', part: '#64748b'
    };
    const nodeRadius = {
        asset: 22, component: 12, failure_mode: 11, symptom: 11,
        action: 11, condition: 6, location: 8, part: 7
    };
    const nodeFontSize = {
        asset: 13, component: 10, failure_mode: 10, symptom: 10,
        action: 10, condition: 0, location: 9, part: 0
    };
    const edgeColors = {
        has_component: '#3b82f6', has_symptom: '#f59e0b',
        caused_by: '#ef4444', resolves: '#10b981',
        has_parameter: '#8b5cf6', indicates: '#f97316',
        requires_part: '#06b6d4', related_to: '#6b7280',
        component_of: '#3b82f6', manufactured_by: '#64748b',
        located_at: '#ec4899', monitors: '#06b6d4',
        operated_by: '#8b5cf6'
    };

    // ── State ───────────────────────────────────────────
    let allNodes = [], allEdges = [], simulation, nodeElements, linkElements;
    let activeFilters = new Set();
    let selectedNode = null;

    // ── SVG Setup ───────────────────────────────────────
    const svg = d3.select('#graph');
    const g = svg.append('g');
    svg.call(d3.zoom().scaleExtent([0.05, 10])
        .on('zoom', (e) => g.attr('transform', e.transform)));

    function resizeSVG() {
        const w = window.innerWidth - 220;
        const h = window.innerHeight - 52;
        svg.attr('width', w).attr('height', h).attr('viewBox', [0, 0, w, h]);
    }
    resizeSVG();
    window.addEventListener('resize', resizeSVG);

    // ── Narrative ───────────────────────────────────────
    function dismissNarrative() {
        document.getElementById('narrative').classList.add('hidden');
    }

    // ── Load Graph ──────────────────────────────────────
    async function loadGraph() {
        const resp = await fetch('/api/v1/graph/data');
        const data = await resp.json();
        allNodes = data.nodes;
        allEdges = data.edges;

        // Stats
        document.getElementById('stat-nodes').textContent = allNodes.length;
        document.getElementById('stat-edges').textContent = allEdges.length;
        const density = allNodes.length > 0
            ? (allEdges.length / allNodes.length).toFixed(1) : '0';
        document.getElementById('stat-density').textContent = density + 'x';

        // Count documents
        const docs = new Set();
        allNodes.forEach(n => {
            if (n.attributes) {
                if (n.attributes.created_by) docs.add(n.attributes.created_by);
                if (n.attributes.last_updated_by) docs.add(n.attributes.last_updated_by);
            }
        });
        document.getElementById('stat-docs').textContent = docs.size;

        // Build filter checkboxes
        buildFilters();

        // Initially hide conditions and parts (reduce clutter)
        activeFilters.delete('condition');
        activeFilters.delete('part');
        document.querySelectorAll('#filter-list input').forEach(cb => {
            if (cb.dataset.type === 'condition' || cb.dataset.type === 'part') {
                cb.checked = false;
            }
        });

        renderGraph();

        // Show reasoning button if graph has data
        if (allNodes.length > 0) {
            document.getElementById('reason-section').style.display = 'block';
        }

        // Auto-dismiss narrative if graph has data
        if (allNodes.length > 0) {
            setTimeout(() => dismissNarrative(), 800);
        }
    }

    function buildFilters() {
        const counts = {};
        allNodes.forEach(n => {
            counts[n.type] = (counts[n.type] || 0) + 1;
        });
        const list = document.getElementById('filter-list');
        list.innerHTML = '';
        const defaultOn = ['asset','component','failure_mode','symptom','action','location'];
        Object.entries(counts).sort((a,b) => b[1] - a[1]).forEach(([type, count]) => {
            const checked = defaultOn.includes(type);
            if (checked) activeFilters.add(type);
            const color = nodeColors[type] || '#6b7280';
            const label = type.replace(/_/g, ' ');
            list.innerHTML += `
                <label class="filter-item">
                    <input type="checkbox" data-type="${type}" ${checked ? 'checked' : ''} />
                    <div class="filter-dot" style="background:${color}"></div>
                    ${label}
                    <span class="filter-count">${count}</span>
                </label>`;
        });
        list.querySelectorAll('input').forEach(cb => {
            cb.addEventListener('change', () => {
                if (cb.checked) activeFilters.add(cb.dataset.type);
                else activeFilters.delete(cb.dataset.type);
                applyFilters();
            });
        });
    }

    function applyFilters() {
        if (!nodeElements) return;
        const q = document.getElementById('search').value.toLowerCase();
        nodeElements.classed('dimmed', d => {
            if (!activeFilters.has(d.type)) return true;
            if (q && !d.name.toLowerCase().includes(q)) return true;
            return false;
        });
        linkElements.style('opacity', d => {
            const sType = d.source.type || '';
            const tType = d.target.type || '';
            if (!activeFilters.has(sType) || !activeFilters.has(tType)) return 0.03;
            if (q) {
                const sn = (d.source.name || '').toLowerCase();
                const tn = (d.target.name || '').toLowerCase();
                if (!sn.includes(q) && !tn.includes(q)) return 0.03;
            }
            return 0.4;
        });
    }

    // ── Render ───────────────────────────────────────────
    function renderGraph() {
        g.selectAll('*').remove();
        const w = window.innerWidth - 220;
        const h = window.innerHeight - 52;

        // Filter nodes
        const visibleTypes = activeFilters;
        const nodes = allNodes;
        const nodeIds = new Set(nodes.map(n => n.id));
        const edges = allEdges.filter(e => {
            const sid = typeof e.source === 'object' ? e.source.id : e.source;
            const tid = typeof e.target === 'object' ? e.target.id : e.target;
            return nodeIds.has(sid) && nodeIds.has(tid);
        });

        simulation = d3.forceSimulation(nodes)
            .force('link', d3.forceLink(edges).id(d => d.id).distance(90))
            .force('charge', d3.forceManyBody().strength(-200))
            .force('center', d3.forceCenter(w / 2, h / 2))
            .force('collision', d3.forceCollide().radius(d =>
                (nodeRadius[d.type] || 8) + 4));

        // Edges with relationship-type colors
        linkElements = g.append('g').selectAll('line').data(edges).join('line')
            .attr('class', 'link')
            .attr('stroke', d => edgeColors[d.type] || '#3b3b52');

        // Nodes with hierarchy
        nodeElements = g.append('g').selectAll('g').data(nodes).join('g')
            .attr('class', 'node')
            .call(d3.drag()
                .on('start', (e) => { if (!e.active) simulation.alphaTarget(0.3).restart(); e.subject.fx = e.subject.x; e.subject.fy = e.subject.y; })
                .on('drag', (e) => { e.subject.fx = e.x; e.subject.fy = e.y; })
                .on('end', (e) => { if (!e.active) simulation.alphaTarget(0); e.subject.fx = null; e.subject.fy = null; })
            );

        nodeElements.append('circle')
            .attr('r', d => nodeRadius[d.type] || 8)
            .attr('fill', d => nodeColors[d.type] || '#6b7280')
            .attr('stroke', d => d3.color(nodeColors[d.type] || '#6b7280').brighter(0.6))
            .on('click', (event, d) => openInspector(d))
            .on('mouseover', (event, d) => highlightNeighbors(d))
            .on('mouseout', () => clearHighlight());

        nodeElements.append('text')
            .attr('class', 'node-label')
            .attr('dy', d => (nodeRadius[d.type] || 8) + 12)
            .attr('font-size', d => (nodeFontSize[d.type] || 10) + 'px')
            .text(d => {
                const fs = nodeFontSize[d.type];
                if (fs === 0) return '';
                return d.name.length > 22 ? d.name.substring(0, 20) + '...' : d.name;
            });

        simulation.on('tick', () => {
            linkElements
                .attr('x1', d => d.source.x).attr('y1', d => d.source.y)
                .attr('x2', d => d.target.x).attr('y2', d => d.target.y);
            nodeElements.attr('transform', d => `translate(${d.x},${d.y})`);
        });

        applyFilters();
    }

    // ── Highlight neighbors on hover ────────────────────
    function highlightNeighbors(d) {
        const neighborIds = new Set([d.id]);
        allEdges.forEach(e => {
            const sid = typeof e.source === 'object' ? e.source.id : e.source;
            const tid = typeof e.target === 'object' ? e.target.id : e.target;
            if (sid === d.id) neighborIds.add(tid);
            if (tid === d.id) neighborIds.add(sid);
        });
        nodeElements.classed('dimmed', n => !neighborIds.has(n.id));
        linkElements.style('opacity', e => {
            const sid = typeof e.source === 'object' ? e.source.id : e.source;
            const tid = typeof e.target === 'object' ? e.target.id : e.target;
            return (sid === d.id || tid === d.id) ? 0.9 : 0.03;
        });
    }
    function clearHighlight() { applyFilters(); }

    // ── Inspector Panel ─────────────────────────────────
    function openInspector(d) {
        selectedNode = d;
        const panel = document.getElementById('inspector');
        panel.classList.add('open');

        document.getElementById('insp-name').textContent = d.name;
        const typeEl = document.getElementById('insp-type');
        typeEl.textContent = d.type.replace(/_/g, ' ');
        typeEl.style.background = nodeColors[d.type] + '22';
        typeEl.style.color = nodeColors[d.type];

        // Build body
        let html = '';

        // Evidence & confidence
        const evCount = d.attributes?.evidence_count || '1';
        const createdBy = d.attributes?.created_by || 'Unknown';
        const updatedBy = d.attributes?.last_updated_by || '';
        html += `<div class="inspector-section">
            <div class="inspector-section-title">Evidence</div>
            <div class="inspector-stat"><span class="label">Documents</span><span class="value">${evCount}</span></div>
            <div class="inspector-stat"><span class="label">Created by</span><span class="value">${createdBy}</span></div>`;
        if (updatedBy) {
            html += `<div class="inspector-stat"><span class="label">Last updated</span><span class="value">${updatedBy}</span></div>`;
        }
        html += '</div>';

        // Description
        if (d.description) {
            html += `<div class="inspector-section">
                <div class="inspector-section-title">Description</div>
                <div style="font-size:12px;color:#9090a8;line-height:1.5">${d.description}</div>
            </div>`;
        }

        // Connections
        const connections = [];
        allEdges.forEach(e => {
            const sid = typeof e.source === 'object' ? e.source.id : e.source;
            const tid = typeof e.target === 'object' ? e.target.id : e.target;
            if (sid === d.id) {
                const target = allNodes.find(n => n.id === tid);
                if (target) connections.push({ rel: e.type, name: target.name, dir: '→' });
            }
            if (tid === d.id) {
                const source = allNodes.find(n => n.id === sid);
                if (source) connections.push({ rel: e.type, name: source.name, dir: '←' });
            }
        });

        if (connections.length > 0) {
            html += `<div class="inspector-section">
                <div class="inspector-section-title">Connections (${connections.length})</div>`;
            connections.slice(0, 20).forEach(c => {
                html += `<div class="inspector-connection">
                    <span class="rel">${c.rel.replace(/_/g,' ')}</span> ${c.dir} ${c.name}
                </div>`;
            });
            if (connections.length > 20) {
                html += `<div style="font-size:11px;color:#5a5a6e;margin-top:4px">+${connections.length - 20} more</div>`;
            }
            html += '</div>';
        }

        document.getElementById('insp-body').innerHTML = html;
    }

    document.getElementById('inspector-close').addEventListener('click', () => {
        document.getElementById('inspector').classList.remove('open');
        selectedNode = null;
    });

    // ── Search ──────────────────────────────────────────
    document.getElementById('search').addEventListener('input', () => applyFilters());

    // ── View Tabs ───────────────────────────────────────
    const viewFilters = {
        all: null,
        asset: ['asset', 'component', 'part'],
        failure: ['asset', 'component', 'symptom', 'failure_mode', 'action'],
        maintenance: ['asset', 'component', 'action', 'part'],
    };
    document.querySelectorAll('.tab').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            const view = tab.dataset.view;
            const types = viewFilters[view];
            document.querySelectorAll('#filter-list input').forEach(cb => {
                if (types === null) {
                    // All view: restore defaults
                    const defaultOn = ['asset','component','failure_mode','symptom','action','location'];
                    cb.checked = defaultOn.includes(cb.dataset.type);
                } else {
                    cb.checked = types.includes(cb.dataset.type);
                }
                if (cb.checked) activeFilters.add(cb.dataset.type);
                else activeFilters.delete(cb.dataset.type);
            });
            applyFilters();
        });
    });

    // ── Animated Reasoning Path ─────────────────────────
    document.getElementById('reason-btn').addEventListener('click', async () => {
        try {
            const resp = await fetch('/api/v1/reason', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: 'Why is Pump P-101 failing?' })
            });
            const data = await resp.json();
            animateReasoning(data.reasoning_chain);
        } catch (e) { console.error('Reasoning failed:', e); }
    });

    function animateReasoning(chain) {
        // Clear previous highlights
        nodeElements.select('circle').classed('reasoning-pulse', false);
        linkElements.classed('highlighted', false);

        let delay = 0;
        chain.forEach(step => {
            step.evidence.forEach(ev => {
                delay += 400;
                setTimeout(() => {
                    // Highlight source node
                    nodeElements.filter(n => n.name === ev.source_name)
                        .select('circle').classed('reasoning-pulse', true);
                    // Highlight target node
                    nodeElements.filter(n => n.name === ev.target_name)
                        .select('circle').classed('reasoning-pulse', true);
                    // Highlight edge
                    linkElements.filter(e => {
                        const sn = typeof e.source === 'object' ? e.source.name : '';
                        const tn = typeof e.target === 'object' ? e.target.name : '';
                        return (sn === ev.source_name && tn === ev.target_name) ||
                               (sn === ev.target_name && tn === ev.source_name);
                    }).classed('highlighted', true);
                }, delay);
            });
        });

        // Clear after animation
        setTimeout(() => {
            nodeElements.select('circle').classed('reasoning-pulse', false);
            linkElements.classed('highlighted', false);
        }, delay + 2000);
    }

    // ── Init ────────────────────────────────────────────
    loadGraph();
    </script>
</body>
</html>"""
