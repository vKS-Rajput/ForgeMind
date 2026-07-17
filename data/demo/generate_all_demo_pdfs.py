"""Generate all demo PDFs for the ForgeMind hackathon demo.

Creates three interconnected industrial documents that demonstrate
organizational memory and cross-document reasoning:

  1. Pump P-101 Maintenance Manual (already exists)
  2. Incident Report — Bearing failure after 90 days
  3. Inspection Report — Lubrication contamination confirmed

Upload order matters: Manual → Incident → Inspection
Each upload evolves the knowledge graph and changes recommendations.

Usage:
    cd ForgeMind
    uv run python data/demo/generate_all_demo_pdfs.py
"""

from pathlib import Path

from fpdf import FPDF


def generate_incident_report() -> Path:
    """Generate a 2-page incident report: bearing failure at 90 days."""
    output_path = Path(__file__).parent / "incident_report_IR-2024-0847.pdf"

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    # ── Page 1: Incident Details ─────────────────────────────────
    pdf.add_page()
    pdf.set_font("Helvetica", "B", size=16)
    pdf.cell(
        w=0,
        text="INCIDENT REPORT",
        new_x="LMARGIN",
        new_y="NEXT",
        align="C",
    )
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", size=12)
    pdf.cell(
        w=0,
        text="Meridian Petrochemical Plant",
        new_x="LMARGIN",
        new_y="NEXT",
        align="C",
    )
    pdf.ln(8)

    # Header table
    pdf.set_font("Helvetica", "B", size=10)
    fields = [
        ("Report Number:", "IR-2024-0847"),
        ("Date of Incident:", "2024-03-15"),
        ("Asset:", "Pump P-101 (AquaFlow AF-3500C)"),
        ("Location:", "Production Unit 3"),
        ("Severity:", "HIGH -- Unplanned Shutdown"),
        ("Reported By:", "S. Patel, Shift Supervisor"),
        ("Downtime:", "18 hours"),
    ]
    for label, value in fields:
        pdf.set_font("Helvetica", "B", size=10)
        pdf.cell(w=50, text=label)
        pdf.set_font("Helvetica", size=10)
        pdf.cell(w=0, text=value, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)

    pdf.ln(6)

    # Incident description
    pdf.set_font("Helvetica", "B", size=12)
    pdf.cell(text="1. Incident Description", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    pdf.set_font("Helvetica", size=10)
    paragraphs = [
        (
            "At approximately 14:30 on March 15, 2024, Pump P-101 experienced an "
            "unexpected bearing failure during normal operation. The control room received "
            "a high vibration alarm at 14:22, followed by a high bearing temperature alarm "
            "at 14:25. Vibration levels reached 8.2 mm/s RMS, significantly above the "
            "4.5 mm/s alarm threshold. Bearing temperature reached 112 degrees Celsius "
            "before automatic shutdown was triggered at 14:30."
        ),
        (
            "The pump was operating at normal conditions: 2950 RPM, 145 cubic meters per hour "
            "flow rate, inlet pressure 3.2 bar, outlet pressure 9.8 bar. No abnormal conditions "
            "were recorded in the preceding 24 hours. The last scheduled bearing inspection "
            "was performed 90 days prior, on December 15, 2023, at which time no defects "
            "were noted."
        ),
    ]
    for p in paragraphs:
        pdf.multi_cell(w=0, text=p)
        pdf.ln(4)

    pdf.set_font("Helvetica", "B", size=12)
    pdf.cell(text="2. Root Cause Analysis", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    pdf.set_font("Helvetica", size=10)
    rca_paragraphs = [
        (
            "The drive-end SKF 6205-2RS bearing was found to have seized due to "
            "inadequate lubrication. Upon disassembly, the bearing grease was found to be "
            "severely degraded and contaminated with fine metal particles. The bearing inner "
            "race showed signs of spalling and surface fatigue. The bearing cage was partially "
            "collapsed."
        ),
        (
            "Root Cause: The bearing lubrication degraded faster than expected due to "
            "operating temperatures consistently at the upper end of the normal range "
            "(72-78 degrees Celsius average, versus the design assumption of 55-65 degrees "
            "Celsius). This accelerated grease breakdown and reduced the effective lubrication "
            "interval from the OEM-recommended 180 days to approximately 90 days."
        ),
        (
            "Contributing Factor: The OEM maintenance manual (Revision 2.4) specifies a "
            "semi-annual (180-day) bearing replacement interval. This interval assumes "
            "standard operating temperatures of 55-65 degrees Celsius. The actual operating "
            "temperature of Pump P-101 is consistently 10-15 degrees higher due to the "
            "higher-viscosity feedstock processed at Meridian. This discrepancy was not "
            "identified during the initial commissioning review."
        ),
    ]
    for p in rca_paragraphs:
        pdf.multi_cell(w=0, text=p)
        pdf.ln(4)

    # ── Page 2: Resolution and Recommendations ───────────────────
    pdf.add_page()

    pdf.set_font("Helvetica", "B", size=12)
    pdf.cell(text="3. Immediate Resolution", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    pdf.set_font("Helvetica", size=10)
    resolution = [
        (
            "Emergency bearing replacement was performed on both drive-end and non-drive-end "
            "bearings. New SKF 6205-2RS bearings were installed with fresh Shell Gadus S2 "
            "V220 grease. Shaft runout was measured at 0.03 mm TIR (within tolerance). "
            "Alignment was verified using laser alignment tool (angular: 0.02 mm, offset: "
            "0.04 mm, both within tolerance). Pump was returned to service on March 16, "
            "2024 at 08:45."
        ),
    ]
    for p in resolution:
        pdf.multi_cell(w=0, text=p)
        pdf.ln(4)

    pdf.set_font("Helvetica", "B", size=12)
    pdf.cell(
        text="4. Corrective Actions and Recommendations",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.ln(3)

    pdf.set_font("Helvetica", size=10)
    actions = [
        (
            "Action 1 (CRITICAL): Reduce bearing inspection interval from 180 days to 90 days "
            "for Pump P-101. This accounts for the elevated operating temperature that accelerates "
            "grease degradation. Apply this change to all similar pumps operating above 70 degrees "
            "Celsius bearing temperature."
        ),
        (
            "Action 2: Implement continuous bearing vibration monitoring using permanently "
            "installed accelerometers. Set alarm threshold at 4.0 mm/s (reduced from current "
            "4.5 mm/s) and trip threshold at 7.0 mm/s."
        ),
        (
            "Action 3: Evaluate transition to a high-temperature grease (Shell Gadus S3 V460XD "
            "or equivalent) rated for continuous operation above 80 degrees Celsius. Conduct a "
            "90-day trial starting Q2 2024."
        ),
        (
            "Action 4: Review OEM maintenance schedule for all centrifugal pumps in the plant. "
            "Adjust maintenance intervals based on actual operating conditions rather than "
            "generic OEM recommendations."
        ),
    ]
    for p in actions:
        pdf.multi_cell(w=0, text=p)
        pdf.ln(4)

    pdf.set_font("Helvetica", "B", size=12)
    pdf.cell(text="5. Impact Assessment", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    pdf.set_font("Helvetica", size=10)
    impact = [
        (
            "Total unplanned downtime: 18 hours. Estimated production loss: 2,700 cubic meters "
            "of feedstock throughput. Estimated cost: bearing replacement $2,400, labor $3,600, "
            "production loss $85,000. Total incident cost: approximately $91,000."
        ),
        (
            "If the bearing inspection interval had been 90 days instead of 180 days, this "
            "failure would likely have been detected during a scheduled inspection and addressed "
            "as a planned maintenance activity with zero unplanned downtime."
        ),
    ]
    for p in impact:
        pdf.multi_cell(w=0, text=p)
        pdf.ln(4)

    # Save
    pdf.output(str(output_path))
    print(f"[OK] Generated: {output_path}")
    print(f"   Pages: 2, Size: {output_path.stat().st_size / 1024:.1f} KB")
    return output_path


def generate_inspection_report() -> Path:
    """Generate a 1-page inspection report: contamination confirmed."""
    output_path = Path(__file__).parent / "inspection_INS-2024-0392.pdf"

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    # ── Page 1: Inspection Findings ──────────────────────────────
    pdf.add_page()
    pdf.set_font("Helvetica", "B", size=16)
    pdf.cell(
        w=0,
        text="INSPECTION REPORT",
        new_x="LMARGIN",
        new_y="NEXT",
        align="C",
    )
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", size=12)
    pdf.cell(
        w=0,
        text="Meridian Petrochemical Plant",
        new_x="LMARGIN",
        new_y="NEXT",
        align="C",
    )
    pdf.ln(8)

    # Header
    pdf.set_font("Helvetica", "B", size=10)
    fields = [
        ("Report Number:", "INS-2024-0392"),
        ("Inspection Date:", "2024-04-02"),
        ("Asset:", "Pump P-101 (AquaFlow AF-3500C)"),
        ("Location:", "Production Unit 3"),
        ("Inspector:", "J. Martinez, Senior Mechanical Inspector"),
        ("Inspection Type:", "Post-Incident Detailed Inspection"),
        ("Related Incident:", "IR-2024-0847 (Bearing Failure, 2024-03-15)"),
    ]
    for label, value in fields:
        pdf.set_font("Helvetica", "B", size=10)
        pdf.cell(w=50, text=label)
        pdf.set_font("Helvetica", size=10)
        pdf.cell(w=0, text=value, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)

    pdf.ln(6)

    pdf.set_font("Helvetica", "B", size=12)
    pdf.cell(text="1. Inspection Findings", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    pdf.set_font("Helvetica", size=10)
    findings = [
        (
            "Bearing Condition: The replaced bearings (installed 2024-03-16) are operating "
            "normally. However, grease samples collected from both bearing housings show early "
            "signs of contamination. Metal particle analysis detected iron and chromium particles "
            "at 45 ppm (threshold: 25 ppm), indicating continued wear from an upstream source. "
            "Grease consistency has degraded from NLGI Grade 2 to Grade 1 after only 17 days "
            "of operation."
        ),
        (
            "Mechanical Seal: The drive-end mechanical seal (John Crane Type 2100) shows visible "
            "wear marks on the seal face. Leakage rate measured at 3.2 ml/hour (acceptable limit: "
            "5 ml/hour). Seal face flatness measured at 0.8 light bands (limit: 2 light bands). "
            "The seal is approaching end of useful life and should be replaced at next scheduled "
            "outage."
        ),
        (
            "Vibration Measurements: Current vibration readings on the drive-end bearing housing "
            "are 4.2 mm/s RMS at pump operating speed. This exceeds the revised alarm threshold "
            "of 4.0 mm/s recommended in IR-2024-0847 but is below the trip threshold of 7.0 mm/s. "
            "Frequency analysis shows a dominant peak at 1x running speed (49.2 Hz) suggesting "
            "residual imbalance or misalignment."
        ),
        (
            "Temperature: Bearing temperature recorded at 82 degrees Celsius during steady-state "
            "operation. This is above the OEM normal range of 55-65 degrees Celsius and "
            "approaching the alarm threshold of 85 degrees Celsius. This confirms the finding "
            "from IR-2024-0847 that operating temperatures are consistently elevated."
        ),
    ]
    for p in findings:
        pdf.multi_cell(w=0, text=p)
        pdf.ln(3)

    pdf.set_font("Helvetica", "B", size=12)
    pdf.cell(text="2. Recommendations", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    pdf.set_font("Helvetica", size=10)
    recs = [
        (
            "Recommendation 1 (CRITICAL): Confirm reduction of bearing inspection interval "
            "from 180 days to 90 days as recommended in IR-2024-0847. Current grease degradation "
            "rate supports this conclusion. Evidence from three sources (OEM manual operating "
            "conditions, incident IR-2024-0847, and this inspection) confirms that the 180-day "
            "interval is insufficient for Pump P-101 operating conditions."
        ),
        (
            "Recommendation 2: Replace mechanical seal at next scheduled outage (estimated "
            "within 30 days). Current leakage rate is within limits but trending upward."
        ),
        (
            "Recommendation 3: Investigate source of metal particle contamination in bearing "
            "grease. Possible sources include wear ring degradation, shaft sleeve wear, or "
            "external contamination through inadequate bearing housing seals."
        ),
        (
            "Recommendation 4: Install permanent vibration monitoring sensors on both bearing "
            "housings. Current portable measurements at 4.2 mm/s warrant continuous monitoring "
            "to detect further degradation trend."
        ),
        (
            "Overall Assessment: Pump P-101 is currently operational but requires close "
            "monitoring. The combination of elevated temperature, grease contamination, and "
            "vibration readings above revised thresholds indicates that the root cause identified "
            "in IR-2024-0847 (accelerated grease degradation due to high operating temperature) "
            "has not been fully resolved. The 90-day inspection interval is confirmed as the "
            "minimum safe interval for current operating conditions. Confidence in this "
            "recommendation: HIGH (supported by OEM manual, incident report, and this inspection)."
        ),
    ]
    for p in recs:
        pdf.multi_cell(w=0, text=p)
        pdf.ln(3)

    # Save
    pdf.output(str(output_path))
    print(f"[OK] Generated: {output_path}")
    print(f"   Pages: 1, Size: {output_path.stat().st_size / 1024:.1f} KB")
    return output_path


if __name__ == "__main__":
    print("=== ForgeMind Demo PDF Generator ===\n")
    generate_incident_report()
    print()
    generate_inspection_report()
    print()
    print("Demo flow:")
    print("  1. Upload pump_p101_manual.pdf")
    print("  2. Upload incident_report_IR-2024-0847.pdf")
    print("  3. Upload inspection_INS-2024-0392.pdf")
    print("  4. POST /api/v1/reason -> cross-document intelligence")
    print("  5. GET /graph -> knowledge visualization")
