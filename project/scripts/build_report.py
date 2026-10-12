#!/usr/bin/env python3
"""Build the final technical report from the reproducible experiment outputs."""

from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    HRFlowable,
    Image,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "deliverables" / "final_report.pdf"
RESULTS = ROOT / "outputs" / "results"
PLOTS = ROOT / "outputs" / "plots"

NAVY = colors.HexColor("#17324D")
BLUE = colors.HexColor("#1874CD")
ORANGE = colors.HexColor("#E17C05")
LIGHT = colors.HexColor("#EEF3F7")
MID = colors.HexColor("#D4DFE8")
DARK = colors.HexColor("#263746")
RED = colors.HexColor("#B33A3A")


def P(text: str, style) -> Paragraph:
    return Paragraph(text, style)


def pct(new: float, old: float) -> float:
    return 100.0 * (new - old) / old


def fit_image(path: Path, width: float, height: float) -> Image:
    from PIL import Image as PILImage
    with PILImage.open(path) as im:
        w, h = im.size
    scale = min(width / w, height / h)
    return Image(str(path), width=w * scale, height=h * scale)


class NumberedDocTemplate(BaseDocTemplate):
    pass


def header_footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(MID)
    canvas.setLineWidth(0.6)
    canvas.line(0.58 * inch, 0.48 * inch, 7.92 * inch, 0.48 * inch)
    canvas.setFillColor(colors.HexColor("#5C6B78"))
    canvas.setFont("Helvetica", 7.5)
    canvas.drawString(0.58 * inch, 0.29 * inch, "CEE 281 | Pathway A | Ruopeng")
    canvas.drawRightString(7.92 * inch, 0.29 * inch, f"Page {doc.page}")
    if doc.page > 1:
        canvas.setFillColor(NAVY)
        canvas.setFont("Helvetica-Bold", 8)
        canvas.drawString(0.58 * inch, 10.55 * inch, "CONNECTED AND AUTOMATED VEHICLE CONTROL")
    canvas.restoreState()


def table(data, widths, font=8.1, header=True, aligns=None):
    head_style = ParagraphStyle(
        "TableHead", fontName="Helvetica-Bold", fontSize=font,
        leading=font + 2, textColor=colors.white, spaceAfter=0,
    )
    cell_style = ParagraphStyle(
        "TableCell", fontName="Helvetica", fontSize=font,
        leading=font + 2, textColor=DARK, spaceAfter=0,
    )
    wrapped = []
    for r, row in enumerate(data):
        wrapped.append([
            cell if isinstance(cell, Paragraph) else Paragraph(str(cell), head_style if header and r == 0 else cell_style)
            for cell in row
        ])
    t = Table(wrapped, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
    style = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), font),
        ("LEADING", (0, 0), (-1, -1), font + 2),
        ("GRID", (0, 0), (-1, -1), 0.35, MID),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7F9FB")]),
    ]
    if header:
        style += [
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ]
    if aligns:
        for col, align in aligns.items():
            style.append(("ALIGN", (col, 1 if header else 0), (col, -1), align))
    t.setStyle(TableStyle(style))
    return t


