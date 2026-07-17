# ForgeMind API Documentation

ForgeMind exposes a RESTful JSON API for document ingestion, graph querying, timeline generation, and deterministic decision support.

## Base URL
When running locally: `http://localhost:8000`

---

## 1. Document Context Endpoints

### Upload PDF Document
Ingests a PDF file, executes chunking, extracts entities and relationships, and indexes the document.

- **Method**: `POST`
- **Path**: `/api/v1/documents/upload`
- **Request Format**: `multipart/form-data`
  - `file`: PDF binary file
- **Success Response (201 Created)**:
```json
{
  "document_id": "8ca7d0be-4a27-4638-9cf8-18e390cbf6bd",
  "title": "pump_p101_manual.pdf",
  "page_count": 3,
  "chunk_count": 12,
  "knowledge_graph": {
    "total_entities": 63,
    "total_relationships": 180,
    "entities_created": 63,
    "relationships_created": 180,
    "entities_updated": 0,
    "relationships_strengthened": 0
  },
  "knowledge_delta": {
    "confidence_changes": [],
    "contradictions": []
  }
}
```
- **Error Responses**:
  - `400 Bad Request`: If the PDF is corrupt, encrypted, or duplicate ingestion was skipped.

---

### Ingest Raw Text
Ingests a raw text block instead of a binary PDF.

- **Method**: `POST`
- **Path**: `/api/v1/documents/text`
- **Request Body (JSON)**:
```json
{
  "text": "Pump P-101 has an operating speed of 3500 RPM. Main bearing is SKF 6310.",
  "title": "Maintenance Note 04"
}
```
- **Success Response (201 Created)**: Matches the upload response schema.

---

## 2. Graph & Timeline Endpoints

### Retrieve Graph Visualization Data
Returns all active nodes and edges in a format ready for visualization engines (like D3.js).

- **Method**: `GET`
- **Path**: `/api/v1/graph/data`
- **Success Response (200 OK)**:
```json
{
  "nodes": [
    {
      "id": "pump-p101-id",
      "name": "Pump P-101",
      "type": "asset",
      "confidence": 0.85
    }
  ],
  "edges": [
    {
      "source": "pump-p101-id",
      "target": "bearing-id",
      "type": "has_component",
      "confidence": 0.85
    }
  ]
}
```

---

### Retrieve Evolving Timeline
Returns a chronological timeline showing how the graph evolved.

- **Method**: `GET`
- **Path**: `/api/v1/graph/timeline`
- **Success Response (200 OK)**:
```json
{
  "timeline": [
    {
      "event_id": "event-uuid",
      "timestamp": "2026-07-17T23:50:10Z",
      "event_type": "entity_added",
      "source_document": "pump_p101_manual.pdf",
      "entity_name": "Pump P-101",
      "entity_type": "asset"
    },
    {
      "event_id": "event-uuid",
      "timestamp": "2026-07-17T23:55:00Z",
      "event_type": "contradiction_detected",
      "source_document": "incident_report_IR-2024-0847.pdf",
      "fact": "Operating Temperature Limit",
      "source_a": "pump_p101_manual.pdf (80C)",
      "source_b": "incident_report_IR-2024-0847.pdf (85C)",
      "resolution": "Retained 80C baseline pending inspection validation."
    }
  ]
}
```

---

## 3. Decision Intelligence Endpoints

### Ask Copilot / Query Decision Support
Submit a diagnostic query to retrieve decision, severity, business impact, and evidence chain.

- **Method**: `POST`
- **Path**: `/api/v1/decide`
- **Request Body (JSON)**:
```json
{
  "query": "Why is Pump P-101 failing?"
}
```
- **Success Response (200 OK)**:
```json
{
  "query": "Why is Pump P-101 failing?",
  "entity_name": "Pump P-101",
  "entity_type": "asset",
  "decision": {
    "problem": "Pump P-101 -- Excessive Vibration (most likely cause: Bearing)",
    "severity": "critical",
    "confidence": 0.85
  },
  "diagnosis": {
    "most_likely_cause": {
      "cause": "Bearing",
      "cause_type": "component",
      "confidence": 0.85,
      "evidence_count": 3,
      "supporting_documents": ["pump_p101_manual.pdf", "inspection_INS-2024-0392.pdf"],
      "evidence_chain": ["Pump P-101 has component Bearing", "Vibration is caused by Bearing"]
    }
  },
  "recommended_actions": [
    {
      "action": "Replace Bearing",
      "priority": "critical",
      "resolves": "Excessive Vibration"
    }
  ],
  "business_impact": {
    "estimated_downtime_prevented": "4-8 hours planned",
    "maintenance_priority": "High -- schedule at next outage",
    "risk_level": "Medium",
    "cost_category": "Low ($1K-$10K)"
  },
  "confidence_breakdown": {
    "score": 0.85,
    "factors": ["3 evidence links analyzed", "2 graph traversals completed"]
  }
}
```

---

## 4. Demo Administration Endpoints

### Reset Demo
Clears all documents, graph, timeline logs, and resets application memory.

- **Method**: `POST`
- **Path**: `/api/demo/reset`
- **Success Response (200 OK)**:
```json
{
  "message": "ForgeMind reset. Ready for a fresh demo.",
  "status": "clean"
}
```
