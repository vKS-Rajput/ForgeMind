"""Graph visualization route -- serves the interactive D3.js knowledge graph.

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
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', 'Segoe UI', system-ui, sans-serif;
            background: #0a0a0f;
            color: #e0e0e6;
            overflow: hidden;
        }
        #header {
            position: fixed; top: 0; left: 0; right: 0; z-index: 100;
            background: rgba(10, 10, 15, 0.85);
            backdrop-filter: blur(12px);
            border-bottom: 1px solid rgba(99, 102, 241, 0.2);
            padding: 12px 24px;
            display: flex; align-items: center; gap: 16px;
        }
        #header h1 {
            font-size: 18px; font-weight: 700;
            background: linear-gradient(135deg, #818cf8, #6366f1, #a78bfa);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        }
        #header .stats {
            font-size: 13px; color: #8b8b9e;
            display: flex; gap: 16px;
        }
        #header .stats span { color: #a78bfa; font-weight: 600; }
        #legend {
            position: fixed; bottom: 20px; left: 20px; z-index: 100;
            background: rgba(15, 15, 25, 0.9);
            border: 1px solid rgba(99, 102, 241, 0.15);
            border-radius: 12px; padding: 14px 18px;
            backdrop-filter: blur(8px);
        }
        #legend h3 {
            font-size: 12px; text-transform: uppercase; letter-spacing: 1px;
            color: #6b6b80; margin-bottom: 10px;
        }
        .legend-item {
            display: flex; align-items: center; gap: 8px;
            font-size: 12px; color: #b0b0c0; margin-bottom: 5px;
        }
        .legend-dot {
            width: 10px; height: 10px; border-radius: 50%;
        }
        #tooltip {
            position: fixed; z-index: 200;
            background: rgba(20, 20, 35, 0.95);
            border: 1px solid rgba(99, 102, 241, 0.3);
            border-radius: 10px; padding: 12px 16px;
            font-size: 13px; max-width: 300px;
            pointer-events: none; opacity: 0;
            transition: opacity 0.15s ease;
            backdrop-filter: blur(12px);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
        }
        #tooltip .name { font-weight: 700; color: #e0e0f0; font-size: 14px; }
        #tooltip .type {
            font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px;
            color: #8b8bff; margin-top: 2px;
        }
        #tooltip .desc {
            color: #9090a8; margin-top: 6px; line-height: 1.4;
        }
        svg { width: 100vw; height: 100vh; }
        .link {
            stroke-opacity: 0.35;
            stroke-width: 1.2;
        }
        .link-label {
            font-size: 9px;
            fill: #5a5a72;
            pointer-events: none;
        }
        .node circle {
            stroke-width: 2;
            cursor: pointer;
            transition: r 0.2s ease;
        }
        .node circle:hover { filter: brightness(1.3); }
        .node-label {
            font-size: 10px;
            fill: #c0c0d0;
            pointer-events: none;
            text-anchor: middle;
        }
        #search-box {
            position: fixed; top: 12px; right: 24px; z-index: 100;
        }
        #search-box input {
            background: rgba(20, 20, 35, 0.9);
            border: 1px solid rgba(99, 102, 241, 0.25);
            border-radius: 8px; padding: 8px 14px;
            color: #e0e0f0; font-size: 13px; width: 220px;
            outline: none;
        }
        #search-box input:focus {
            border-color: #6366f1;
            box-shadow: 0 0 12px rgba(99, 102, 241, 0.2);
        }
        #search-box input::placeholder { color: #5a5a72; }
    </style>
</head>
<body>
    <div id="header">
        <h1>⚙ ForgeMind Knowledge Graph</h1>
        <div class="stats">
            <div>Entities: <span id="stat-nodes">0</span></div>
            <div>Relationships: <span id="stat-edges">0</span></div>
            <div>Density: <span id="stat-density">0</span></div>
        </div>
    </div>

    <div id="search-box">
        <input type="text" id="search" placeholder="Search entities..." />
    </div>

    <div id="legend">
        <h3>Entity Types</h3>
        <div class="legend-item"><div class="legend-dot" style="background:#6366f1"></div>Asset</div>
        <div class="legend-item"><div class="legend-dot" style="background:#8b5cf6"></div>Component</div>
        <div class="legend-item"><div class="legend-dot" style="background:#ef4444"></div>Failure Mode</div>
        <div class="legend-item"><div class="legend-dot" style="background:#f59e0b"></div>Symptom</div>
        <div class="legend-item"><div class="legend-dot" style="background:#10b981"></div>Action</div>
        <div class="legend-item"><div class="legend-dot" style="background:#06b6d4"></div>Condition</div>
        <div class="legend-item"><div class="legend-dot" style="background:#ec4899"></div>Location</div>
        <div class="legend-item"><div class="legend-dot" style="background:#64748b"></div>Part</div>
    </div>

    <div id="tooltip">
        <div class="name"></div>
        <div class="type"></div>
        <div class="desc"></div>
    </div>

    <svg id="graph"></svg>

    <script>
    const colors = {
        0: '#6366f1',  // asset
        1: '#8b5cf6',  // component
        2: '#ef4444',  // failure_mode
        3: '#f59e0b',  // symptom
        4: '#10b981',  // action
        5: '#06b6d4',  // condition
        6: '#ec4899',  // location
        7: '#64748b',  // part
        8: '#6b7280',  // unknown
    };

    const svg = d3.select('#graph');
    const width = window.innerWidth;
    const height = window.innerHeight;

    svg.attr('viewBox', [0, 0, width, height]);

    const g = svg.append('g');

    // Zoom
    svg.call(d3.zoom()
        .scaleExtent([0.1, 8])
        .on('zoom', (event) => g.attr('transform', event.transform))
    );

    const tooltip = d3.select('#tooltip');

    async function loadGraph() {
        const resp = await fetch('/api/v1/graph/data');
        const data = await resp.json();

        document.getElementById('stat-nodes').textContent = data.nodes.length;
        document.getElementById('stat-edges').textContent = data.edges.length;
        const density = data.nodes.length > 0
            ? (data.edges.length / data.nodes.length).toFixed(1)
            : '0';
        document.getElementById('stat-density').textContent = density + 'x';

        const simulation = d3.forceSimulation(data.nodes)
            .force('link', d3.forceLink(data.edges)
                .id(d => d.id)
                .distance(100))
            .force('charge', d3.forceManyBody().strength(-250))
            .force('center', d3.forceCenter(width / 2, height / 2))
            .force('collision', d3.forceCollide().radius(30));

        // Edges
        const link = g.append('g')
            .selectAll('line')
            .data(data.edges)
            .join('line')
            .attr('class', 'link')
            .attr('stroke', '#3b3b52');

        // Edge labels
        const linkLabel = g.append('g')
            .selectAll('text')
            .data(data.edges)
            .join('text')
            .attr('class', 'link-label')
            .text(d => d.label || d.type);

        // Nodes
        const node = g.append('g')
            .selectAll('g')
            .data(data.nodes)
            .join('g')
            .attr('class', 'node')
            .call(d3.drag()
                .on('start', dragstarted)
                .on('drag', dragged)
                .on('end', dragended));

        node.append('circle')
            .attr('r', d => d.type === 'asset' ? 16 : 9)
            .attr('fill', d => colors[d.group] || colors[8])
            .attr('stroke', d => d3.color(colors[d.group] || colors[8]).brighter(0.5))
            .on('mouseover', (event, d) => {
                tooltip.style('opacity', 1);
                tooltip.select('.name').text(d.name);
                tooltip.select('.type').text(d.type);
                tooltip.select('.desc').text(d.description || '');
                tooltip.style('left', (event.clientX + 15) + 'px');
                tooltip.style('top', (event.clientY - 10) + 'px');
            })
            .on('mousemove', (event) => {
                tooltip.style('left', (event.clientX + 15) + 'px');
                tooltip.style('top', (event.clientY - 10) + 'px');
            })
            .on('mouseout', () => tooltip.style('opacity', 0));

        node.append('text')
            .attr('class', 'node-label')
            .attr('dy', d => d.type === 'asset' ? 28 : 20)
            .text(d => d.name.length > 20 ? d.name.substring(0, 18) + '...' : d.name);

        // Search
        document.getElementById('search').addEventListener('input', (e) => {
            const q = e.target.value.toLowerCase();
            node.select('circle')
                .attr('opacity', d => !q || d.name.toLowerCase().includes(q) ? 1 : 0.15);
            node.select('text')
                .attr('opacity', d => !q || d.name.toLowerCase().includes(q) ? 1 : 0.1);
            link.attr('opacity', d => {
                if (!q) return 1;
                const sn = (d.source.name || '').toLowerCase();
                const tn = (d.target.name || '').toLowerCase();
                return sn.includes(q) || tn.includes(q) ? 1 : 0.05;
            });
        });

        simulation.on('tick', () => {
            link
                .attr('x1', d => d.source.x)
                .attr('y1', d => d.source.y)
                .attr('x2', d => d.target.x)
                .attr('y2', d => d.target.y);
            linkLabel
                .attr('x', d => (d.source.x + d.target.x) / 2)
                .attr('y', d => (d.source.y + d.target.y) / 2);
            node.attr('transform', d => `translate(${d.x},${d.y})`);
        });

        function dragstarted(event) {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            event.subject.fx = event.subject.x;
            event.subject.fy = event.subject.y;
        }
        function dragged(event) {
            event.subject.fx = event.x;
            event.subject.fy = event.y;
        }
        function dragended(event) {
            if (!event.active) simulation.alphaTarget(0);
            event.subject.fx = null;
            event.subject.fy = null;
        }
    }

    loadGraph();
    </script>
</body>
</html>"""
