"""ForgeMind Dashboard — the product experience.

This replaces the API-first Swagger landing with a polished,
product-grade dashboard. Judges land here, not on /docs.

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
    <title>ForgeMind — Industrial Organizational Memory</title>
    <meta name="description" content="ForgeMind transforms maintenance manuals, incident reports, and inspection records into a living organizational memory that explains failures, tracks evolving knowledge, and recommends evidence-backed actions.">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        :root {
            --bg: #06060e; --bg2: #0c0c18; --bg3: #12121f;
            --border: rgba(99,102,241,0.12); --border2: rgba(99,102,241,0.2);
            --text: #e0e0f0; --text2: #8b8b9e; --text3: #5a5a6e;
            --accent: #818cf8; --accent2: #6366f1; --accent3: #a78bfa;
            --green: #10b981; --red: #ef4444; --amber: #f59e0b;
            --cyan: #06b6d4;
        }
        * { margin:0; padding:0; box-sizing:border-box; }
        body { font-family:'Inter',system-ui,sans-serif; background:var(--bg); color:var(--text); overflow-x:hidden; }

        /* ── Metrics Bar ─────────────────────────── */
        #metrics {
            display:flex; gap:2px; padding:8px 16px; background:var(--bg2);
            border-bottom:1px solid var(--border); overflow-x:auto;
        }
        .metric-card {
            flex:1; min-width:100px; text-align:center; padding:10px 8px;
            border-radius:8px; background:rgba(99,102,241,0.04);
        }
        .metric-card .label { font-size:9px; text-transform:uppercase; letter-spacing:1px; color:var(--text3); font-weight:600; }
        .metric-card .value { font-size:22px; font-weight:800; color:var(--accent); margin:2px 0; }
        .metric-card .unit { font-size:10px; color:var(--text2); }

        /* ── Main Layout ─────────────────────────── */
        #app { display:grid; grid-template-columns:1fr 380px; grid-template-rows:1fr; height:calc(100vh - 72px); }

        /* ── Left: Copilot ───────────────────────── */
        #copilot {
            display:flex; flex-direction:column; border-right:1px solid var(--border);
            overflow:hidden;
        }
        #copilot-header {
            padding:20px 24px 0; flex-shrink:0;
        }
        #copilot-header h1 {
            font-size:24px; font-weight:900; letter-spacing:-0.5px;
            background:linear-gradient(135deg,#818cf8,#a78bfa,#c084fc);
            -webkit-background-clip:text; -webkit-text-fill-color:transparent;
        }
        #copilot-header p { font-size:13px; color:var(--text2); margin-top:4px; }

        /* Search */
        #ask-box {
            padding:16px 24px; flex-shrink:0;
        }
        #ask-form { display:flex; gap:8px; }
        #ask-input {
            flex:1; background:var(--bg3); border:1px solid var(--border2);
            border-radius:10px; padding:12px 16px; color:var(--text);
            font-size:14px; outline:none; font-family:inherit;
        }
        #ask-input:focus { border-color:var(--accent2); box-shadow:0 0 20px rgba(99,102,241,0.15); }
        #ask-input::placeholder { color:var(--text3); }
        #ask-btn {
            padding:12px 20px; border-radius:10px; border:none;
            background:linear-gradient(135deg,var(--accent2),#8b5cf6);
            color:white; font-weight:700; font-size:13px; cursor:pointer;
            transition:transform 0.15s,box-shadow 0.15s; font-family:inherit;
        }
        #ask-btn:hover { transform:translateY(-1px); box-shadow:0 6px 20px rgba(99,102,241,0.3); }

        /* Sample questions */
        #samples {
            padding:0 24px 12px; display:flex; flex-wrap:wrap; gap:6px; flex-shrink:0;
        }
        .sample {
            font-size:11px; color:var(--accent3); background:rgba(99,102,241,0.06);
            border:1px solid rgba(99,102,241,0.1); border-radius:6px;
            padding:4px 10px; cursor:pointer; transition:all 0.15s;
        }
        .sample:hover { background:rgba(99,102,241,0.12); border-color:var(--accent); }

        /* Results area */
        #results {
            flex:1; overflow-y:auto; padding:0 24px 24px;
        }

        /* Loading */
        #loading { display:none; padding:20px 0; }
        .loading-step {
            display:flex; align-items:center; gap:10px; margin-bottom:10px;
            font-size:13px; color:var(--text2); opacity:0;
            animation:fadeIn 0.4s ease forwards;
        }
        .loading-bar {
            width:120px; height:4px; background:var(--bg3); border-radius:2px; overflow:hidden;
        }
        .loading-bar-fill {
            height:100%; background:linear-gradient(90deg,var(--accent2),var(--accent3));
            border-radius:2px; animation:loadBar 1.2s ease forwards;
        }
        @keyframes fadeIn { to { opacity:1; } }
        @keyframes loadBar { from { width:0; } to { width:100%; } }

        /* Decision Cards */
        .card {
            background:var(--bg3); border:1px solid var(--border);
            border-radius:14px; padding:18px 20px; margin-bottom:12px;
            transition:border-color 0.2s;
        }
        .card:hover { border-color:var(--border2); }
        .card-label {
            font-size:9px; text-transform:uppercase; letter-spacing:1.2px;
            color:var(--text3); font-weight:700; margin-bottom:8px;
        }
        .card-title { font-size:16px; font-weight:700; color:var(--text); margin-bottom:4px; }
        .card-subtitle { font-size:12px; color:var(--text2); }

        /* Confidence bar */
        .conf-bar { display:flex; align-items:center; gap:10px; margin-top:8px; }
        .conf-track {
            flex:1; height:6px; background:var(--bg); border-radius:3px; overflow:hidden;
        }
        .conf-fill {
            height:100%; border-radius:3px; transition:width 0.8s ease;
        }
        .conf-value { font-size:14px; font-weight:800; min-width:40px; }

        /* Severity badges */
        .badge {
            display:inline-block; padding:3px 10px; border-radius:4px;
            font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:0.5px;
        }
        .badge-critical { background:rgba(239,68,68,0.15); color:var(--red); }
        .badge-high { background:rgba(245,158,11,0.15); color:var(--amber); }
        .badge-medium { background:rgba(6,182,212,0.15); color:var(--cyan); }
        .badge-low { background:rgba(16,185,129,0.15); color:var(--green); }

        /* Action items */
        .action-item {
            display:flex; align-items:flex-start; gap:10px; padding:10px 12px;
            border-radius:8px; margin-bottom:6px; background:rgba(99,102,241,0.03);
        }
        .action-dot {
            width:8px; height:8px; border-radius:50%; margin-top:5px; flex-shrink:0;
        }
        .action-text { font-size:13px; color:var(--text); }
        .action-resolves { font-size:11px; color:var(--text3); margin-top:2px; }

        /* Evidence chain toggle */
        .toggle-btn {
            background:none; border:1px solid var(--border); border-radius:6px;
            padding:6px 12px; color:var(--text2); font-size:11px; cursor:pointer;
            font-family:inherit; margin-top:8px;
        }
        .toggle-btn:hover { border-color:var(--accent); color:var(--accent); }
        .evidence-chain {
            display:none; margin-top:10px; padding:12px; background:var(--bg);
            border-radius:8px; font-size:12px; color:var(--text2); line-height:1.8;
        }
        .evidence-chain.open { display:block; }

        /* ── Right Sidebar ───────────────────────── */
        #sidebar {
            display:flex; flex-direction:column; background:var(--bg2); overflow:hidden;
        }

        /* Tabs */
        #sidebar-tabs {
            display:flex; border-bottom:1px solid var(--border); flex-shrink:0;
        }
        .stab {
            flex:1; padding:10px; text-align:center; font-size:11px;
            font-weight:600; color:var(--text3); cursor:pointer;
            border-bottom:2px solid transparent; transition:all 0.2s;
        }
        .stab:hover { color:var(--text2); }
        .stab.active { color:var(--accent); border-bottom-color:var(--accent); }

        /* Tab content */
        .tab-content { display:none; flex:1; overflow-y:auto; }
        .tab-content.active { display:flex; flex-direction:column; }

        /* Upload panel */
        #upload-panel { padding:16px; }
        #drop-zone {
            border:2px dashed var(--border2); border-radius:12px;
            padding:32px 20px; text-align:center; cursor:pointer;
            transition:all 0.2s; margin-bottom:12px;
        }
        #drop-zone:hover, #drop-zone.dragover {
            border-color:var(--accent); background:rgba(99,102,241,0.05);
        }
        #drop-zone .icon { font-size:28px; margin-bottom:8px; }
        #drop-zone .text { font-size:13px; color:var(--text2); }
        #drop-zone .hint { font-size:11px; color:var(--text3); margin-top:4px; }
        #file-input { display:none; }

        /* Upload history */
        #upload-history { padding:0 16px; }
        .upload-item {
            padding:10px 12px; border-radius:8px; margin-bottom:8px;
            background:var(--bg3); border:1px solid var(--border);
        }
        .upload-item .name { font-size:13px; font-weight:600; color:var(--text); }
        .upload-item .meta { font-size:11px; color:var(--text3); margin-top:2px; }

        /* What Changed cards */
        .delta-card {
            margin-top:8px; padding:10px 12px; border-radius:8px;
            background:var(--bg); border:1px solid var(--border);
        }
        .delta-row {
            display:flex; justify-content:space-between; align-items:center;
            font-size:12px; margin-bottom:4px;
        }
        .delta-label { color:var(--text2); }
        .delta-value { font-weight:700; }
        .delta-value.positive { color:var(--green); }
        .delta-value.warning { color:var(--amber); }
        .delta-value.danger { color:var(--red); }
        .delta-conf {
            display:flex; align-items:center; gap:6px; font-size:11px;
            margin-bottom:3px; color:var(--text2);
        }
        .delta-conf .arrow { color:var(--green); font-weight:700; }
        .delta-contradiction {
            padding:6px 8px; border-radius:6px; margin-top:6px;
            background:rgba(239,68,68,0.06); border-left:3px solid var(--red);
            font-size:11px; color:var(--text2);
        }

        /* Graph panel */
        #graph-panel { position:relative; }
        #graph-panel svg { width:100%; height:100%; }
        #graph-controls {
            position:absolute; bottom:12px; left:12px; right:12px;
            display:flex; gap:6px; z-index:10;
        }
        .graph-btn {
            flex:1; padding:7px; border-radius:8px;
            border:1px solid var(--border); background:rgba(10,10,18,0.9);
            color:var(--text2); font-size:10px; font-weight:600; cursor:pointer;
            font-family:inherit; backdrop-filter:blur(8px);
        }
        .graph-btn:hover { border-color:var(--accent); color:var(--accent); }

        /* Reset button */
        #reset-btn {
            margin:12px 16px; padding:8px; border-radius:8px;
            border:1px solid rgba(239,68,68,0.2); background:rgba(239,68,68,0.05);
            color:var(--red); font-size:11px; font-weight:600; cursor:pointer;
            font-family:inherit; flex-shrink:0;
        }
        #reset-btn:hover { background:rgba(239,68,68,0.1); }

        /* ── Animations ──────────────────────────── */
        .fade-in { animation:fadeIn 0.5s ease forwards; }
        .slide-up { animation:slideUp 0.4s ease forwards; }
        @keyframes slideUp {
            from { opacity:0; transform:translateY(12px); }
            to { opacity:1; transform:translateY(0); }
        }

        /* Node styles for embedded graph */
        .gnode circle { cursor:pointer; transition:filter 0.2s; }
        .gnode circle:hover { filter:brightness(1.5) drop-shadow(0 0 8px currentColor); }
        .gnode text { fill:var(--text2); font-size:8px; pointer-events:none; text-anchor:middle; }
        .glink { stroke-opacity:0.3; }

        /* Scrollbar */
        ::-webkit-scrollbar { width:6px; }
        ::-webkit-scrollbar-track { background:transparent; }
        ::-webkit-scrollbar-thumb { background:var(--border); border-radius:3px; }
    </style>
</head>
<body>

<!-- ══ Metrics Bar ═══════════════════════════════════════ -->
<div id="metrics">
    <div class="metric-card">
        <div class="label">Knowledge</div>
        <div class="value" id="m-entities">0</div>
        <div class="unit">Entities</div>
    </div>
    <div class="metric-card">
        <div class="label">Connections</div>
        <div class="value" id="m-edges">0</div>
        <div class="unit">Relationships</div>
    </div>
    <div class="metric-card">
        <div class="label">Sources</div>
        <div class="value" id="m-docs">0</div>
        <div class="unit">Documents</div>
    </div>
    <div class="metric-card">
        <div class="label">Issues</div>
        <div class="value" id="m-contradictions">0</div>
        <div class="unit">Contradictions</div>
    </div>
    <div class="metric-card">
        <div class="label">Confidence</div>
        <div class="value" id="m-confidence">--</div>
        <div class="unit">Average</div>
    </div>
    <div class="metric-card">
        <div class="label">Actions</div>
        <div class="value" id="m-actions">0</div>
        <div class="unit">Recommendations</div>
    </div>
</div>

<!-- ══ Main App ══════════════════════════════════════════ -->
<div id="app">

    <!-- Left: Copilot -->
    <div id="copilot">
        <div id="copilot-header">
            <h1>ForgeMind</h1>
            <p>Industrial Organizational Memory — ask questions, get evidence-backed decisions</p>
        </div>

        <div id="ask-box">
            <form id="ask-form" onsubmit="askForgeMind(event)">
                <input id="ask-input" type="text" placeholder="Ask ForgeMind..." autocomplete="off" />
                <button id="ask-btn" type="submit">Analyze</button>
            </form>
        </div>

        <div id="samples">
            <div class="sample" onclick="fillQuestion(this)">Why is Pump P-101 failing?</div>
            <div class="sample" onclick="fillQuestion(this)">What changed after the inspection?</div>
            <div class="sample" onclick="fillQuestion(this)">Which component has highest risk?</div>
            <div class="sample" onclick="fillQuestion(this)">Explain bearing failure evidence</div>
            <div class="sample" onclick="fillQuestion(this)">Show maintenance recommendations</div>
        </div>

        <div id="results">
            <!-- Welcome state -->
            <div id="welcome" style="text-align:center;padding:48px 20px;">
                <div style="font-size:48px;margin-bottom:16px;">🧠</div>
                <div style="font-size:18px;font-weight:700;color:var(--text);margin-bottom:8px;">Ready to reason</div>
                <div style="font-size:13px;color:var(--text2);max-width:400px;margin:0 auto;line-height:1.6;">
                    Upload maintenance documents on the right, then ask questions.
                    ForgeMind traverses the knowledge graph to produce evidence-backed decisions.
                </div>
            </div>

            <!-- Loading state -->
            <div id="loading">
                <div class="loading-step" style="animation-delay:0s">
                    <div class="loading-bar"><div class="loading-bar-fill"></div></div>
                    Searching knowledge graph...
                </div>
                <div class="loading-step" style="animation-delay:0.4s">
                    <div class="loading-bar"><div class="loading-bar-fill" style="animation-delay:0.4s"></div></div>
                    Analyzing across documents...
                </div>
                <div class="loading-step" style="animation-delay:0.8s">
                    <div class="loading-bar"><div class="loading-bar-fill" style="animation-delay:0.8s"></div></div>
                    Evaluating contradictions...
                </div>
                <div class="loading-step" style="animation-delay:1.2s">
                    <div class="loading-bar"><div class="loading-bar-fill" style="animation-delay:1.2s"></div></div>
                    Building recommendation...
                </div>
            </div>

            <!-- Decision cards go here -->
            <div id="decision-cards"></div>
        </div>
    </div>

    <!-- Right: Sidebar -->
    <div id="sidebar">
        <div id="sidebar-tabs">
            <div class="stab active" data-tab="graph-panel" onclick="switchTab(this)">Graph</div>
            <div class="stab" data-tab="upload-panel" onclick="switchTab(this)">Upload</div>
            <div class="stab" data-tab="history-panel" onclick="switchTab(this)">History</div>
        </div>

        <div id="graph-panel" class="tab-content active">
            <svg id="mini-graph"></svg>
            <div id="graph-controls">
                <button class="graph-btn" onclick="window.open('/graph','_blank')">Full View</button>
                <button class="graph-btn" id="replay-btn" onclick="replayEvolution()">▶ Replay</button>
            </div>
        </div>

        <div id="upload-panel" class="tab-content">
            <div id="drop-zone" onclick="document.getElementById('file-input').click()">
                <div class="icon">📄</div>
                <div class="text">Drop PDF here or click to upload</div>
                <div class="hint">Supports manuals, incident reports, inspections</div>
            </div>
            <input type="file" id="file-input" accept=".pdf" onchange="uploadFile(this.files[0])" />
            <div id="upload-history"></div>
        </div>

        <div id="history-panel" class="tab-content">
            <div id="timeline-list" style="padding:16px;"></div>
        </div>

        <button id="reset-btn" onclick="resetDemo()">↺ Reset Demo</button>
    </div>
</div>

<script>
// ══ State ═══════════════════════════════════════════════
let uploadCount = 0;
let totalContradictions = 0;

// ══ Metrics ═════════════════════════════════════════════
async function refreshMetrics() {
    try {
        const [statsResp, timelineResp] = await Promise.all([
            fetch('/api/v1/graph/stats'),
            fetch('/api/v1/graph/timeline'),
        ]);
        const stats = await statsResp.json();
        const timeline = await timelineResp.json();

        document.getElementById('m-entities').textContent = stats.total_entities;
        document.getElementById('m-edges').textContent = stats.total_relationships;
        document.getElementById('m-docs').textContent = uploadCount;

        const contradictions = timeline.timeline.filter(e => e.event_type === 'contradiction_detected').length;
        totalContradictions = contradictions;
        document.getElementById('m-contradictions').textContent = contradictions;

        // Avg confidence from confidence_increased events
        const confEvents = timeline.timeline.filter(e =>
            e.event_type === 'confidence_increased' && e.new_confidence > 0);
        if (confEvents.length > 0) {
            const avg = confEvents.reduce((s, e) => s + e.new_confidence, 0) / confEvents.length;
            document.getElementById('m-confidence').textContent = Math.round(avg * 100) + '%';
        }

        // Count action entities
        const actions = stats.entities_by_type?.action || 0;
        document.getElementById('m-actions').textContent = actions;

        refreshMiniGraph();
    } catch (e) { /* server not ready yet */ }
}

// ══ Upload ══════════════════════════════════════════════
const dropZone = document.getElementById('drop-zone');
dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.classList.add('dragover'); });
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
dropZone.addEventListener('drop', (e) => {
    e.preventDefault(); dropZone.classList.remove('dragover');
    if (e.dataTransfer.files.length) uploadFile(e.dataTransfer.files[0]);
});

async function uploadFile(file) {
    if (!file) return;
    const formData = new FormData();
    formData.append('file', file);

    dropZone.innerHTML = '<div class="icon">⏳</div><div class="text">Processing...</div>';

    try {
        const resp = await fetch('/api/v1/documents/upload', { method: 'POST', body: formData });
        const data = await resp.json();
        uploadCount++;

        // Restore drop zone
        dropZone.innerHTML = '<div class="icon">📄</div><div class="text">Drop PDF here or click to upload</div><div class="hint">Supports manuals, incident reports, inspections</div>';

        // Show What Changed
        showWhatChanged(data, file.name);

        // Refresh metrics
        await refreshMetrics();

        // Switch to upload tab to show results
        document.querySelector('.stab[data-tab="upload-panel"]').click();

    } catch (e) {
        dropZone.innerHTML = '<div class="icon">❌</div><div class="text">Upload failed</div>';
        setTimeout(() => {
            dropZone.innerHTML = '<div class="icon">📄</div><div class="text">Drop PDF here or click to upload</div><div class="hint">Supports manuals, incident reports, inspections</div>';
        }, 2000);
    }
}

function showWhatChanged(data, filename) {
    const history = document.getElementById('upload-history');
    const kg = data.knowledge_graph;
    const delta = data.knowledge_delta || {};

    let html = `<div class="upload-item slide-up">
        <div class="name">📄 ${data.title || filename}</div>
        <div class="meta">${kg.total_entities} entities · ${kg.total_relationships} relationships</div>
        <div class="delta-card">`;

    html += `<div class="delta-row"><span class="delta-label">+ Entities</span><span class="delta-value positive">+${kg.entities_created}</span></div>`;
    html += `<div class="delta-row"><span class="delta-label">+ Relationships</span><span class="delta-value positive">+${kg.relationships_created}</span></div>`;

    if (kg.entities_updated > 0) {
        html += `<div class="delta-row"><span class="delta-label">↑ Updated</span><span class="delta-value positive">${kg.entities_updated}</span></div>`;
    }

    // Confidence changes
    if (delta.confidence_changes && delta.confidence_changes.length > 0) {
        delta.confidence_changes.slice(0, 4).forEach(c => {
            const before = Math.round((c.before || 0) * 100);
            const after = Math.round((c.after || 0) * 100);
            html += `<div class="delta-conf">
                ${c.entity} <span class="arrow">${before}% → ${after}%</span>
            </div>`;
        });
    }

    // Contradictions
    if (delta.contradictions && delta.contradictions.length > 0) {
        delta.contradictions.forEach(c => {
            html += `<div class="delta-contradiction">
                ⚠ <strong>${c.fact}</strong><br/>
                ${c.source_a} vs ${c.source_b}<br/>
                ✓ ${c.resolution}
            </div>`;
        });
    }

    html += '</div></div>';
    history.insertAdjacentHTML('afterbegin', html);
}

// ══ Ask ForgeMind ═══════════════════════════════════════
function fillQuestion(el) {
    document.getElementById('ask-input').value = el.textContent;
    document.getElementById('ask-input').focus();
}

async function askForgeMind(event) {
    event.preventDefault();
    const query = document.getElementById('ask-input').value.trim();
    if (!query) return;

    // Hide welcome, show loading
    document.getElementById('welcome').style.display = 'none';
    document.getElementById('decision-cards').innerHTML = '';
    const loading = document.getElementById('loading');
    loading.style.display = 'block';
    // Reset loading animation
    loading.querySelectorAll('.loading-step').forEach(s => {
        s.style.animation = 'none';
        s.offsetHeight;
        s.style.animation = '';
    });

    try {
        const resp = await fetch('/api/v1/decide', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query }),
        });
        const data = await resp.json();

        // Wait for loading animation to feel real
        await new Promise(r => setTimeout(r, 2000));
        loading.style.display = 'none';

        renderDecision(data);
    } catch (e) {
        loading.style.display = 'none';
        document.getElementById('decision-cards').innerHTML =
            '<div class="card"><div class="card-label">Error</div><div class="card-title">Upload documents first, then ask questions.</div></div>';
    }
}

function renderDecision(data) {
    const container = document.getElementById('decision-cards');
    let html = '';

    // 1. Decision card
    const sev = data.decision?.severity || 'unknown';
    const badgeClass = 'badge-' + (sev === 'unknown' ? 'medium' : sev);
    const conf = Math.round((data.decision?.confidence || 0) * 100);
    const confColor = conf >= 80 ? 'var(--green)' : conf >= 50 ? 'var(--amber)' : 'var(--red)';

    html += `<div class="card slide-up">
        <div class="card-label">Decision</div>
        <div class="card-title">${data.decision?.problem || data.query}</div>
        <div style="margin-top:8px"><span class="badge ${badgeClass}">${sev}</span></div>
        <div class="conf-bar">
            <div class="conf-track"><div class="conf-fill" style="width:${conf}%;background:${confColor}"></div></div>
            <div class="conf-value" style="color:${confColor}">${conf}%</div>
        </div>
    </div>`;

    // 2. Root cause card
    const cause = data.diagnosis?.most_likely_cause;
    if (cause) {
        const causeConf = Math.round((cause.confidence || 0) * 100);
        const docs = (cause.supporting_documents || []).join(', ');
        html += `<div class="card slide-up" style="animation-delay:0.1s">
            <div class="card-label">Root Cause</div>
            <div class="card-title">${cause.cause}</div>
            <div class="card-subtitle">${cause.cause_type} · ${cause.evidence_count} evidence sources</div>
            <div class="conf-bar">
                <div class="conf-track"><div class="conf-fill" style="width:${causeConf}%;background:var(--accent)"></div></div>
                <div class="conf-value" style="color:var(--accent)">${causeConf}%</div>
            </div>
            <div style="font-size:11px;color:var(--text3);margin-top:6px;">Supported by: ${docs}</div>
        </div>`;
    }

    // 3. Business impact card
    const impact = data.business_impact;
    if (impact) {
        html += `<div class="card slide-up" style="animation-delay:0.2s">
            <div class="card-label">Business Impact</div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:4px;">
                <div><div style="font-size:11px;color:var(--text3);">Downtime Prevented</div><div style="font-size:14px;font-weight:700;color:var(--amber)">${impact.estimated_downtime_prevented}</div></div>
                <div><div style="font-size:11px;color:var(--text3);">Priority</div><div style="font-size:14px;font-weight:700;color:var(--red)">${impact.maintenance_priority?.split(' -- ')[0] || ''}</div></div>
                <div><div style="font-size:11px;color:var(--text3);">Risk Level</div><div style="font-size:14px;font-weight:700;color:var(--amber)">${impact.risk_level?.split(' -- ')[0] || ''}</div></div>
                <div><div style="font-size:11px;color:var(--text3);">Cost Category</div><div style="font-size:14px;font-weight:700;color:var(--red)">${impact.cost_category?.split(' (')[0] || ''}</div></div>
            </div>
        </div>`;
    }

    // 4. Recommended actions
    const actions = data.recommended_actions || [];
    if (actions.length) {
        html += `<div class="card slide-up" style="animation-delay:0.3s">
            <div class="card-label">Recommended Actions</div>`;
        actions.forEach(a => {
            const dotColor = a.priority === 'critical' ? 'var(--red)' :
                             a.priority === 'high' ? 'var(--amber)' : 'var(--green)';
            const label = a.priority === 'critical' ? 'Immediate Action' :
                          a.priority === 'high' ? 'Recommended' : 'Consider';
            html += `<div class="action-item">
                <div class="action-dot" style="background:${dotColor}"></div>
                <div>
                    <div class="action-text">${a.action}</div>
                    <div class="action-resolves"><span style="color:${dotColor};font-weight:600;">${label}</span> · resolves ${a.resolves}</div>
                </div>
            </div>`;
        });
        html += '</div>';
    }

    // 5. Confidence breakdown card
    const cb = data.confidence_breakdown;
    if (cb) {
        html += `<div class="card slide-up" style="animation-delay:0.4s">
            <div class="card-label">Confidence Breakdown</div>`;
        (cb.factors || []).forEach(f => {
            html += `<div style="font-size:12px;color:var(--text2);margin-bottom:3px;">• ${f}</div>`;
        });
        html += '</div>';
    }

    // 6. Reasoning trace toggle
    const trace = data.reasoning_trace || [];
    if (trace.length) {
        html += `<div class="card slide-up" style="animation-delay:0.5s">
            <div class="card-label">Reasoning</div>
            <button class="toggle-btn" onclick="this.nextElementSibling.classList.toggle('open');this.textContent=this.textContent==='Show Full Reasoning →'?'Hide Reasoning':'Show Full Reasoning →'">Show Full Reasoning →</button>
            <div class="evidence-chain">`;
        trace.forEach(s => {
            html += `<div>Step ${s.step}: ${s.description} (${s.evidence_count} evidence links)</div>`;
        });
        html += '</div></div>';
    }

    container.innerHTML = html;
}

// ══ Mini Graph ══════════════════════════════════════════
const nodeColors = {
    asset:'#6366f1', component:'#8b5cf6', failure_mode:'#ef4444',
    symptom:'#f59e0b', action:'#10b981', condition:'#06b6d4',
    location:'#ec4899', part:'#64748b'
};
const nodeR = { asset:16, component:8, symptom:7, action:7, part:5, condition:4 };

async function refreshMiniGraph() {
    try {
        const resp = await fetch('/api/v1/graph/data');
        const data = await resp.json();
        renderMiniGraph(data);
    } catch(e) {}
}

function renderMiniGraph(data) {
    const svg = d3.select('#mini-graph');
    svg.selectAll('*').remove();
    const rect = document.getElementById('graph-panel').getBoundingClientRect();
    const w = rect.width || 380, h = rect.height || 400;
    svg.attr('viewBox', [0,0,w,h]);
    const g = svg.append('g');
    svg.call(d3.zoom().scaleExtent([0.1,8]).on('zoom', e => g.attr('transform', e.transform)));

    // Filter out conditions for cleaner view
    const nodes = data.nodes.filter(n => n.type !== 'condition' && n.type !== 'part');
    const ids = new Set(nodes.map(n => n.id));
    const edges = data.edges.filter(e => ids.has(e.source) && ids.has(e.target));

    const sim = d3.forceSimulation(nodes)
        .force('link', d3.forceLink(edges).id(d=>d.id).distance(50))
        .force('charge', d3.forceManyBody().strength(-100))
        .force('center', d3.forceCenter(w/2, h/2))
        .force('collision', d3.forceCollide().radius(d => (nodeR[d.type]||6)+3));

    const link = g.append('g').selectAll('line').data(edges).join('line')
        .attr('class','glink').attr('stroke','#2a2a3a').attr('stroke-width',1);

    const node = g.append('g').selectAll('g').data(nodes).join('g').attr('class','gnode');
    node.append('circle')
        .attr('r', d => nodeR[d.type]||6)
        .attr('fill', d => nodeColors[d.type]||'#6b7280')
        .attr('stroke', d => d3.color(nodeColors[d.type]||'#6b7280').brighter(0.5));

    node.filter(d => d.type === 'asset' || d.type === 'component' || d.type === 'symptom')
        .append('text').attr('dy', d => (nodeR[d.type]||6)+10)
        .text(d => d.name.length > 16 ? d.name.substring(0,14)+'..' : d.name);

    sim.on('tick', () => {
        link.attr('x1',d=>d.source.x).attr('y1',d=>d.source.y)
            .attr('x2',d=>d.target.x).attr('y2',d=>d.target.y);
        node.attr('transform', d => `translate(${d.x},${d.y})`);
    });
}

// ══ Replay ══════════════════════════════════════════════
async function replayEvolution() {
    const btn = document.getElementById('replay-btn');
    btn.textContent = '⏸ Playing...';

    try {
        const resp = await fetch('/api/v1/graph/timeline');
        const data = await resp.json();
        const events = data.timeline || [];

        // Group by source_document
        const groups = {};
        events.forEach(e => {
            const doc = e.source_document || 'Unknown';
            if (!groups[doc]) groups[doc] = [];
            groups[doc].push(e);
        });

        // Clear graph
        d3.select('#mini-graph').selectAll('*').remove();
        const rect = document.getElementById('graph-panel').getBoundingClientRect();
        const w = rect.width || 380, h = rect.height || 400;
        const svg = d3.select('#mini-graph').attr('viewBox', [0,0,w,h]);
        const centerG = svg.append('g');

        // Animate document by document
        const docNames = Object.keys(groups);
        for (let i = 0; i < docNames.length; i++) {
            const docName = docNames[i];
            const count = groups[docName].length;

            // Show doc label
            centerG.selectAll('*').remove();
            centerG.append('text')
                .attr('x', w/2).attr('y', h/2 - 20)
                .attr('text-anchor','middle').attr('fill','var(--accent)')
                .attr('font-size','16px').attr('font-weight','700')
                .text(`📄 ${docName}`);
            centerG.append('text')
                .attr('x', w/2).attr('y', h/2 + 10)
                .attr('text-anchor','middle').attr('fill','var(--text2)')
                .attr('font-size','12px')
                .text(`${count} knowledge events`);

            await new Promise(r => setTimeout(r, 1500));
        }

        // Final: show the full graph
        btn.textContent = '▶ Replay';
        await refreshMiniGraph();
    } catch(e) {
        btn.textContent = '▶ Replay';
    }
}

// ══ Tabs ════════════════════════════════════════════════
function switchTab(el) {
    document.querySelectorAll('.stab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
    el.classList.add('active');
    document.getElementById(el.dataset.tab).classList.add('active');
}

// ══ Reset ═══════════════════════════════════════════════
async function resetDemo() {
    if (!confirm('Reset all data? This clears everything for a fresh demo.')) return;
    await fetch('/api/demo/reset', { method: 'POST' });
    uploadCount = 0; totalContradictions = 0;
    document.getElementById('upload-history').innerHTML = '';
    document.getElementById('decision-cards').innerHTML = '';
    document.getElementById('welcome').style.display = 'block';
    document.getElementById('m-entities').textContent = '0';
    document.getElementById('m-edges').textContent = '0';
    document.getElementById('m-docs').textContent = '0';
    document.getElementById('m-contradictions').textContent = '0';
    document.getElementById('m-confidence').textContent = '--';
    document.getElementById('m-actions').textContent = '0';
    d3.select('#mini-graph').selectAll('*').remove();
}

// ══ Init ════════════════════════════════════════════════
refreshMetrics();
</script>
</body>
</html>"""
