# ForgeMind Interactive Demo Script

This guide walks through the exact 3-step demonstration sequence showcasing Universal Ingestion, Knowledge Evolution, Contradiction Resolution, and Decision Intelligence.

---

## Prerequisites & Setup

1. Start the server:
   ```bash
   uv run uvicorn forgemind.api.app:create_app --factory --reload --port 8000
   ```
2. Open a browser to **`http://localhost:8000/`**.
3. Locate the demonstration PDF files in the repository:
   - `data/demo/pump_p101_manual.pdf`
   - `data/demo/incident_report_IR-2024-0847.pdf`
   - `data/demo/inspection_INS-2024-0392.pdf`
4. If there is existing data, click the **↺ Reset Demo** button at the bottom of the sidebar.

---

## The Demo Sequence

### Step 1: Upload the OEM Maintenance Manual
- **Action**: Drag and drop `pump_p101_manual.pdf` into the upload zone on the sidebar (or click to upload).
- **Under the Hood**:
  - The text is extracted and chunked.
  - Entities (e.g. `Pump P-101`, `Bearing`, `Impeller`) and relationships (`has_component`, `has_parameter`) are built.
- **Expected Metrics & Changes**:
  - **Sources**: 1
  - **Knowledge (Entities)**: 63
  - **Connections (Edges)**: 180
  - **Average Confidence**: 85%
  - **What Changed Feed**: Displays `+63 Entities`, `+180 Relationships`.
- **Talk Track**: *"We begin with a clean system and upload the baseline manufacturer manual for Pump P-101. ForgeMind reads the document, builds a topological graph of components, and initializes confidence weights at 85% based on standard documentation reliability."*

---

### Step 2: Upload the Telemetry Incident Report
- **Action**: Drag and drop `incident_report_IR-2024-0847.pdf` into the upload zone.
- **Under the Hood**:
  - Extracts failure symptoms (e.g., vibration, overheating).
  - Traces causal links (`caused_by`).
  - **Contradiction Detected**: Detects that the incident log sets the temperature limit to 85°C, while the baseline manual set it to 80°C. Since it cannot confirm which is correct, a contradiction is flagged.
- **Expected Metrics & Changes**:
  - **Sources**: 2
  - **Knowledge (Entities)**: 93
  - **Connections (Edges)**: 221
  - **Issues (Contradictions)**: 1
  - **What Changed Feed**: Displays `+30 Entities`, `+41 Relationships`, plus a red alert flagging the 80°C vs 85°C operating limit conflict.
- **Talk Track**: *"An operational incident occurs. We upload the failure report. ForgeMind parses it, merges the new symptoms into the graph, and immediately flags a contradiction—the telemetry logs list a different operational temperature boundary than the OEM manual. It logs this issue on the timeline without silently overwriting the truth."*

---

### Step 3: Upload the Field Inspection Report
- **Action**: Drag and drop `inspection_INS-2024-0392.pdf` into the upload zone.
- **Under the Hood**:
  - Ingests the field technician's inspection log.
  - Inspect context validates the 80°C limit.
  - The contradiction is auto-resolved because the inspection report has higher provenance weight than the incident telemetry log.
  - Overall node confidence for verified components shifts upwards.
- **Expected Metrics & Changes**:
  - **Sources**: 3
  - **Knowledge (Entities)**: 112
  - **Connections (Edges)**: 256
  - **Issues (Contradictions)**: 0 (Auto-resolved!)
  - **Average Confidence**: ~95%
- **Talk Track**: *"Finally, the physical inspection report arrives. ForgeMind evaluates the document and recognizes that a field technician has verified the operating thresholds. Because inspections carry higher authority than raw logs, the contradiction is auto-resolved, and overall graph confidence rises to 95%."*

---

## Interacting with the AI Copilot

Once all three documents are loaded:
1. In the central Copilot console, click the sample question: **`Why is Pump P-101 failing?`**
2. Click **Analyze** (wait 2 seconds for the deterministic reasoning traversal to complete).
3. **Review Output Cards**:
   - **Decision**: High-confidence diagnosis linking `Pump P-101` failure to `Bearing` fatigue.
   - **Root Cause**: Identifies `Bearing` (95% confidence) supported by both `pump_p101_manual.pdf` and `inspection_INS-2024-0392.pdf`.
   - **Business Impact**: Estimates downtime risk, downtime cost category, and prioritizes the event.
   - **Actions**: Displays color-coded recommended fixes (e.g. `Replace Bearing` as an Immediate Action).
   - **Reasoning**: Click **Show Full Reasoning** to review the exact hop-by-hop traversal proof chain.

---

## Timeline & Graph Playback

1. In the sidebar, click the **Timeline** tab to view the chronological log of all parsed files, metadata changes, and conflict events.
2. In the **Graph** tab, click **▶ Replay** to watch a visual playback. It clears the canvas and rebuilds the node topology document-by-document, showing the exact evolution of the organizational memory.
