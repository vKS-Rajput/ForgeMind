"""Graph visualization route -- classic interactive knowledge graph.

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


# ── Inline HTML ──────────────────────────────────────────────────

_GRAPH_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ForgeMind — Knowledge Graph</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        * { margin:0; padding:0; box-sizing:border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #e8e8e8; color: #1a1a1a; font-size: 14px;
            overflow: hidden;
        }

        /* ── Top Bar ──────────────────────────────── */
        #topbar {
            background: #003366; color: white; padding: 0 16px;
            display: flex; align-items: center; height: 42px; gap: 16px;
            border-bottom: 3px solid #001a33;
        }
        #topbar h1 { font-size: 16px; font-weight: bold; white-space: nowrap; }
        .tab-bar { display: flex; gap: 2px; margin-left: 10px; }
        .tab {
            padding: 5px 12px; font-size: 12px; font-weight: bold;
            cursor: pointer; color: #99ccff; background: transparent;
            border: 1px solid transparent; border-radius: 2px;
        }
        .tab:hover { background: rgba(255,255,255,0.1); }
        .tab.active { color: white; background: #004488; border-color: #006699; }
        .stats-bar {
            display: flex; gap: 14px; margin-left: auto;
            font-size: 11px; color: #99ccff;
        }
        .stats-bar .val { color: white; font-weight: bold; }
        .nav-links { margin-left: 16px; }
        .nav-links a { color: #99ccff; font-size: 11px; margin-left: 12px; text-decoration: none; }
        .nav-links a:hover { text-decoration: underline; color: white; }

        /* ── Left Sidebar ─────────────────────────── */
        #sidebar {
            position: fixed; left: 0; top: 42px; bottom: 0; width: 200px;
            background: #f0f0f0; border-right: 2px solid #bbb;
            padding: 10px; overflow-y: auto;
        }
        .sidebar-title {
            font-size: 10px; text-transform: uppercase; letter-spacing: 0.8px;
            color: #666; font-weight: bold; margin-bottom: 6px; margin-top: 8px;
            border-bottom: 1px solid #ccc; padding-bottom: 3px;
        }
        .filter-item {
            display: flex; align-items: center; gap: 6px;
            font-size: 12px; color: #333; margin-bottom: 4px; cursor: pointer;
        }
        .filter-item input[type="checkbox"] { width: 14px; height: 14px; }
        .filter-dot { width: 10px; height: 10px; border-radius: 2px; flex-shrink: 0; }
        .filter-count { margin-left: auto; color: #888; font-size: 11px; }
        #search-box { padding: 0 0 8px 0; }
        #search-box input {
            width: 100%; border: 2px solid #99aabb; border-radius: 3px;
            padding: 6px 8px; font-size: 12px; background: white;
        }
        #search-box input:focus { border-color: #003366; outline: none; }
        #reason-btn {
            width: 100%; padding: 7px; border: 1px solid #003366;
            background: #e8eef5; color: #003366; font-size: 11px;
            font-weight: bold; cursor: pointer; border-radius: 3px;
            margin-top: 8px;
        }
        #reason-btn:hover { background: #d0dced; }

        /* ── Right Inspector ──────────────────────── */
        #inspector {
            position: fixed; right: 0; top: 42px; bottom: 0; width: 280px;
            background: white; border-left: 2px solid #bbb;
            padding: 12px; overflow-y: auto;
            transform: translateX(100%); transition: transform 0.2s ease;
        }
        #inspector.open { transform: translateX(0); }
        #inspector-close {
            position: absolute; top: 8px; right: 10px;
            background: none; border: none; color: #999; font-size: 18px; cursor: pointer;
        }
        #inspector-close:hover { color: #333; }
        .inspector-name { font-size: 16px; font-weight: bold; color: #003366; margin-bottom: 4px; }
        .inspector-type {
            font-size: 10px; text-transform: uppercase; letter-spacing: 0.5px;
            font-weight: bold; margin-bottom: 12px; padding: 2px 8px;
            border-radius: 2px; display: inline-block; border: 1px solid;
        }
        .inspector-section { margin-bottom: 12px; }
        .inspector-section-title {
            font-size: 10px; text-transform: uppercase; letter-spacing: 0.8px;
            color: #888; font-weight: bold; margin-bottom: 5px;
            border-bottom: 1px solid #eee; padding-bottom: 3px;
        }
        .inspector-stat {
            display: flex; justify-content: space-between;
            font-size: 12px; margin-bottom: 3px;
        }
        .inspector-stat .label { color: #666; }
        .inspector-stat .value { color: #1a1a1a; font-weight: bold; }
        .inspector-connection {
            font-size: 11px; color: #333; margin-bottom: 3px;
            padding: 3px 6px; background: #f8f9fb; border-left: 3px solid #003366;
        }
        .inspector-connection .rel {
            color: #0055aa; font-size: 10px; text-transform: uppercase; font-weight: bold;
        }

        /* ── Graph Canvas ─────────────────────────── */
        svg { position: fixed; left: 200px; top: 42px; background: #fafafa; }
        .link { stroke-opacity: 0.5; stroke-width: 1.5; }
        .link.highlighted { stroke-opacity: 1; stroke-width: 3; }
        .node circle { stroke-width: 2; cursor: pointer; }
        .node circle:hover { filter: brightness(1.2); }
        .node.dimmed circle { opacity: 0.1; }
        .node.dimmed text { opacity: 0.05; }
        .node-label { fill: #333; pointer-events: none; text-anchor: middle; font-weight: 500; }
        .node.dimmed .node-label { fill: #ccc; }

        /* ── Reasoning animation ──────────────────── */
        .reasoning-pulse { animation: pulse-glow 0.6s ease-in-out; }
        @keyframes pulse-glow {
            0% { filter: brightness(1); }
            50% { filter: brightness(1.5) drop-shadow(0 0 8px currentColor); }
            100% { filter: brightness(1.2); }
        }

        /* ── Landing Narrative ────────────────────── */
        #narrative {
            position: fixed; top: 42px; left: 200px; right: 0; bottom: 0;
            display: flex; align-items: center; justify-content: center;
            z-index: 80; background: rgba(240,240,240,0.97);
            transition: opacity 0.3s ease;
        }
        #narrative.hidden { opacity: 0; pointer-events: none; }
        .narrative-box { text-align: center; max-width: 550px; padding: 30px; }
        .narrative-box h2 { font-size: 22px; font-weight: bold; color: #003366; margin-bottom: 16px; }
        .narrative-box p { font-size: 14px; color: #555; line-height: 1.6; margin-bottom: 20px; }
        .demo-flow { display: flex; align-items: center; justify-content: center; gap: 6px; flex-wrap: wrap; margin-bottom: 24px; }
        .demo-step {
            padding: 6px 14px; border: 1px solid #99aabb; border-radius: 3px;
            font-size: 12px; font-weight: bold; background: white; color: #003366;
        }
        .demo-arrow { color: #888; font-size: 16px; }
        .narrative-btn {
            padding: 10px 28px; border: 1px solid #001a33; border-radius: 3px;
            background: #003366; color: white; font-size: 13px; font-weight: bold;
            cursor: pointer;
        }
        .narrative-btn:hover { background: #004488; }
    </style>
</head>
<body>
    <!-- Top Bar -->
    <div id="topbar">
        <h1>⚙ ForgeMind — Knowledge Graph</h1>
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
        </div>
        <div class="nav-links">
            <a href="/">Dashboard</a>
            <a href="/docs">API Docs</a>
        </div>
    </div>

    <!-- Left Sidebar -->
    <div id="sidebar">
        <div id="search-box">
            <input type="text" id="search" placeholder="Search entities..." />
        </div>
        <div class="sidebar-title">Entity Types</div>
        <div id="filter-list"></div>
        <div id="reason-section" style="display:none">
            <div class="sidebar-title">Reasoning</div>
            <button id="reason-btn">▶ Animate Reasoning Path</button>
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
            <h2>ForgeMind Knowledge Graph</h2>
            <p>Upload maintenance documents and watch ForgeMind build a live knowledge graph. Each document adds entities, relationships, and evolving confidence.</p>
            <div class="demo-flow">
                <div class="demo-step">📄 Manual</div>
                <div class="demo-arrow">→</div>
                <div class="demo-step">⚠️ Incident</div>
                <div class="demo-arrow">→</div>
                <div class="demo-step">🔍 Inspection</div>
                <div class="demo-arrow">→</div>
                <div class="demo-step">🧠 Memory</div>
            </div>
            <button class="narrative-btn" onclick="dismissNarrative()">Explore Graph →</button>
        </div>
    </div>

    <!-- Graph SVG -->
    <svg id="graph"></svg>

    <script>
    // ── Config ──────────────────────────────────────────
    const nodeColors = {
        asset: '#003366', component: '#336699', failure_mode: '#cc0000',
        symptom: '#cc6600', action: '#006633', condition: '#006699',
        location: '#993366', part: '#555555'
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
        has_component: '#336699', has_symptom: '#cc6600',
        caused_by: '#cc0000', resolves: '#006633',
        has_parameter: '#6633aa', indicates: '#cc6600',
        requires_part: '#006699', related_to: '#888888',
        component_of: '#336699', manufactured_by: '#555555',
        located_at: '#993366', monitors: '#006699',
        operated_by: '#6633aa'
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
        const w = window.innerWidth - 200;
        const h = window.innerHeight - 42;
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

        document.getElementById('stat-nodes').textContent = allNodes.length;
        document.getElementById('stat-edges').textContent = allEdges.length;
        const density = allNodes.length > 0
            ? (allEdges.length / allNodes.length).toFixed(1) : '0';
        document.getElementById('stat-density').textContent = density + 'x';

        buildFilters();
        activeFilters.delete('condition');
        activeFilters.delete('part');
        document.querySelectorAll('#filter-list input').forEach(cb => {
            if (cb.dataset.type === 'condition' || cb.dataset.type === 'part') cb.checked = false;
        });

        renderGraph();

        if (allNodes.length > 0) {
            document.getElementById('reason-section').style.display = 'block';
            setTimeout(() => dismissNarrative(), 800);
        }
    }

    function buildFilters() {
        const counts = {};
        allNodes.forEach(n => { counts[n.type] = (counts[n.type] || 0) + 1; });
        const list = document.getElementById('filter-list');
        list.innerHTML = '';
        const defaultOn = ['asset','component','failure_mode','symptom','action','location'];
        Object.entries(counts).sort((a,b) => b[1] - a[1]).forEach(([type, count]) => {
            const checked = defaultOn.includes(type);
            if (checked) activeFilters.add(type);
            const color = nodeColors[type] || '#888';
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
            return 0.5;
        });
    }

    // ── Render ───────────────────────────────────────────
    function renderGraph() {
        g.selectAll('*').remove();
        const w = window.innerWidth - 200;
        const h = window.innerHeight - 42;

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
            .force('collision', d3.forceCollide().radius(d => (nodeRadius[d.type] || 8) + 4));

        linkElements = g.append('g').selectAll('line').data(edges).join('line')
            .attr('class', 'link')
            .attr('stroke', d => edgeColors[d.type] || '#aaa');

        nodeElements = g.append('g').selectAll('g').data(nodes).join('g')
            .attr('class', 'node')
            .call(d3.drag()
                .on('start', (e) => { if (!e.active) simulation.alphaTarget(0.3).restart(); e.subject.fx = e.subject.x; e.subject.fy = e.subject.y; })
                .on('drag', (e) => { e.subject.fx = e.x; e.subject.fy = e.y; })
                .on('end', (e) => { if (!e.active) simulation.alphaTarget(0); e.subject.fx = null; e.subject.fy = null; })
            );

        nodeElements.append('circle')
            .attr('r', d => nodeRadius[d.type] || 8)
            .attr('fill', d => nodeColors[d.type] || '#888')
            .attr('stroke', d => d3.color(nodeColors[d.type] || '#888').brighter(0.5))
            .on('click', (event, d) => openInspector(d))
            .on('mouseover', (event, d) => highlightNeighbors(d))
            .on('mouseout', () => clearHighlight());

        nodeElements.append('text')
            .attr('class', 'node-label')
            .attr('dy', d => (nodeRadius[d.type] || 8) + 14)
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

    // ── Highlight neighbors ─────────────────────────────
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
        const tc = nodeColors[d.type] || '#888';
        typeEl.style.background = tc + '18';
        typeEl.style.color = tc;
        typeEl.style.borderColor = tc;

        let html = '';
        const evCount = d.attributes?.evidence_count || '1';
        const createdBy = d.attributes?.created_by || 'Unknown';
        const updatedBy = d.attributes?.last_updated_by || '';
        html += '<div class="inspector-section">';
        html += '<div class="inspector-section-title">Evidence</div>';
        html += '<div class="inspector-stat"><span class="label">Documents</span><span class="value">' + evCount + '</span></div>';
        html += '<div class="inspector-stat"><span class="label">Created by</span><span class="value">' + createdBy + '</span></div>';
        if (updatedBy) html += '<div class="inspector-stat"><span class="label">Last updated</span><span class="value">' + updatedBy + '</span></div>';
        html += '</div>';

        if (d.description) {
            html += '<div class="inspector-section"><div class="inspector-section-title">Description</div>';
            html += '<div style="font-size:12px;color:#555;line-height:1.5">' + d.description + '</div></div>';
        }

        const connections = [];
        allEdges.forEach(e => {
            const sid = typeof e.source === 'object' ? e.source.id : e.source;
            const tid = typeof e.target === 'object' ? e.target.id : e.target;
            if (sid === d.id) { const t = allNodes.find(n => n.id === tid); if (t) connections.push({rel:e.type,name:t.name,dir:'→'}); }
            if (tid === d.id) { const s = allNodes.find(n => n.id === sid); if (s) connections.push({rel:e.type,name:s.name,dir:'←'}); }
        });

        if (connections.length > 0) {
            html += '<div class="inspector-section"><div class="inspector-section-title">Connections (' + connections.length + ')</div>';
            connections.slice(0, 20).forEach(c => {
                html += '<div class="inspector-connection"><span class="rel">' + c.rel.replace(/_/g,' ') + '</span> ' + c.dir + ' ' + c.name + '</div>';
            });
            if (connections.length > 20) html += '<div style="font-size:10px;color:#888;margin-top:3px">+' + (connections.length-20) + ' more</div>';
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
        nodeElements.select('circle').classed('reasoning-pulse', false);
        linkElements.classed('highlighted', false);

        let delay = 0;
        chain.forEach(step => {
            step.evidence.forEach(ev => {
                delay += 400;
                setTimeout(() => {
                    nodeElements.filter(n => n.name === ev.source_name)
                        .select('circle').classed('reasoning-pulse', true);
                    nodeElements.filter(n => n.name === ev.target_name)
                        .select('circle').classed('reasoning-pulse', true);
                    linkElements.filter(e => {
                        const sn = typeof e.source === 'object' ? e.source.name : '';
                        const tn = typeof e.target === 'object' ? e.target.name : '';
                        return (sn === ev.source_name && tn === ev.target_name) ||
                               (sn === ev.target_name && tn === ev.source_name);
                    }).classed('highlighted', true);
                }, delay);
            });
        });

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