def main():
    metrics = pd.read_csv(RESULTS / "scenario_metrics.csv").set_index("scenario_id")
    forecast = pd.read_csv(RESULTS / "forecast_metrics.csv")
    audit = pd.read_csv(RESULTS / "detector_audit.csv")
    tmc = pd.read_csv(RESULTS / "tmc_comparison.csv").set_index("meter_mode")
    timestep = pd.read_csv(RESULTS / "timestep_sensitivity.csv")

    h = metrics.loc["nominal_human"]
    a50 = metrics.loc["nominal_acc_50"]
    c50 = metrics.loc["nominal_cacc_50"]
    cdeg = metrics.loc["degraded_cacc_50"]
    high_h = metrics.loc["high_demand_human"]
    high_c = metrics.loc["high_demand_cacc_50"]

    styles = getSampleStyleSheet()
    title = ParagraphStyle("TitleX", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=25, leading=29, textColor=NAVY, alignment=TA_LEFT, spaceAfter=8)
    subtitle = ParagraphStyle("SubtitleX", parent=styles["Normal"], fontSize=11, leading=14, textColor=colors.HexColor("#526675"), spaceAfter=10)
    h1 = ParagraphStyle("H1X", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=16, leading=19, textColor=NAVY, spaceBefore=2, spaceAfter=7)
    h2 = ParagraphStyle("H2X", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=10.7, leading=13, textColor=BLUE, spaceBefore=5, spaceAfter=3)
    body = ParagraphStyle("BodyX", parent=styles["BodyText"], fontName="Helvetica", fontSize=8.8, leading=11.5, textColor=DARK, spaceAfter=5)
    small = ParagraphStyle("SmallX", parent=body, fontSize=7.7, leading=9.6, spaceAfter=3)
    bullet = ParagraphStyle("BulletX", parent=body, leftIndent=12, firstLineIndent=-7, bulletIndent=4, spaceAfter=3)
    caption = ParagraphStyle("CaptionX", parent=body, fontSize=7.3, leading=9, textColor=colors.HexColor("#5C6B78"), alignment=TA_CENTER, spaceBefore=2, spaceAfter=5)
    callout = ParagraphStyle("CalloutX", parent=body, fontName="Helvetica-Bold", fontSize=9.5, leading=12, textColor=NAVY, borderColor=BLUE, borderWidth=0.7, borderPadding=7, backColor=LIGHT, spaceBefore=4, spaceAfter=7)
    equation = ParagraphStyle("EquationX", parent=body, fontName="Courier", fontSize=7.5, leading=10, leftIndent=6, rightIndent=6, borderColor=MID, borderWidth=0.5, borderPadding=5, backColor=colors.HexColor("#F8FAFC"), spaceAfter=5)
    refstyle = ParagraphStyle("RefX", parent=small, leftIndent=12, firstLineIndent=-12, spaceAfter=5)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc = NumberedDocTemplate(
        str(OUT), pagesize=letter,
        leftMargin=0.58 * inch, rightMargin=0.58 * inch,
        topMargin=0.60 * inch, bottomMargin=0.58 * inch,
        title="CEE 281 Pathway A - Connected and Automated Vehicle Control",
        author="Ruopeng",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="main")
    doc.addPageTemplates([PageTemplate(id="report", frames=[frame], onPage=header_footer)])
    story = []

    # Page 1
    story += [
        Spacer(1, 0.15 * inch),
        P("Connected and Automated Vehicle Control", title),
        P("CEE 281 Final Design Report | Pathway A | Fall 2026<br/><b>Contributor:</b> Ruopeng (individual project; official UID to be added)", subtitle),
        HRFlowable(width="100%", thickness=2, color=ORANGE, spaceBefore=1, spaceAfter=10),
        P("Bounded design question", h1),
        P("At 50% and 100% equipment penetration, does delayed predecessor-acceleration feedforward (CACC) reduce a lead-braking disturbance relative to otherwise identical ACC while maintaining throughput and bounded gaps in a mixed, open freeway simulation?", callout),
    ]
    kpi = [
        [P("CACC vs ACC (50%)", small), P("Nominal throughput", small), P("Decision", small)],
        [P(f"<b>{abs(pct(c50['disturbance_amplification'], a50['disturbance_amplification'])):.1f}%</b><br/>lower amplification", body), P(f"<b>{c50['throughput_veh_h']:.0f} veh/h</b><br/>unchanged", body), P("<b>Revise before adoption</b><br/>tradeoffs remain", body)],
    ]
    story += [table(kpi, [2.35*inch, 2.15*inch, 2.35*inch], font=8.4), Spacer(1, 6)]
    story += [fit_image(PLOTS / "01_nominal_performance.png", 7.2*inch, 4.25*inch), P("Figure 1. Same demand, initialization, disturbance, ramp logic, and 900-s horizon. All nominal vehicles clear; throughput therefore ties, while delay and trajectory indicators distinguish controllers.", caption)]
    story += [P(f"<b>Answer.</b> CACC has incremental value over matched ACC: amplification falls from {a50['disturbance_amplification']:.3f} to {c50['disturbance_amplification']:.3f} and the minimum gap rises from {a50['minimum_gap_m']:.3f} to {c50['minimum_gap_m']:.3f} m. It also adds {pct(c50['total_delay_veh_h'], a50['total_delay_veh_h']):.1f}% delay and does not beat the already stable human baseline on amplification or hard-braking count. These are operational simulation indicators, not evidence of crash reduction.", body), PageBreak()]

    # Page 2
    story += [P("1. System, equations, and controller boundary", h1)]
    story += [P("The common environment is a 2.5-km, one-lane freeway with deterministic arrivals until 600 s, a gap-accepted ramp merge at 1.2 km, a 300-m speed bottleneck beginning at 1.6 km, and a 300-s clearance period. A 12-vehicle initial platoon receives a four-second braking pulse. All waiting, overflow, in-system, and exited vehicles remain in performance accounting.", body)]
    story += [P("Human vehicle dynamics", h2), P("IDM [1] with s1 = 0:", body), P("a_IDM = a [1 - (v/v0)^delta - (s_star/s)^2]<br/>s_star = s0 + max(0, v T + v (v-v_lead)/(2 sqrt(a b)))", equation)]
    story += [P("ACC and cooperative extension", h2), P("The reduced-order controller follows Ploeg et al.'s constant-time-headway policy and predecessor feedforward structure [2]; gains use their reported kp and kd while the project uses a larger 1.1-s headway. A first-order actuator represents ordinary command-to-motion dynamics [3]. A controller-level safety supervisor checks one-step clearance and differential stopping distance; when its 2.0-m physical gap floor is threatened, bounded braking is applied immediately and logged separately.", body), P("s_des = r + h v<br/>u_ACC = min[k_v(v0-v), k_p(s-s_des) + k_d(v_lead-v)]<br/>u_CACC = u_ACC + k_ff a_lead(t-delay), then clip to [-4, 2] m/s2<br/>s_physical >= 2.0 m; a_dot = (u-a)/tau outside safety override", equation)]
    model_rows = [
        ["Element", "Declared value", "Reason / boundary"],
        ["Human IDM", "T=1.4 s; s0=2 m; a=1.2; b=1.8; delta=4", "Plausible, interpretable parameters; not field calibrated"],
        ["ACC/CACC", "h=1.1 s; kp=0.20; kd=0.70; kff=0.80", "ACC is the CEE281 communication ablation"],
        ["Messages", "0.15 s nominal; 0.8 s + 30% dropout degraded", "Immediate equipped predecessor acceleration only"],
        ["Fallback", "Feedforward=0; local ACC and emergency brake remain", "Missing, unavailable, or >1.0-s stale messages"],
        ["Safety supervisor", "2.0-m physical net-gap floor", "One-step and stopping-distance limits; override logged"],
        ["Update", "control 0.1 s; simulation 0.1 s", "0.05/0.20-s numerical checks"],
    ]
    story += [table(model_rows, [1.25*inch, 2.75*inch, 2.95*inch], font=7.7)]
    story += [P("Controller-information boundary", h2)]
    interface_rows = [
        ["Permitted controller inputs", "Withheld evaluation truth", "Logged command output"],
        ["Ego speed; local gap; relative speed; delayed predecessor acceleration when communicated", "Future trajectories; disturbance schedule; downstream vehicle truth; uncommunicated human state", "Issue/apply time; measured inputs; message validity/age; bounded acceleration; fallback state"],
    ]
    story += [table(interface_rows, [2.35*inch, 2.25*inch, 2.35*inch], font=7.6), P("Vehicle states, observations, forecasts, ramp commands, and evaluation records use explicit units and stable identifiers. See interfaces.md.", caption), PageBreak()]

    # Page 3
    story += [P("2. Verification, observation, forecasting, and common TMC", h1)]
    checks = [
        ["Check", "Expected", "Evidence"],
        ["Free motion", "a_IDM=a at v=0 with no leader", "Unit test passes"],
        ["Equilibrium", "Analytical equilibrium gap gives a=0", "Unit test passes to 7 decimals"],
        ["Conservation", "generated = exited + in-system + queues + overflow", "Unit test passes; nominal residual=0"],
        ["Physical clearance", "minimum net gap >= 2.0 m", "All 12 final scenarios pass; final guard activations=0"],
        ["Detector count", "event recount equals 30-s report", f"{len(audit)} labeled intervals; max error={audit['count_error_veh'].abs().max():.0f}"],
        ["Time step", "ranking stable at 0.05/0.10/0.20 s", "Human delay 5.586-5.607; CACC-50 1.917-1.956 veh-h"],
    ]
    story += [table(checks, [1.25*inch, 3.05*inch, 2.65*inch], font=7.7)]
    story += [P("Observation and one-step forecast", h2), P("D1/D2 return 30-s count, mean crossing speed when measurable, a 50-m area-occupancy proxy, and a quality flag [5]. Exponential smoothing is tuned only on the first 15 intervals, then compared with a three-interval moving average on the same 15 held-out targets, consistent with historical-average comparison practice [6].", body)]
    f0, f1 = forecast.iloc[0], forecast.iloc[1]
    fr = [
        ["Observation condition", "MA(3) MAE", "Exp. smoothing MAE", "Interpretation"],
        ["Complete", f"{f0['moving_average_3_mae_veh_per_interval']:.3f}", f"{f0['exponential_smoothing_mae_veh_per_interval']:.3f}", "Smoother wins held-out comparison"],
        ["Every 5th interval missing", f"{f1['moving_average_3_mae_veh_per_interval']:.3f}", f"{f1['exponential_smoothing_mae_veh_per_interval']:.3f}", "Unexpected decrease is pattern-specific, not a benefit claim"],
    ]
    story += [table(fr, [1.55*inch, 1.1*inch, 1.45*inch, 2.85*inch], font=7.6)]
    story += [fit_image(PLOTS / "06_sensitivity_tmc.png", 7.1*inch, 2.7*inch), P("Figure 2. Numerical sensitivity is small. The ALINEA-like occupancy loop [7] is bounded and functional but does not improve nominal total delay: unmetered 5.442, fixed 5.531, feedback 5.590 veh-h.", caption)]
    story += [P("The TMC result is deliberately retained as a supported negative result. The virtual occupancy proxy, light nominal constraint, and uncalibrated target limit any claim about field ramp metering.", body), PageBreak()]

    # Page 4
    story += [P("3. Fair final-pathway experiment and nominal evidence", h1)]
    story += [P("Every controller comparison holds demand, initial platoon, disturbance timing, bottleneck, ramp logic, run length, detector definitions, and seed constant. The required penetration set is 0%, 50%, and 100%; ACC is included at both nonzero levels to isolate communication. Nominal CACC uses 0.15-s delay. The evaluation record includes residual queues and unmet/overflow demand.", body)]
    story += [fit_image(PLOTS / "02_disturbance_speed_traces.png", 7.15*inch, 3.15*inch), P("Figure 3. Speed traces for the same disturbance cohort. The human baseline already dissipates the pulse; CACC improves the matched ACC response at 50% penetration but does not dominate the human amplification ratio.", caption)]
    nominal_rows = [
        ["Scenario", "Delay (veh-h)", "Throughput (veh/h)", "Amplification", "Min gap (m)", "Hard brakes"],
        ["Human 0%", f"{h['total_delay_veh_h']:.3f}", f"{h['throughput_veh_h']:.0f}", f"{h['disturbance_amplification']:.3f}", f"{h['minimum_gap_m']:.3f}", f"{h['hard_brake_events']:.0f}"],
        ["ACC 50%", f"{a50['total_delay_veh_h']:.3f}", f"{a50['throughput_veh_h']:.0f}", f"{a50['disturbance_amplification']:.3f}", f"{a50['minimum_gap_m']:.3f}", f"{a50['hard_brake_events']:.0f}"],
        ["CACC 50%", f"{c50['total_delay_veh_h']:.3f}", f"{c50['throughput_veh_h']:.0f}", f"{c50['disturbance_amplification']:.3f}", f"{c50['minimum_gap_m']:.3f}", f"{c50['hard_brake_events']:.0f}"],
        ["ACC 100%", f"{metrics.loc['nominal_acc_100','total_delay_veh_h']:.3f}", "1288", f"{metrics.loc['nominal_acc_100','disturbance_amplification']:.3f}", f"{metrics.loc['nominal_acc_100','minimum_gap_m']:.3f}", f"{metrics.loc['nominal_acc_100','hard_brake_events']:.0f}"],
        ["CACC 100%", f"{metrics.loc['nominal_cacc_100','total_delay_veh_h']:.3f}", "1288", f"{metrics.loc['nominal_cacc_100','disturbance_amplification']:.3f}", f"{metrics.loc['nominal_cacc_100','minimum_gap_m']:.3f}", f"{metrics.loc['nominal_cacc_100','hard_brake_events']:.0f}"],
    ]
    story += [table(nominal_rows, [1.15*inch, 1.1*inch, 1.2*inch, 1.1*inch, 1.0*inch, 0.9*inch], font=7.5)]
    story += [P(f"<b>CEE281 ablation.</b> At 50%, enabling communication changes only the feedforward channel: amplification improves {abs(pct(c50['disturbance_amplification'], a50['disturbance_amplification'])):.1f}% and minimum gap improves {pct(c50['minimum_gap_m'], a50['minimum_gap_m']):.1f}%, but delay worsens {pct(c50['total_delay_veh_h'], a50['total_delay_veh_h']):.1f}%. At 100%, both automated controllers have very low delay but high hard-braking counts; this exposes gain/actuation behavior that a delay-only conclusion would hide.", callout), PageBreak()]

    # Page 5
    story += [P("4. Stress, degradation, and failure evidence", h1)]
    story += [fit_image(PLOTS / "04_stress_tests.png", 7.15*inch, 3.45*inch), P("Figure 4. Changed-demand and stronger-braking tests. Values are scored over the same 900-s horizon and include unserved/overflow vehicles.", caption)]
    stress_rows = [
        ["Test", "Change", "Observed response", "Design implication"],
        ["Communication degradation", "CACC-50: delay 0.15->0.8 s; dropout 0->30%", f"Delay +{pct(cdeg['total_delay_veh_h'],c50['total_delay_veh_h']):.1f}%; amplification +{pct(cdeg['disturbance_amplification'],c50['disturbance_amplification']):.1f}%; hard brakes +{pct(cdeg['hard_brake_events'],c50['hard_brake_events']):.1f}%", "ACC fallback is bounded, but stale/lost information erodes performance"],
        ["High demand", "Mainline 1500->1740; ramp 360->480 veh/h", f"CACC-50 exits {high_c['exited_vehicles']:.0f} vs human {high_h['exited_vehicles']:.0f}; delay -{abs(pct(high_c['total_delay_veh_h'],high_h['total_delay_veh_h'])):.1f}%; overflow {high_c['ramp_overflow_vehicles']:.0f} vs {high_h['ramp_overflow_vehicles']:.0f}", "Mobility improves, but boundary storage still binds"],
        ["Stronger brake", "-2.5->-3.5 m/s2 for 4 s", "CACC-50 and ACC-50 delay nearly tie; CACC minimum gap is larger in this run", "One pulse is insufficient for a safety conclusion"],
        ["Forecast missingness", "Every fifth D1 interval missing", "Smoother MAE falls from 1.820 to 1.618", "Counterintuitive result requires multiple missingness patterns"],
        ["TMC failure condition", "Uncalibrated occupancy feedback", "Feedback delay 5.590 vs unmetered 5.442 veh-h", "Retune target/gain only after a binding-demand and detector study"],
    ]
    story += [table(stress_rows, [1.2*inch, 1.65*inch, 2.15*inch, 1.95*inch], font=7.25)]
    story += [P("Failure condition shown to the reviewer", h2), P(f"A controller can look favorable on total delay while increasing hard-braking and relying on safety intervention. At 50% nominal penetration, CACC reduces delay {abs(pct(c50['total_delay_veh_h'], h['total_delay_veh_h'])):.1f}% relative to human driving, yet reports {c50['hard_brake_events']:.0f} hard-brake events versus {h['hard_brake_events']:.0f} and {c50['safety_interventions']:.0f} safety overrides. Its {c50['minimum_gap_m']:.3f}-m minimum gap exceeds the 2.0-m floor and the final collision guard never activates, but those simulation indicators do not establish real-world crash risk or deployment readiness.", callout), PageBreak()]

    # Page 6
    story += [P("5. Interpretation, limitations, and decision", h1)]
    story += [P("Supported claim", h2), P("In this controlled model, delayed acceleration communication provides incremental value over otherwise identical ACC at 50% penetration: it reduces disturbance amplification and enlarges the minimum gap without changing throughput. The gain persists weakly under the stronger-braking test and degrades under communication faults, which is mechanistically consistent with feedforward being removed or delayed.", body)]
    story += [P("Unsupported claims", h2)]
    for text in [
        "CACC is safer than human driving. Minimum gaps and hard-brake events are surrogate simulation indicators, not crash outcomes.",
        "The controller is externally validated. Parameters are literature-informed but not calibrated to measured trajectories.",
        "ALINEA reduces delay in this environment. The implemented loop is operational, but its nominal result is negative.",
        "Missing detector data improve forecasting. The observed reduction is specific to one deterministic removal pattern.",
    ]:
        story.append(P("- " + text, bullet))
    story += [P("Decision: revise before adoption", h2), P("Retain the CACC architecture and safety supervisor, but reject the present gains/headway as deployment-ready. The next design iteration should minimize delay and amplification subject to no increase in hard braking relative to human driving, fewer safety overrides, zero final-guard activations, bounded actuation, and stable performance across arrival/equipment seeds. Then validate the accepted model against measured vehicle trajectories.", callout)]
    limits = [
        ["Limitation", "Consequence", "Next test"],
        ["One lane; insertion merge", "No lane-changing or accepted-gap distribution", "Two-lane merge or calibrated gap acceptance"],
        ["One deterministic demand/assignment seed", "No probabilistic uncertainty interval", "At least 20 paired seeds with common random numbers"],
        ["Simplified actuation/communication", "No actuator saturation map or network burst loss", "Measured ACC/CACC trajectories and burst-error model"],
        ["Virtual occupancy", "Not equivalent to field loop calibration", "Detector placement/target sensitivity under binding demand"],
    ]
    story += [table(limits, [1.55*inch, 2.25*inch, 3.15*inch], font=7.6)]
    story += [P("Reproducibility and individual contribution", h2), P("Ruopeng owns dynamics, arrivals/boundaries, detectors, forecasts, ramp control, ACC/CACC communication, experiments, verification, interpretation, and presentation. Run <font name='Courier'>bash run_all.sh</font>. Versioned configuration, raw CSVs, plots, experiment record, decision trace, source-to-design table, AI disclosure, and contribution record are included. The submitter must add the official UID and personally verify the cited sources and code behavior.", body), PageBreak()]

    # Page 7 References
    story += [P("References", h1)]
    refs = [
        "[1] Treiber, M., Hennecke, A., & Helbing, D. (2000). Congested traffic states in empirical observations and microscopic simulations. <i>Physical Review E, 62</i>, 1805-1824. doi:10.1103/PhysRevE.62.1805.",
        "[2] Ploeg, J., Scheepers, B. T. M., van Nunen, E., van de Wouw, N., & Nijmeijer, H. (2011). Design and experimental evaluation of cooperative adaptive cruise control. <i>14th IEEE ITSC</i>, 260-265.",
        "[3] Milanes, V., & Shladover, S. E. (2014). Modeling cooperative and autonomous adaptive cruise control dynamic responses using experimental data. <i>Transportation Research Part C, 48</i>, 285-300. doi:10.1016/j.trc.2014.09.001.",
        "[4] van Arem, B., van Driel, C. J. G., & Visser, R. (2006). The impact of cooperative adaptive cruise control on traffic-flow characteristics. <i>IEEE Transactions on ITS, 7</i>(4), 429-436. doi:10.1109/TITS.2006.884615.",
        "[5] Federal Highway Administration. (2006). <i>Traffic Detector Handbook: Third Edition, Volume I</i>. FHWA-HRT-06-108.",
        "[6] Smith, B. L., & Demetsky, M. J. (1997). Traffic flow forecasting: Comparison of modeling approaches. <i>Journal of Transportation Engineering, 123</i>(4), 261-266. doi:10.1061/(ASCE)0733-947X(1997)123:4(261).",
        "[7] Papageorgiou, M., Hadj-Salem, H., & Blosseville, J.-M. (1991). ALINEA: A local feedback control law for on-ramp metering. <i>Transportation Research Record, 1320</i>, 58-64.",
        "[8] CEE 181/281. (2026). <i>Fall 2026 Design Project Guide, Revised</i>. Course-provided document.",
    ]
    for ref in refs: story.append(P(ref, refstyle))
    story += [Spacer(1, 10), P("Data and artifact provenance", h2), P("All reported numbers are generated locally from configs/scenarios.json by run_project.py and are preserved in outputs/results. Figures are generated from the corresponding CSVs. No external image or empirical dataset is used. Exact web links are listed in deliverables/references.md.", body), P("AI-use disclosure", h2), P("Generative AI assisted literature discovery, code/document drafting, debugging, and presentation preparation. The project owner remains responsible for verifying equations, units, sources, quantitative claims, and understanding. No fabricated field data or reference is presented.", body), PageBreak()]

    # Page 8 source traceability
    story += [P("Appendix A - Source-to-design and evidence trace", h1)]
    trace_rows = [
        ["Source", "Implemented design choice", "Code / evidence"],
        ["Treiber et al. [1]", "IDM equation, dynamic desired gap, interpretable parameters; local bottleneck", "core.py::idm_acceleration; equilibrium/free-motion/time-step checks"],
        ["Ploeg et al. [2]", "Constant-time-headway spacing; kp=0.2, kd=0.7; predecessor feedforward; 0.15-s delay context", "automated_command; ACC/CACC ablation; decision trace"],
        ["Milanes & Shladover [3]", "First-order vehicle response and empirical motivation for ACC/CACC string comparison", "tau=0.5 s; matched ACC/CACC scenarios"],
        ["van Arem et al. [4]", "Penetration and merging context affect flow-level outcomes", "0/50/100% matrix; on-ramp/high-demand case"],
        ["FHWA [5]", "Explicit detector capabilities: count, speed, occupancy, quality", "DetectorAccumulator; event-log recount; missing record"],
        ["Smith & Demetsky [6]", "Simple historical/moving-average baseline and equal evaluation period", "forecast_records.csv; held-out MAE"],
        ["Papageorgiou et al. [7]", "Integral occupancy feedback for ramp release", "RampMeter; unmetered/fixed/feedback comparison"],
        ["Project Guide [8]", "Interfaces, fairness, residual-demand accounting, Pathway A stress/evaluation, required package", "README; configs; metrics; report; presentation; disclosures"],
    ]
    story += [table(trace_rows, [1.45*inch, 3.35*inch, 2.15*inch], font=7.45)]
    story += [Spacer(1, 8), P("Repository evidence index", h2)]
    evidence = [
        ["Claim", "Primary evidence"],
        ["Communication adds value beyond ACC", "scenario_metrics.csv: nominal_acc_50 vs nominal_cacc_50; plots 01-03"],
        ["Fault handling is explicit", "decision_trace.csv fields message_valid, message_age_s, fallback_state"],
        ["Boundary demand is not dropped", "generated/exited/residual/overflow fields; high-demand cases"],
        ["Observation forecast is fairly evaluated", "forecast_records.csv development/evaluation label and common target times"],
        ["Detector counts are audited", "detector_audit.csv plus detector_audit_clip.mp4"],
        ["Numerical result is not a step-size artifact", "timestep_sensitivity.csv and plot 06"],
        ["Negative evidence is preserved", "TMC comparison, missingness result, hard-braking tradeoff, adoption decision"],
    ]
    story += [table(evidence, [2.45*inch, 4.5*inch], font=7.7), Spacer(1, 10), P("End of report", caption)]

    doc.build(story)
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
