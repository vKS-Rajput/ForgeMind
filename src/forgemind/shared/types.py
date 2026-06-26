"""Common type aliases used across all ForgeMind bounded contexts.

These types form the ubiquitous language of the system. All modules
reference these shared types rather than using raw primitives.

Bounded Context: Shared
Layer: Types
Dependencies: None (pure type definitions)
"""

from typing import NewType

# ── Identity Types ───────────────────────────────────────────────
# Distinct types prevent accidentally passing a DocumentId where
# an EntityId is expected. NewType has zero runtime overhead.

DocumentId = NewType("DocumentId", str)
"""Unique identifier for an ingested document."""

ChunkId = NewType("ChunkId", str)
"""Unique identifier for a document chunk."""

EntityId = NewType("EntityId", str)
"""Unique identifier for a knowledge entity (node in the graph)."""

RelationshipId = NewType("RelationshipId", str)
"""Unique identifier for a knowledge relationship (edge in the graph)."""

IncidentId = NewType("IncidentId", str)
"""Unique identifier for an incident report."""

WorkOrderId = NewType("WorkOrderId", str)
"""Unique identifier for a maintenance work order."""

# ── Semantic Types ───────────────────────────────────────────────

Confidence = NewType("Confidence", float)
"""A confidence score in [0.0, 1.0]. Higher means more certain."""

EmbeddingVector = NewType("EmbeddingVector", list[float])
"""A dense vector embedding from a sentence-transformer model."""
