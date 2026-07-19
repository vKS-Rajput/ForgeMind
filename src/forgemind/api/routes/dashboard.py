"""ForgeMind Dashboard — the product experience.

This replaces the API-first Swagger landing with a clean,
classic dashboard. Judges land here, not on /docs.

Routes:
  GET /              -- The full ForgeMind dashboard.
  POST /api/demo/reset  -- Reset all data for clean demos.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from forgemind.api.state import AppState, create_app_state
from forgemind.shared.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["Dashboard"])


def _get_state(request: Request) -> AppState:
    """Extract the AppState from the FastAPI request."""
    return request.app.state.forgemind  # type: ignore[no-any-return]


@router.post(
    "/api/demo/reset",
    summary="Reset all data for a clean demo",
    description="Clears documents, graph, timeline, and all knowledge. Every demo starts fresh.",
)
async def reset_demo(request: Request) -> dict[str, Any]:
    """Reset all application state for a clean demo."""
    new_state = create_app_state()
    request.app.state.forgemind = new_state
    logger.info("demo_reset", message="All data cleared for clean demo")
    return {"message": "ForgeMind reset. Ready for a fresh demo.", "status": "clean"}


@router.get(
    "/",
    response_class=HTMLResponse,
    summary="ForgeMind Dashboard",
    description="The product experience — upload, ask, decide.",
)
async def dashboard(request: Request) -> HTMLResponse:
    """Serve the ForgeMind dashboard."""
    return HTMLResponse(content=_DASHBOARD_HTML, status_code=200)


# ── The Dashboard ────────────────────────────────────────────────

_DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ForgeMind — Industrial Knowledge Intelligence</title>
    <meta name="description" content="ForgeMind transforms maintenance documents into an evolving organizational memory with explainable reasoning.">
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        /* ── Reset & Base ──────────────────────────── */
        * { margin:0; padding:0; box-sizing:border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #e8e8e8; color: #1a1a1a; font-size: 13px;
        }
        a { color: #0055aa; }
        a:hover { color: #003377; }

        /* ── Title Bar ─────────────────────────────── */
        #titlebar {
            background: #003366; color: white; padding: 8px 16px;
            display: flex; align-items: center; justify-content: space-between;
            border-bottom: 3px solid #001a33;
        }
        #titlebar h1 { font-size: 16px; font-weight: bold; }
        #titlebar .version { font-size: 10px; color: #99ccff; }
        #titlebar .links a {
            color: #99ccff; font-size: 11px; margin-left: 14px; text-decoration: none;
        }
        #titlebar .links a:hover { text-decoration: underline; color: white; }

        /* ── Metrics Strip ─────────────────────────── */
        #metrics {
            display: flex; background: #dde4ec;
            border-bottom: 1px solid #bbb; padding: 4px 16px; gap: 3px;
        }
        .metric {
            flex: 1; text-align: center; padding: 6px 4px;
            background: white; border: 1px solid #bbb; border-radius: 2px;
        }
        .metric .label { font-size: 9px; color: #666; text-transform: uppercase; letter-spacing: 0.5px; }
        .metric .value { font-size: 20px; font-weight: bold; color: #003366; }
        .metric .unit { font-size: 9px; color: #888; }

        /* ── Main Layout ───────────────────────────── */
        #main { display: flex; height: calc(100vh - 90px); }

        /* ── Left Panel ────────────────────────────── */
        #left { flex: 1; display: flex; flex-direction: column; background: white; border-right: 2px solid #bbb; }
        #copilot-header {
            background: #e8eef5; padding: 10px 16px; border-bottom: 1px solid #ccc;
        }
        #copilot-header h2 { font-size: 14px; color: #003366; }
        #copilot-header p { font-size: 11px; color: #555; margin-top: 1px; }

        /* Ask box */
        #ask-box { padding: 8px 16px; background: #f5f6f8; border-bottom: 1px solid #ddd; }
        #ask-form { display: flex; gap: 5px; }
        #ask-input {
            flex: 1; padding: 7px 10px; border: 2px solid #99aabb;
            border-radius: 2px; font-size: 12px; font-family: inherit; background: white;
        }
        #ask-input:focus { border-color: #003366; outline: none; }
        #ask-btn {
            padding: 7px 16px; background: #003366; color: white;
            border: 1px solid #001a33; border-radius: 2px; font-size: 12px;
            font-weight: bold; cursor: pointer; font-family: inherit;
        }
        #ask-btn:hover { background: #004488; }

        /* Samples */
        #samples { padding: 6px 16px; display: flex; flex-wrap: wrap; gap: 4px; }
        .sample {
            font-size: 10px; color: #003366; background: #e8eef5;
            border: 1px solid #b0c4de; border-radius: 2px; padding: 2px 8px; cursor: pointer;
        }
        .sample:hover { background: #d0dced; }

        /* Results area */
        #results { flex: 1; overflow-y: auto; padding: 10px 16px; }

        /* Loading */
        #loading { display: none; padding: 12px 0; }
        .loading-step {
            display: flex; align-items: center; gap: 6px;
            font-size: 11px; color: #555; margin-bottom: 4px;
        }
        .spinner {
            width: 12px; height: 12px; border: 2px solid #ccc;
            border-top-color: #003366; border-radius: 50%;
            animation: spin 0.8s linear infinite;
        }
        @keyframes spin { to { transform: rotate(360deg); } }

        /* Decision Cards */
        .card {
            background: white; border: 1px solid #bbb;
            border-radius: 3px; padding: 10px 12px; margin-bottom: 8px;
        }
        .card-label {
            font-size: 9px; text-transform: uppercase; letter-spacing: 0.8px;
            color: #888; font-weight: bold; margin-bottom: 4px;
            border-bottom: 1px solid #eee; padding-bottom: 3px;
        }
        .card-title { font-size: 13px; font-weight: bold; color: #1a1a1a; margin-bottom: 2px; }
        .card-subtitle { font-size: 11px; color: #555; }

        /* Confidence bar */
        .conf-bar { display: flex; align-items: center; gap: 6px; margin-top: 4px; }
        .conf-track {
            flex: 1; height: 10px; background: #e0e0e0;
            border: 1px solid #bbb; border-radius: 1px; overflow: hidden;
        }
        .conf-fill { height: 100%; }
        .conf-value { font-size: 13px; font-weight: bold; min-width: 36px; }

        /* Badges */
        .badge {
            display: inline-block; padding: 1px 7px; border-radius: 2px;
            font-size: 9px; font-weight: bold; text-transform: uppercase; border: 1px solid;
        }
        .badge-critical { background: #fdd; color: #c00; border-color: #c00; }
        .badge-high { background: #fff3cd; color: #856404; border-color: #856404; }
        .badge-medium { background: #d1ecf1; color: #0c5460; border-color: #0c5460; }
        .badge-low { background: #d4edda; color: #155724; border-color: #155724; }

        /* Evidence */
        .evidence-item {
            font-size: 11px; color: #333; padding: 3px 6px;
            border-left: 3px solid #003366; margin-bottom: 3px; background: #f8f9fb;
        }

        /* Observations */
        .obs-item {
            font-size: 11px; color: #333; padding: 3px 6px;
            background: #f0f4f8; border: 1px solid #d0dced;
            margin-bottom: 3px; border-radius: 2px;
        }
        .obs-item:before { content: "• "; color: #003366; font-weight: bold; }

        /* ── Right Panel ───────────────────────────── */
        #right { width: 320px; display: flex; flex-direction: column; background: #f5f6f8; }

        /* Tabs */
        #sidebar-tabs { display: flex; background: #dde4ec; border-bottom: 1px solid #bbb; }
        .tab-btn {
            flex: 1; padding: 6px; text-align: center; font-size: 10px;
            font-weight: bold; cursor: pointer; border: none;
            background: transparent; color: #555; font-family: inherit;
            border-bottom: 2px solid transparent; text-transform: uppercase;
            letter-spacing: 0.3px;
        }
        .tab-btn.active { color: #003366; background: white; border-bottom-color: #003366; }
        .tab-btn:hover { background: #e8eef5; }

        /* Tab panels */
        .tab-panel { display: none; flex: 1; overflow-y: auto; }
        .tab-panel.active { display: block; }

        /* Upload */
        #tab-upload { padding: 12px; }
        #upload-zone {
            border: 2px dashed #99aabb; border-radius: 3px;
            padding: 24px 16px; text-align: center; cursor: pointer; background: white;
        }
        #upload-zone:hover { border-color: #003366; }
        #upload-zone.dragover { border-color: #003366; background: #e8eef5; }
        #upload-zone .icon { font-size: 24px; margin-bottom: 4px; }
        #upload-zone .text { font-size: 12px; color: #555; }
        #upload-zone .hint { font-size: 10px; color: #888; margin-top: 3px; }
        #upload-status { margin-top: 8px; font-size: 11px; }

        /* Graph mini */
        #tab-graph { padding: 0; }
        #mini-graph-container {
            width: 100%; height: 220px; background: #fafafa;
            border-bottom: 1px solid #ddd; position: relative;
        }
        #mini-graph-container svg { width: 100%; height: 100%; }
        #graph-legend {
            padding: 8px 12px; font-size: 10px; color: #555;
            display: flex; flex-wrap: wrap; gap: 8px;
        }
        .legend-item { display: flex; align-items: center; gap: 3px; }
        .legend-dot { width: 8px; height: 8px; border-radius: 2px; }
        #graph-info { padding: 6px 12px; font-size: 11px; color: #333; }
        #graph-info a { font-size: 11px; }

        /* Feed */
        #tab-feed { padding: 8px 12px; }
        .feed-item {
            padding: 6px 8px; border: 1px solid #ddd;
            background: white; border-radius: 2px; margin-bottom: 4px; font-size: 11px;
        }
        .feed-item .title { font-weight: bold; color: #003366; margin-bottom: 1px; }
        .feed-item .detail { color: #555; }
        .feed-item .conf-change { font-size: 10px; color: #006633; }
        .feed-item .contradiction { font-size: 10px; color: #c00; font-weight: bold; }
        .feed-item .ts { font-size: 9px; color: #999; margin-top: 2px; }

        /* Timeline */
        #tab-timeline { padding: 8px 12px; }
        .tl-event {
            display: flex; gap: 6px; margin-bottom: 5px; font-size: 10px; color: #333;
        }
        .tl-dot {
            width: 8px; height: 8px; border-radius: 50%;
            margin-top: 2px; flex-shrink: 0;
        }
        .tl-dot.created { background: #006633; }
        .tl-dot.strengthened { background: #336699; }
        .tl-dot.contradiction { background: #c00; }
        .tl-dot.updated { background: #cc6600; }
        .tl-conf { font-size: 9px; color: #888; }

        /* Reset button */
        #reset-btn {
            margin: 8px 12px; padding: 6px; text-align: center;
            background: white; border: 1px solid #cc0000; color: #cc0000;
            border-radius: 2px; font-size: 11px; font-weight: bold;
            cursor: pointer; font-family: inherit;
        }
        #reset-btn:hover { background: #fff0f0; }

        /* Empty state */
        .empty-state { text-align: center; padding: 24px; color: #888; font-size: 12px; }
        .empty-state .icon { font-size: 28px; margin-bottom: 6px; }

        /* Status bar */
        #statusbar {
            background: #dde4ec; border-top: 1px solid #bbb; padding: 3px 16px;
            font-size: 10px; color: #555; display: flex; justify-content: space-between;
        }
    </style>
</head>
<body>

<!-- ── Title Bar ──────────────────────────────── -->
<div id="titlebar">
    <div style="display:flex;align-items:center;gap:12px">
        <h1>⚙ ForgeMind</h1>
        <span class="version">v1.0 — Industrial Knowledge Intelligence</span>
    </div>
    <div class="links">
        <a href="/graph">Knowledge Graph</a>
        <a href="/docs">API Reference</a>
    </div>
</div>

<!-- ── Metrics ────────────────────────────────── -->
<div id="metrics">
    <div class="metric"><div class="label">Documents</div><div class="value" id="m-docs">0</div></div>
    <div class="metric"><div class="label">Entities</div><div class="value" id="m-entities">0</div></div>
    <div class="metric"><div class="label">Relationships</div><div class="value" id="m-edges">0</div></div>
    <div class="metric"><div class="label">Events</div><div class="value" id="m-events">0</div></div>
    <div class="metric"><div class="label">Contradictions</div><div class="value" id="m-contradictions">0</div></div>
    <div class="metric"><div class="label">Avg Confidence</div><div class="value" id="m-confidence">—</div></div>
</div>

<!-- ── Main ───────────────────────────────────── -->
<div id="main">

    <!-- Left: Copilot -->
    <div id="left">
        <div id="copilot-header">
            <h2>Decision Intelligence</h2>
            <p>Ask natural language questions. ForgeMind traverses the knowledge graph and produces explainable, evidence-backed decisions.</p>
        </div>
        <div id="ask-box">
            <form id="ask-form" onsubmit="askQuestion(event)">
                <input id="ask-input" type="text" placeholder="e.g. Why is Pump P-101 failing?" autocomplete="off">
                <button id="ask-btn" type="submit">Analyze</button>
            </form>
        </div>
        <div id="samples">
            <span class="sample" onclick="fillQ(this)">Why is Pump P-101 failing?</span>
            <span class="sample" onclick="fillQ(this)">What causes excessive vibration?</span>
            <span class="sample" onclick="fillQ(this)">Recommended actions for bearing failure?</span>
            <span class="sample" onclick="fillQ(this)">What are the symptoms of seal degradation?</span>
        </div>
        <div id="results">
            <div class="empty-state">
                <div class="icon">📋</div>
                <div><b>No queries yet.</b></div>
                <div style="margin-top:4px">Upload documents in the right panel, then ask a question.</div>
                <div style="margin-top:8px;font-size:11px;color:#aaa">
                    ForgeMind will traverse the knowledge graph, discover root causes,<br>
                    assess severity, and recommend prioritized actions — all with full evidence trails.
                </div>
            </div>
        </div>
    </div>

    <!-- Right: Sidebar -->
    <div id="right">
        <div id="sidebar-tabs">
            <button class="tab-btn active" onclick="switchTab('upload')">Upload</button>
            <button class="tab-btn" onclick="switchTab('graph')">Graph</button>
            <button class="tab-btn" onclick="switchTab('feed')">Changes</button>
            <button class="tab-btn" onclick="switchTab('timeline')">Timeline</button>
        </div>

        <!-- Upload Tab -->
        <div id="tab-upload" class="tab-panel active">
            <div id="upload-zone" onclick="document.getElementById('file-input').click()"
                 ondragover="event.preventDefault();this.classList.add('dragover')"
                 ondragleave="this.classList.remove('dragover')"
                 ondrop="handleDrop(event)">
                <div class="icon">📄</div>
                <div class="text">Drop PDF here or click to upload</div>
                <div class="hint">Manuals · Incident Reports · Inspections</div>
            </div>
            <input type="file" id="file-input" accept=".pdf" style="display:none" onchange="uploadFile(this.files[0])">
            <div id="upload-status"></div>
            <div id="doc-list" style="margin-top:10px"></div>
        </div>

        <!-- Mini Graph Tab -->
        <div id="tab-graph" class="tab-panel">
            <div id="mini-graph-container"><svg id="mini-graph"></svg></div>
            <div id="graph-legend"></div>
            <div id="graph-info">
                <a href="/graph">Open full Knowledge Graph →</a>
            </div>
        </div>

        <!-- What Changed Tab -->
        <div id="tab-feed" class="tab-panel">
            <div class="empty-state"><div class="icon">📝</div><div>No changes yet.</div></div>
        </div>

        <!-- Timeline Tab -->
        <div id="tab-timeline" class="tab-panel">
            <div class="empty-state"><div class="icon">🕐</div><div>Timeline appears after ingestion.</div></div>
        </div>

        <button id="reset-btn" onclick="resetDemo()">↺ Reset Demo Data</button>
    </div>
</div>

<!-- ── Status Bar ─────────────────────────────── -->
<div id="statusbar">
    <span id="status-msg">Ready</span>
    <span id="status-time"></span>
</div>

<script>
// ── State ────────────────────────────────────────
let feedItems = [];

// ── Tabs ────────────────────────────────────────
function switchTab(name) {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
    // Find tab button
    const tabs = ['upload','graph','feed','timeline'];
    const idx = tabs.indexOf(name);
    document.querySelectorAll('.tab-btn')[idx].classList.add('active');
    document.getElementById('tab-'+name).classList.add('active');
    // Render mini graph when switching to graph tab
    if (name === 'graph') renderMiniGraph();
}

function fillQ(el) { document.getElementById('ask-input').value = el.textContent; }

// ── Upload ──────────────────────────────────────
function handleDrop(e) {
    e.preventDefault();
    e.currentTarget.classList.remove('dragover');
    const f = e.dataTransfer.files[0];
    if (f) uploadFile(f);
}

async function uploadFile(file) {
    if (!file) return;
    const status = document.getElementById('upload-status');
    status.innerHTML = '<b>⏳ Uploading:</b> ' + file.name + '...';
    setStatus('Uploading ' + file.name + '...');

    const form = new FormData();
    form.append('file', file);

    try {
        const r = await fetch('/api/v1/documents/upload', { method:'POST', body:form });
        const d = await r.json();
        if (!r.ok) {
            status.innerHTML = '<span style="color:#c00">✗ ' + (d.detail||'Upload failed') + '</span>';
            setStatus('Upload failed');
            return;
        }
        status.innerHTML = '<span style="color:#155724">✓ Ingested: ' + (d.title||file.name) + '</span>';
        setStatus('Ingested: ' + (d.title||file.name));

        addFeedItem(d);
        refreshMetrics();
        loadTimeline();
        loadDocList();
    } catch(err) {
        status.innerHTML = '<span style="color:#c00">✗ ' + err.message + '</span>';
        setStatus('Error: ' + err.message);
    }
}

function addFeedItem(d) {
    const feed = document.getElementById('tab-feed');
    const empty = feed.querySelector('.empty-state');
    if (empty) empty.remove();

    const kg = d.knowledge_graph || {};
    const delta = d.knowledge_delta || {};

    let html = '<div class="feed-item">';
    html += '<div class="title">📄 ' + (d.title||'Document') + '</div>';
    
    // Capability analysis badge
    const cap = d.capability || {};
    if (cap.support_level) {
        const badgeColor = cap.support_level === 'full' ? '#007000' : (cap.support_level === 'partial' ? '#b86200' : '#c00');
        const badgeBg = cap.support_level === 'full' ? '#e6ffe6' : (cap.support_level === 'partial' ? '#fff4e6' : '#ffe6e6');
        html += '<div style="margin: 4px 0; font-size: 11px;">';
        html += '<span style="background:'+badgeBg+'; color:'+badgeColor+'; border: 1px solid '+badgeColor+'; padding: 2px 6px; font-weight: bold;">';
        html += (cap.support_level.toUpperCase()) + ' SUPPORT</span> ';
        html += '<span style="color:#555;">Industrial Relevance: ' + Math.round((cap.relevance_score||0)*100) + '%</span>';
        html += '</div>';
    }

    html += '<div class="detail">';
    html += '+' + (kg.entities_created||0) + ' entities, ';
    html += '+' + (kg.relationships_created||0) + ' relationships';
    if (kg.relationships_strengthened > 0) html += ', ' + kg.relationships_strengthened + ' strengthened';
    html += '</div>';

    // Capability Warnings & Recommendations
    if (cap.warnings && cap.warnings.length > 0) {
        cap.warnings.forEach(w => {
            html += '<div class="contradiction" style="background:#fff3cd; color:#856404; border-color:#ffeeba;">⚠ ' + w + '</div>';
        });
    }
    if (cap.recommendations && cap.recommendations.length > 0) {
        html += '<div style="font-size:11px; color:#444; margin-top:3px; background:#f8f9fa; padding:4px; border:1px dashed #ccc;">';
        html += '<b>💡 Recommended Actions:</b><br/>• ' + cap.recommendations.join('<br/>• ') + '</div>';
    }

    // Confidence changes
    const confChanges = delta.confidence_changes || [];
    if (confChanges.length > 0) {
        confChanges.slice(0, 5).forEach(c => {
            const oldPct = Math.round((c.old_confidence||0)*100);
            const newPct = Math.round((c.new_confidence||0)*100);
            html += '<div class="conf-change">↑ ' + (c.entity||'') + ': ' + oldPct + '% → ' + newPct + '%</div>';
        });
    }

    // Contradictions
    const contras = delta.contradictions || [];
    if (contras.length > 0) {
        contras.forEach(c => {
            html += '<div class="contradiction">⚠ Contradiction: ' + (c.description||c.entity||'detected') + '</div>';
        });
    }

    html += '<div class="ts">' + new Date().toLocaleTimeString() + '</div>';
    html += '</div>';

    feed.insertAdjacentHTML('afterbegin', html);
}

// ── Ask ─────────────────────────────────────────
async function askQuestion(e) {
    e.preventDefault();
    const q = document.getElementById('ask-input').value.trim();
    if (!q) return;

    const results = document.getElementById('results');
    results.innerHTML = '<div id="loading" style="display:block">'
        + '<div class="loading-step"><div class="spinner"></div> Identifying focal entity...</div>'
        + '<div class="loading-step"><div class="spinner"></div> Traversing knowledge graph...</div>'
        + '<div class="loading-step"><div class="spinner"></div> Analyzing causes and symptoms...</div>'
        + '<div class="loading-step"><div class="spinner"></div> Compiling evidence chains...</div>'
        + '</div>';
    setStatus('Reasoning: ' + q);

    try {
        const r = await fetch('/api/v1/decide', {
            method: 'POST',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify({query: q})
        });
        const d = await r.json();
        if (!r.ok) {
            results.innerHTML = '<div class="card"><div class="card-label">Error</div>'
                + '<div class="card-subtitle">' + (d.detail||'Request failed') + '</div></div>';
            setStatus('Error');
            return;
        }
        renderDecision(d);
        setStatus('Decision complete: ' + (d.entity_name||q));
    } catch(err) {
        results.innerHTML = '<div class="card"><div class="card-label">Error</div>'
            + '<div class="card-subtitle">' + err.message + '</div></div>';
        setStatus('Error');
    }
}

function renderDecision(d) {
    const results = document.getElementById('results');
    let html = '';

    // ── Decision card ──
    const dec = d.decision || {};
    const sev = dec.severity || 'medium';
    html += '<div class="card">';
    html += '<div class="card-label">Decision — ' + (d.entity_name||'') + ' (' + (d.entity_type||'') + ')</div>';
    html += '<div class="card-title">' + (dec.problem||d.query||'—') + '</div>';
    html += '<span class="badge badge-' + sev + '">' + sev + '</span>';
    const confData = d.confidence_breakdown || {};
    const conf = confData.score || dec.confidence || 0;
    const pct = Math.round(conf * 100);
    const color = pct >= 80 ? '#006633' : pct >= 50 ? '#856404' : '#c00';
    html += '<div class="conf-bar">';
    html += '<div class="conf-track"><div class="conf-fill" style="width:'+pct+'%;background:'+color+'"></div></div>';
    html += '<div class="conf-value" style="color:'+color+'">' + pct + '%</div>';
    html += '</div>';
    if (confData.factors) {
        html += '<div style="font-size:10px;color:#888;margin-top:2px">';
        Object.entries(confData.factors).forEach(([k,v]) => {
            html += k.replace(/_/g,' ') + ': ' + v + ' · ';
        });
        html += '</div>';
    }
    html += '</div>';

    // ── Diagnosis ──
    const diag = d.diagnosis || {};
    const mlc = diag.most_likely_cause || {};
    if (mlc.cause) {
        html += '<div class="card">';
        html += '<div class="card-label">Root Cause Analysis</div>';
        html += '<div class="card-title">' + mlc.cause + '</div>';
        html += '<div class="card-subtitle">Type: ' + (mlc.cause_type||'—') + ' · Evidence: ' + (mlc.evidence_count||0) + ' links</div>';
        if (mlc.supporting_documents && mlc.supporting_documents.length) {
            html += '<div style="margin-top:4px;font-size:10px;color:#555">Sources: ' + mlc.supporting_documents.join(', ') + '</div>';
        }
        if (mlc.evidence_chain && mlc.evidence_chain.length) {
            html += '<div style="margin-top:4px">';
            mlc.evidence_chain.forEach(e => { html += '<div class="evidence-item">' + e + '</div>'; });
            html += '</div>';
        }
        html += '</div>';
    }

    // Other possible causes
    const otherCauses = diag.other_possible_causes || [];
    if (otherCauses.length) {
        html += '<div class="card">';
        html += '<div class="card-label">Other Possible Causes</div>';
        otherCauses.forEach(c => {
            html += '<div style="padding:3px 0;border-bottom:1px solid #eee;font-size:12px">';
            html += '<b>' + (c.cause||'') + '</b> (' + (c.cause_type||'') + ')';
            html += ' — ' + (c.evidence_count||0) + ' evidence links';
            html += '</div>';
        });
        html += '</div>';
    }

    // ── Business Impact ──
    const biz = d.business_impact || {};
    if (Object.keys(biz).length) {
        html += '<div class="card">';
        html += '<div class="card-label">Business Impact</div>';
        Object.entries(biz).forEach(([k,v]) => {
            const label = k.replace(/_/g,' ').replace(/\b\w/g, c=>c.toUpperCase());
            html += '<div style="margin-bottom:3px"><b style="font-size:10px;color:#666">' + label + ':</b> <span style="font-size:12px">' + v + '</span></div>';
        });
        html += '</div>';
    }

    // ── Recommended Actions ──
    const acts = d.recommended_actions || [];
    if (acts.length) {
        html += '<div class="card">';
        html += '<div class="card-label">Recommended Actions (' + acts.length + ')</div>';
        acts.forEach((a,i) => {
            html += '<div style="padding:4px 0;border-bottom:1px solid #eee">';
            html += '<b>' + (i+1) + '. ' + (a.action||'') + '</b>';
            if (a.priority) html += ' <span class="badge badge-' + a.priority + '">' + a.priority + '</span>';
            if (a.resolves) html += '<div style="font-size:10px;color:#555">Resolves: ' + a.resolves + '</div>';
            if (a.evidence) html += '<div style="font-size:10px;color:#888">' + a.evidence + '</div>';
            html += '</div>';
        });
        html += '</div>';
    }

    // ── Reasoning Trace ──
    const trace = d.reasoning_trace || [];
    if (trace.length) {
        html += '<div class="card">';
        html += '<div class="card-label">Reasoning Trace (' + trace.length + ' steps)</div>';
        trace.forEach(s => {
            html += '<div style="font-size:11px;padding:2px 0;border-bottom:1px solid #f0f0f0">';
            html += '<b>Step ' + s.step + ':</b> ' + s.description;
            html += ' <span style="color:#888">(' + s.evidence_count + ' evidence)</span>';
            html += '</div>';
        });
        html += '</div>';
    }

    results.innerHTML = html;
}

// ── Metrics ─────────────────────────────────────
async function refreshMetrics() {
    try {
        // Graph data
        const r = await fetch('/api/v1/graph/data');
        const d = await r.json();
        const nodes = d.nodes || [];
        const edges = d.edges || [];
        document.getElementById('m-entities').textContent = nodes.length;
        document.getElementById('m-edges').textContent = edges.length;

        // Avg confidence
        if (nodes.length) {
            const avg = nodes.reduce((s,n) => s + (n.confidence||0), 0) / nodes.length;
            document.getElementById('m-confidence').textContent = Math.round(avg * 100) + '%';
        }

        // Document count
        try {
            const dr = await fetch('/api/v1/documents/stats');
            const ds = await dr.json();
            document.getElementById('m-docs').textContent = ds.total_documents || 0;
        } catch(e) { /* non-critical */ }

        // Timeline for events/contradictions
        const tr = await fetch('/api/v1/graph/timeline');
        const td = await tr.json();
        const timeline = td.timeline || [];
        document.getElementById('m-events').textContent = timeline.length;
        const contras = timeline.filter(e => (e.event_type||'').includes('contradiction'));
        document.getElementById('m-contradictions').textContent = contras.length;
    } catch(err) { /* metrics are non-critical */ }
}

// ── Document List ───────────────────────────────
async function loadDocList() {
    try {
        const r = await fetch('/api/v1/documents');
        const docs = await r.json();
        const el = document.getElementById('doc-list');
        if (!docs.length) { el.innerHTML = ''; return; }
        let html = '<div style="font-size:10px;color:#888;text-transform:uppercase;font-weight:bold;margin-bottom:4px;border-bottom:1px solid #ddd;padding-bottom:2px">Ingested Documents</div>';
        docs.forEach(d => {
            html += '<div style="font-size:11px;padding:2px 0;border-bottom:1px solid #eee">';
            html += '📄 ' + (d.title||d.filename||'Document');
            html += ' <span style="color:#888">(' + (d.chunk_count||0) + ' chunks)</span>';
            html += '</div>';
        });
        el.innerHTML = html;
    } catch(e) { /* non-critical */ }
}

// ── Mini Graph ──────────────────────────────────
async function renderMiniGraph() {
    try {
        const r = await fetch('/api/v1/graph/data');
        const data = await r.json();
        const nodes = data.nodes || [];
        const edges = data.edges || [];

        if (!nodes.length) {
            document.getElementById('mini-graph-container').innerHTML =
                '<div class="empty-state" style="padding-top:60px"><div class="icon">🔗</div><div>No graph data yet.</div></div>';
            return;
        }

        const colors = {
            asset: '#003366', component: '#336699', failure_mode: '#cc0000',
            symptom: '#cc6600', action: '#006633', condition: '#006699',
            location: '#993366', part: '#555555'
        };
        const radii = {
            asset: 14, component: 8, failure_mode: 7, symptom: 7,
            action: 7, condition: 4, location: 5, part: 4
        };

        const container = document.getElementById('mini-graph-container');
        container.innerHTML = '<svg id="mini-graph"></svg>';
        const svg = d3.select('#mini-graph');
        const w = container.clientWidth;
        const h = container.clientHeight;
        svg.attr('width', w).attr('height', h).attr('viewBox', [0,0,w,h]);
        const g = svg.append('g');

        svg.call(d3.zoom().scaleExtent([0.2, 5])
            .on('zoom', (e) => g.attr('transform', e.transform)));

        const sim = d3.forceSimulation(nodes)
            .force('link', d3.forceLink(edges).id(d => d.id).distance(40))
            .force('charge', d3.forceManyBody().strength(-60))
            .force('center', d3.forceCenter(w/2, h/2))
            .force('collision', d3.forceCollide().radius(d => (radii[d.type]||5) + 2));

        const links = g.append('g').selectAll('line').data(edges).join('line')
            .attr('stroke', '#aaa').attr('stroke-opacity', 0.4).attr('stroke-width', 1);

        const nodeG = g.append('g').selectAll('g').data(nodes).join('g')
            .call(d3.drag()
                .on('start', e => { if(!e.active) sim.alphaTarget(0.3).restart(); e.subject.fx=e.subject.x; e.subject.fy=e.subject.y; })
                .on('drag', e => { e.subject.fx=e.x; e.subject.fy=e.y; })
                .on('end', e => { if(!e.active) sim.alphaTarget(0); e.subject.fx=null; e.subject.fy=null; })
            );

        nodeG.append('circle')
            .attr('r', d => radii[d.type]||5)
            .attr('fill', d => colors[d.type]||'#888')
            .attr('stroke', d => d3.color(colors[d.type]||'#888').brighter(0.4))
            .attr('stroke-width', 1.5);

        nodeG.append('title').text(d => d.name + ' (' + d.type + ')');

        sim.on('tick', () => {
            links.attr('x1',d=>d.source.x).attr('y1',d=>d.source.y).attr('x2',d=>d.target.x).attr('y2',d=>d.target.y);
            nodeG.attr('transform', d => 'translate('+d.x+','+d.y+')');
        });

        // Legend
        const types = {};
        nodes.forEach(n => { types[n.type] = (types[n.type]||0)+1; });
        let legendHtml = '';
        Object.entries(types).sort((a,b)=>b[1]-a[1]).forEach(([t,c]) => {
            legendHtml += '<div class="legend-item"><div class="legend-dot" style="background:'+(colors[t]||'#888')+'"></div>'+t.replace(/_/g,' ')+' ('+c+')</div>';
        });
        document.getElementById('graph-legend').innerHTML = legendHtml;

    } catch(e) { console.error('Mini graph:', e); }
}

// ── Timeline ────────────────────────────────────
async function loadTimeline() {
    try {
        const r = await fetch('/api/v1/graph/timeline');
        const d = await r.json();
        const events = d.timeline || [];
        const el = document.getElementById('tab-timeline');

        if (!events.length) return;

        let html = '';
        const recent = events.slice(-60).reverse();
        recent.forEach(ev => {
            const type = ev.event_type || '';
            let dotClass = 'created';
            if (type.includes('contradiction')) dotClass = 'contradiction';
            else if (type.includes('strengthen')) dotClass = 'strengthened';
            else if (type.includes('update')) dotClass = 'updated';

            html += '<div class="tl-event">';
            html += '<div class="tl-dot ' + dotClass + '"></div>';
            html += '<div><b>' + type.replace(/_/g,' ') + '</b>';
            if (ev.entity_name) html += ': ' + ev.entity_name;
            if (ev.new_confidence) {
                const pct = Math.round(ev.new_confidence * 100);
                html += ' <span class="tl-conf">[' + pct + '% confidence]</span>';
            }
            if (ev.source_document) html += ' <span style="color:#888">— ' + ev.source_document + '</span>';
            html += '</div></div>';
        });
        el.innerHTML = html;
    } catch(err) { /* non-critical */ }
}

// ── Reset ───────────────────────────────────────
async function resetDemo() {
    if (!confirm('Reset all data? This clears everything.')) return;
    await fetch('/api/demo/reset', { method:'POST' });
    location.reload();
}

// ── Status Bar ──────────────────────────────────
function setStatus(msg) {
    document.getElementById('status-msg').textContent = msg;
    document.getElementById('status-time').textContent = new Date().toLocaleTimeString();
}

// ── Init ────────────────────────────────────────
refreshMetrics();
loadDocList();
loadTimeline();
setStatus('Ready');
</script>
</body>
</html>
"""
