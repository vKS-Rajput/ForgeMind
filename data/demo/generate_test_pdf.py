"""Generate a sample PDF for testing the ForgeMind ingestion API.

Run this script to create a realistic 3-page industrial maintenance
manual that you can upload to the API at http://localhost:8000/docs.

Usage:
    cd ForgeMind
    uv run python data/demo/generate_test_pdf.py
"""

from pathlib import Path

from fpdf import FPDF


def generate_pump_manual() -> Path:
    """Generate a 3-page pump maintenance manual PDF."""
    output_path = Path(__file__).parent / "pump_p101_manual.pdf"

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    # ── Page 1: Equipment Overview ───────────────────────────────
    pdf.add_page()
    pdf.set_font("Helvetica", "B", size=18)
    pdf.cell(w=0, text="MERIDIAN PETROCHEMICAL PLANT", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(3)
    pdf.set_font("Helvetica", "B", size=14)
    pdf.cell(w=0, text="Pump P-101 Maintenance Manual", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.cell(w=0, text="Document Revision 2.4 | June 2025", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(10)

    pdf.set_font("Helvetica", "B", size=12)
    pdf.cell(text="1. Equipment Overview", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    pdf.set_font("Helvetica", size=10)
    paragraphs = [
        (
            "Pump P-101 is a single-stage centrifugal pump manufactured by AquaFlow Industries, "
            "model AF-3500C. It is installed in Production Unit 3 of the Meridian Petrochemical Plant "
            "and is critical for feedstock transfer operations. The pump was commissioned in March 2019 "
            "and operates continuously during production cycles."
        ),
        (
            "The pump operates at a nominal speed of 3000 RPM driven by a 75 kW electric motor through "
            "a flexible coupling. Design flow rate is 150 cubic meters per hour with a total dynamic "
            "head of 45 meters. The pump handles light hydrocarbon feedstock at temperatures between "
            "25 and 65 degrees Celsius."
        ),
        (
            "Major components include: the impeller (316L stainless steel, closed type), the mechanical "
            "seal (John Crane Type 2100, single cartridge), the bearing housing with two SKF 6205-2RS "
            "deep groove ball bearings, the shaft (AISI 4140 steel), and the volute casing (cast iron "
            "Grade 25). The pump is mounted on a concrete foundation with vibration isolation pads."
        ),
    ]
    for p in paragraphs:
        pdf.multi_cell(w=0, text=p)
        pdf.ln(4)

    pdf.set_font("Helvetica", "B", size=12)
    pdf.cell(text="2. Operating Parameters", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    pdf.set_font("Helvetica", size=10)
    limits = [
        (
            "Normal operating parameters must be maintained within the following limits at all times. "
            "Inlet pressure: 2.0 to 4.0 bar gauge. Outlet pressure: 8.0 to 12.0 bar gauge. "
            "Flow rate: 120 to 180 cubic meters per hour. Bearing temperature: not to exceed 80 degrees "
            "Celsius. Vibration level: not to exceed 4.5 mm/s RMS on bearing housing."
        ),
        (
            "The pump must not be operated below minimum continuous stable flow of 60 cubic meters per hour "
            "to prevent recirculation damage. Dry running for more than 30 seconds will cause catastrophic "
            "mechanical seal failure and is strictly prohibited."
        ),
    ]
    for p in limits:
        pdf.multi_cell(w=0, text=p)
        pdf.ln(4)

    # ── Page 2: Maintenance Schedule ─────────────────────────────
    pdf.add_page()
    pdf.set_font("Helvetica", "B", size=12)
    pdf.cell(text="3. Preventive Maintenance Schedule", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    pdf.set_font("Helvetica", size=10)
    schedule_items = [
        (
            "Daily Checks: Verify bearing temperature using infrared thermometer. Check vibration levels "
            "with portable analyzer. Inspect mechanical seal for visible leakage. Verify inlet and outlet "
            "pressure readings on local gauges. Record all readings in the daily logbook."
        ),
        (
            "Weekly Maintenance: Grease motor bearings using Shell Gadus S2 V220 grease (2 pumps per "
            "grease point). Check coupling alignment using dial indicators. Inspect foundation bolts for "
            "tightness. Clean strainer basket on the suction line."
        ),
        (
            "Monthly Maintenance: Perform vibration spectrum analysis and compare to baseline. Check "
            "motor current draw against nameplate rating. Inspect piping supports and expansion joints. "
            "Verify all safety instrumentation (pressure relief valve PSV-101, flow switch FS-101)."
        ),
        (
            "Semi-Annual Overhaul: Replace mechanical seal assembly. Replace both SKF 6205-2RS bearings. "
            "Inspect impeller for erosion and cavitation damage. Measure shaft runout (max 0.05 mm TIR). "
            "Replace coupling elastomer element. Perform hydrostatic test at 1.5x MAWP."
        ),
        (
            "Annual Inspection: Full disassembly and inspection of all wetted parts. Measure casing wear "
            "ring clearance (replace if exceeds 0.5 mm). NDT inspection of shaft for cracks. Thickness "
            "measurement of volute casing. Review and update maintenance procedures as needed."
        ),
    ]
    for p in schedule_items:
        pdf.multi_cell(w=0, text=p)
        pdf.ln(4)

    # ── Page 3: Troubleshooting ──────────────────────────────────
    pdf.add_page()
    pdf.set_font("Helvetica", "B", size=12)
    pdf.cell(text="4. Troubleshooting Guide", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    pdf.set_font("Helvetica", size=10)
    issues = [
        (
            "Symptom: Excessive Vibration (above 4.5 mm/s RMS). "
            "Possible Causes: Bearing failure or degradation, shaft misalignment, impeller imbalance "
            "due to erosion, loose foundation bolts, cavitation. "
            "Corrective Actions: Immediately reduce pump speed to 2000 RPM. Perform vibration spectrum "
            "analysis to identify the dominant frequency. If bearing defect frequency is present, schedule "
            "bearing replacement within 48 hours. Check and correct alignment using reverse dial indicator "
            "method. Verify inlet pressure is above minimum NPSH required."
        ),
        (
            "Symptom: High Bearing Temperature (above 80 degrees Celsius). "
            "Possible Causes: Insufficient or degraded lubrication, bearing overload due to misalignment, "
            "internal bearing damage, ambient temperature effects. "
            "Corrective Actions: Check grease condition and re-lubricate if dry or contaminated. Verify "
            "alignment is within tolerance (0.05 mm angular, 0.08 mm offset). If temperature exceeds "
            "95 degrees Celsius, shut down immediately and replace bearings."
        ),
        (
            "Symptom: Reduced Flow Rate (below 120 cubic meters per hour). "
            "Possible Causes: Impeller wear or erosion damage, suction strainer blockage, air entrainment "
            "in suction line, worn wear rings increasing internal recirculation. "
            "Corrective Actions: Check and clean suction strainer. Verify suction line is free of air "
            "leaks. Measure actual head versus curve to determine impeller condition. If performance has "
            "degraded more than 10 percent from baseline, schedule impeller replacement."
        ),
        (
            "Symptom: Mechanical Seal Leakage. "
            "Possible Causes: Seal face damage, shaft sleeve scoring, incorrect seal setting, thermal "
            "shock from rapid temperature changes, excessive shaft deflection. "
            "Corrective Actions: Minor drip leakage (less than 5 ml per hour) can be monitored. "
            "Continuous stream leakage requires immediate shutdown. Replace the complete John Crane "
            "Type 2100 cartridge seal assembly. Inspect shaft sleeve for scoring and replace if "
            "runout exceeds 0.025 mm."
        ),
        (
            "Symptom: Abnormal Noise During Operation. "
            "Possible Causes: Cavitation (crackling or rattling sound), bearing damage (grinding or "
            "squealing), impeller rubbing on wear ring, loose internal components. "
            "Corrective Actions: For cavitation noise, increase suction pressure or reduce flow rate. "
            "For bearing noise, schedule immediate replacement. For rubbing noise, shut down and check "
            "wear ring clearance. Document all noise events with timestamp and operating conditions."
        ),
    ]
    for p in issues:
        pdf.multi_cell(w=0, text=p)
        pdf.ln(4)

    # ── Save ─────────────────────────────────────────────────────
    pdf.output(str(output_path))
    print(f"✅ Generated: {output_path}")
    print(f"   Pages: 3")
    print(f"   Size:  {output_path.stat().st_size / 1024:.1f} KB")
    print()
    print("Upload this file at: http://localhost:8000/docs")
    print('  → POST /api/v1/documents/upload → "Try it out" → Choose File')

    return output_path


if __name__ == "__main__":
    generate_pump_manual()
