# Meridian Petrochemical Plant — Demo Dataset

## Overview

The demo dataset represents a fictional mid-size chemical processing facility called **Meridian Petrochemical Plant**. It provides realistic industrial maintenance data for demonstrating ForgeMind's capabilities.

## Facility Description

- **Location**: Fictional coastal industrial zone
- **Operations**: Chemical processing and petrochemical refining
- **Scale**: 3 production lines, 12 major assets
- **History**: 2 years of operational data

## Major Assets

| Asset ID | Type | Location | Status |
| :--- | :--- | :--- | :--- |
| P-101 | Centrifugal Pump | Production Line 1 | Active |
| P-102 | Centrifugal Pump | Production Line 1 | Active |
| C-201 | Reciprocating Compressor | Production Line 2 | Active |
| C-202 | Screw Compressor | Production Line 2 | Under Maintenance |
| HX-301 | Shell & Tube Heat Exchanger | Production Line 3 | Active |
| HX-302 | Plate Heat Exchanger | Production Line 3 | Active |
| V-101 | Control Valve | Production Line 1 | Active |
| V-201 | Safety Valve | Production Line 2 | Active |

## Dataset Components

### `manuals/`
Synthetic equipment maintenance manuals (PDF format):
- Operating parameters and specifications
- Component lists and parts numbers
- Maintenance schedules and procedures
- Troubleshooting guides (symptom → cause → action)
- Safety warnings

### `incidents/`
Synthetic incident reports (JSON format):
- Incident ID, date, severity, affected asset
- Description, root cause, resolution
- Cross-references to related incidents

### `work_orders/`
Synthetic maintenance work orders (JSON format):
- Work order ID, date, asset, type (corrective/preventive)
- Description, parts used, labor hours, outcome

### `golden_queries/`
10 benchmark questions with expected answer patterns for testing.

## Key Narrative: The Cascading Failure

The dataset includes a narrative arc of interconnected incidents:
1. Vibration alert on Pump P-101 (INC-2024-0029)
2. Bearing replacement on P-101 (INC-2024-0038)
3. Coupling misalignment and overheating (INC-2024-0042)

This chain demonstrates ForgeMind's ability to trace causal relationships across time.
