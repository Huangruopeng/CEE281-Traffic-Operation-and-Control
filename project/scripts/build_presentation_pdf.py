#!/usr/bin/env python3
"""Build an eight-slide, eight-minute final presentation as a landscape PDF."""

from pathlib import Path

import pandas as pd
from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, Table, TableStyle

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "deliverables" / "final_presentation.pdf"
RESULTS = ROOT / "outputs" / "results"
PLOTS = ROOT / "outputs" / "plots"
PAGE = (13.333 * inch, 7.5 * inch)

NAVY = colors.HexColor("#17324D")
BLUE = colors.HexColor("#1874CD")
ORANGE = colors.HexColor("#E17C05")
LIGHT = colors.HexColor("#EEF3F7")
MID = colors.HexColor("#D4DFE8")
DARK = colors.HexColor("#263746")
GRAY = colors.HexColor("#667784")
RED = colors.HexColor("#B33A3A")
GREEN = colors.HexColor("#2A7B52")


def para(c, text, x, y_top, w, h, size=17, color=DARK, bold=False, align=TA_LEFT, leading=None):
    style = ParagraphStyle(
        "slide", fontName="Helvetica-Bold" if bold else "Helvetica",
        fontSize=size, leading=leading or size * 1.2,
        textColor=color, alignment=align, spaceAfter=0,
    )
    p = Paragraph(text, style)
    _, ph = p.wrap(w, h)
    p.drawOn(c, x, y_top - ph)
    return ph


def title(c, kicker, heading, slide_no):
    c.setFillColor(NAVY)
    c.rect(0, PAGE[1] - 0.18 * inch, PAGE[0], 0.18 * inch, fill=1, stroke=0)
    para(c, kicker.upper(), 0.62 * inch, PAGE[1] - 0.42 * inch, 5.8 * inch, 0.25 * inch, 10, BLUE, True)
    para(c, heading, 0.62 * inch, PAGE[1] - 0.72 * inch, 12.0 * inch, 0.6 * inch, 25, NAVY, True, leading=28)
    c.setStrokeColor(MID)
    c.setLineWidth(0.6)
    c.line(0.62 * inch, 0.42 * inch, 12.72 * inch, 0.42 * inch)
    para(c, "CEE 281 | Pathway A | Ruopeng", 0.62 * inch, 0.34 * inch, 5 * inch, 0.2 * inch, 8.5, GRAY)
    para(c, str(slide_no), 12.25 * inch, 0.34 * inch, 0.45 * inch, 0.2 * inch, 8.5, GRAY, align=TA_CENTER)


def rounded_box(c, x, y, w, h, fill=LIGHT, stroke=MID, radius=10):
    c.setFillColor(fill)
    c.setStrokeColor(stroke)
    c.setLineWidth(0.8)
    c.roundRect(x, y, w, h, radius, fill=1, stroke=1)


def image_fit(c, path, x, y, w, h):
    with PILImage.open(path) as im:
        iw, ih = im.size
    scale = min(w / iw, h / ih)
    dw, dh = iw * scale, ih * scale
    c.drawImage(str(path), x + (w - dw) / 2, y + (h - dh) / 2, dw, dh, preserveAspectRatio=True, mask="auto")


def draw_table(c, rows, x, y_top, widths, font=10):
    head = ParagraphStyle("th", fontName="Helvetica-Bold", fontSize=font, leading=font + 2, textColor=colors.white)
    cell = ParagraphStyle("td", fontName="Helvetica", fontSize=font, leading=font + 2, textColor=DARK)
    wrapped = [[Paragraph(str(v), head if i == 0 else cell) for v in row] for i, row in enumerate(rows)]
    t = Table(wrapped, colWidths=widths)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("GRID", (0, 0), (-1, -1), 0.45, MID),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7F9FB")]),
    ]))
    _, th = t.wrap(sum(widths), 5 * inch)
    t.drawOn(c, x, y_top - th)
    return th


def percent(new, old):
    return 100 * (new - old) / old


def build():
    m = pd.read_csv(RESULTS / "scenario_metrics.csv").set_index("scenario_id")
    f = pd.read_csv(RESULTS / "forecast_metrics.csv")
    audit = pd.read_csv(RESULTS / "detector_audit.csv")
    dtrace = pd.read_csv(ROOT / "outputs/data/nominal_cacc_50/decision_trace.csv")
    trace = dtrace[(dtrace.issue_time_s == 8.0) & (dtrace.vehicle_id == "veh_0003")].iloc[0]
    fallback = dtrace[(dtrace.issue_time_s == 8.0) & (dtrace.fallback_state == "ACC_fallback")].iloc[0]
    human = m.loc["nominal_human"]
    acc50 = m.loc["nominal_acc_50"]
    cacc50 = m.loc["nominal_cacc_50"]
    degraded = m.loc["degraded_cacc_50"]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(OUT), pagesize=PAGE)
    c.setTitle("CEE 281 Pathway A - CACC Control")

    # Slide 1
    c.setFillColor(NAVY)
    c.rect(0, 0, PAGE[0], PAGE[1], fill=1, stroke=0)
    c.setFillColor(ORANGE)
    c.rect(0.65 * inch, 6.77 * inch, 1.15 * inch, 0.09 * inch, fill=1, stroke=0)
    para(c, "CEE 281 FINAL DESIGN | PATHWAY A", 0.65 * inch, 6.55 * inch, 7 * inch, 0.3 * inch, 12, colors.HexColor("#AFC6DA"), True)
    para(c, "CACC adds value over ACC -<br/>but the design is not adoption-ready", 0.65 * inch, 5.98 * inch, 8.0 * inch, 1.5 * inch, 34, colors.white, True, leading=39)
    para(c, "A bounded mixed-traffic test of predecessor-acceleration feedforward", 0.65 * inch, 4.05 * inch, 7.4 * inch, 0.5 * inch, 18, colors.HexColor("#D5E2EC"))
    rounded_box(c, 8.8 * inch, 1.35 * inch, 3.8 * inch, 4.65 * inch, fill=colors.HexColor("#214866"), stroke=colors.HexColor("#446B87"), radius=14)
    para(c, "50% CACC vs ACC", 9.18 * inch, 5.55 * inch, 3.05 * inch, 0.3 * inch, 13, colors.HexColor("#BFD3E2"), True, TA_CENTER)
    para(c, f"{abs(percent(cacc50.disturbance_amplification, acc50.disturbance_amplification)):.1f}%", 9.15 * inch, 4.75 * inch, 3.1 * inch, 0.7 * inch, 42, colors.white, True, TA_CENTER)
    para(c, "lower disturbance amplification", 9.15 * inch, 4.08 * inch, 3.1 * inch, 0.5 * inch, 14, colors.white, align=TA_CENTER)
    para(c, f"+{percent(cacc50.minimum_gap_m, acc50.minimum_gap_m):.1f}% min gap<br/>+{percent(cacc50.total_delay_veh_h, acc50.total_delay_veh_h):.1f}% delay<br/>throughput unchanged", 9.15 * inch, 3.35 * inch, 3.1 * inch, 1.0 * inch, 15, colors.white, align=TA_CENTER, leading=22)
    c.setFillColor(ORANGE)
    c.roundRect(9.15 * inch, 1.7 * inch, 3.1 * inch, 0.55 * inch, 8, fill=1, stroke=0)
    para(c, "REVISE BEFORE ADOPTION", 9.23 * inch, 2.08 * inch, 2.95 * inch, 0.3 * inch, 13, colors.white, True, TA_CENTER)
    para(c, "Ruopeng (individual project; UID to be added)", 0.65 * inch, 0.6 * inch, 7 * inch, 0.3 * inch, 10, colors.HexColor("#AFC6DA"))
    c.showPage()

    # Slide 2
    title(c, "Design", "One common environment; one isolated controller change", 2)
    y = 5.58 * inch
    steps = [
        ("Arrivals", "1500 + 360 veh/h"), ("Mixed vehicles", "IDM / ACC / CACC"),
        ("Ramp + bottleneck", "queue, storage, 18 m/s zone"),
        ("Observe + act", "D1/D2, forecast, ramp meter"),
        ("Evaluate", "delay, flow, gaps, amplification"),
    ]
    x = 0.6 * inch
    for i, (head, sub) in enumerate(steps):
        w = 2.18 * inch
        rounded_box(c, x, y - 1.15 * inch, w, 1.15 * inch, fill=colors.white, stroke=BLUE)
        para(c, head, x + 0.12 * inch, y - 0.26 * inch, w - 0.24 * inch, 0.28 * inch, 14, NAVY, True, TA_CENTER)
        para(c, sub, x + 0.12 * inch, y - 0.63 * inch, w - 0.24 * inch, 0.45 * inch, 10.5, GRAY, align=TA_CENTER, leading=13)
        if i < len(steps) - 1:
            c.setStrokeColor(ORANGE)
            c.setLineWidth(2)
            c.line(x + w + 0.04 * inch, y - 0.57 * inch, x + w + 0.28 * inch, y - 0.57 * inch)
            c.line(x + w + 0.22 * inch, y - 0.63 * inch, x + w + 0.28 * inch, y - 0.57 * inch)
            c.line(x + w + 0.22 * inch, y - 0.51 * inch, x + w + 0.28 * inch, y - 0.57 * inch)
        x += 2.52 * inch
    rounded_box(c, 0.72 * inch, 1.12 * inch, 11.88 * inch, 2.9 * inch, fill=LIGHT, stroke=MID)
    para(c, "Fair comparison contract", 1.0 * inch, 3.68 * inch, 3.2 * inch, 0.35 * inch, 18, BLUE, True)
    bullets = [
        "Same initial platoon, arrival schedules, seed, disturbance, ramp logic, and 900-s horizon",
        "0%, 50%, 100% equipment; noncooperative ACC isolates the value of communication",
        "Demand stops at 600 s; residual queues and ramp overflow remain in the evaluation record",
        "Simulator truth scores behavior only - it never enters a vehicle controller",
    ]
    yy = 3.2 * inch
    for bullet in bullets:
        c.setFillColor(ORANGE)
        c.circle(1.05 * inch, yy - 0.06 * inch, 3, fill=1, stroke=0)
        para(c, bullet, 1.2 * inch, yy + 0.06 * inch, 10.9 * inch, 0.42 * inch, 14, DARK, leading=17)
        yy -= 0.58 * inch
    c.showPage()

    # Slide 3
    title(c, "Mechanism", "CACC = bounded ACC + one delayed feedforward term", 3)
    cards = [
        (0.65, "Human baseline", "IDM", "a[1-(v/v0)^delta-(s*/s)^2]", MID, colors.white),
        (4.78, "ACC", "local sensing", "speed control + kp gap error + kd relative speed", ORANGE, colors.white),
        (8.91, "CACC", "ACC + communication", "+ 0.8 a_lead(t-delay)<br/>if immediate leader is equipped", BLUE, LIGHT),
    ]
    for x0, head, sub, formula, stroke, fill in cards:
        rounded_box(c, x0 * inch, 3.65 * inch, 3.7 * inch, 2.15 * inch, fill=fill, stroke=stroke)
        para(c, head, (x0 + 0.27) * inch, 5.48 * inch, 3.15 * inch, 0.35 * inch, 18, NAVY, True)
        para(c, sub, (x0 + 0.27) * inch, 4.98 * inch, 3.15 * inch, 0.35 * inch, 15, stroke if stroke != MID else ORANGE, True)
        para(c, formula, (x0 + 0.27) * inch, 4.47 * inch, 3.15 * inch, 0.7 * inch, 12.5, DARK, leading=17)
    rounded_box(c, 0.9 * inch, 1.05 * inch, 11.55 * inch, 1.75 * inch, fill=NAVY, stroke=NAVY)
    labels = [(1.25, "0.1-s update"), (3.45, "clip [-4, 2] m/s2"), (5.9, "0.5-s actuator"), (8.2, "2.0-m safety floor"), (10.15, "ACC fallback")]
    for x0, label in labels:
        para(c, label, x0 * inch, 2.25 * inch, 1.9 * inch, 0.4 * inch, 16, colors.HexColor("#FFD493") if "fallback" in label else colors.white, True, TA_CENTER)
    para(c, "Measured: ego speed, gap, relative speed", 1.25 * inch, 1.68 * inch, 4.4 * inch, 0.35 * inch, 12, colors.HexColor("#D5E2EC"), align=TA_CENTER)
    para(c, "Communicated: delayed predecessor acceleration only", 6.25 * inch, 1.68 * inch, 5.3 * inch, 0.35 * inch, 12, colors.HexColor("#D5E2EC"), align=TA_CENTER)
    c.showPage()

    # Slide 4
    title(c, "Trace", "The decision record proves what the controller knew", 4)
    rows = [
        ["t (s)", "Vehicle", "Ego v", "Gap", "Rel. v", "Msg a / age", "Command", "State"],
        [f"{trace.issue_time_s:.1f}", trace.vehicle_id, f"{trace.measured_ego_speed_mps:.3f}", f"{trace.measured_gap_m:.3f}", f"{trace.measured_relative_speed_mps:.3f}", f"{trace.communicated_predecessor_accel_mps2:.3f} / {trace.message_age_s:.1f}s", f"{trace.command_mps2:.3f}", trace.fallback_state],
        [f"{fallback.issue_time_s:.1f}", fallback.vehicle_id, f"{fallback.measured_ego_speed_mps:.3f}", f"{fallback.measured_gap_m:.3f}", f"{fallback.measured_relative_speed_mps:.3f}", "none", f"{fallback.command_mps2:.3f}", fallback.fallback_state],
    ]
    draw_table(c, rows, 0.65 * inch, 5.75 * inch, [0.65*inch,1.05*inch,1.05*inch,1.0*inch,1.0*inch,1.65*inch,1.1*inch,1.5*inch], font=10)
    rounded_box(c, 0.8 * inch, 1.22 * inch, 5.7 * inch, 2.9 * inch, fill=LIGHT, stroke=BLUE)
    para(c, "CACC row", 1.08 * inch, 3.82 * inch, 2.0 * inch, 0.35 * inch, 18, BLUE, True)
    para(c, "The leader message is 0.2 s old because the simulation stores only past messages. Its negative acceleration adds braking before the local gap closes further.", 1.08 * inch, 3.28 * inch, 5.15 * inch, 1.25 * inch, 15, DARK, leading=19)
    rounded_box(c, 6.85 * inch, 1.22 * inch, 5.7 * inch, 2.9 * inch, fill=colors.HexColor("#FFF6E8"), stroke=ORANGE)
    para(c, "Fallback row", 7.13 * inch, 3.82 * inch, 2.2 * inch, 0.35 * inch, 18, ORANGE, True)
    para(c, "The immediate predecessor is not communicating. Feedforward becomes zero, the local ACC law remains active, and command bounds are unchanged.", 7.13 * inch, 3.28 * inch, 5.15 * inch, 1.25 * inch, 15, DARK, leading=19)
    para(c, "Not available: future trajectories, brake schedule, downstream truth, or uncommunicated human state.", 0.85 * inch, 0.88 * inch, 11.7 * inch, 0.35 * inch, 13, RED, True, TA_CENTER)
    c.showPage()

    # Slide 5
    title(c, "Nominal result", "Communication improves matched ACC - not every baseline metric", 5)
    image_fit(c, PLOTS / "02_disturbance_speed_traces.png", 0.65*inch, 2.72*inch, 12.0*inch, 3.0*inch)
    rows = [
        ["Case", "Delay (veh-h)", "Amplification", "Min gap (m)", "Hard brakes"],
        ["Human 0%", f"{human.total_delay_veh_h:.3f}", f"{human.disturbance_amplification:.3f}", f"{human.minimum_gap_m:.3f}", f"{human.hard_brake_events:.0f}"],
        ["ACC 50%", f"{acc50.total_delay_veh_h:.3f}", f"{acc50.disturbance_amplification:.3f}", f"{acc50.minimum_gap_m:.3f}", f"{acc50.hard_brake_events:.0f}"],
        ["CACC 50%", f"{cacc50.total_delay_veh_h:.3f}", f"{cacc50.disturbance_amplification:.3f}", f"{cacc50.minimum_gap_m:.3f}", f"{cacc50.hard_brake_events:.0f}"],
    ]
    draw_table(c, rows, 0.78*inch, 2.68*inch, [1.6*inch,1.65*inch,1.65*inch,1.55*inch,1.4*inch], font=10.5)
    rounded_box(c, 8.85*inch, 0.93*inch, 3.65*inch, 1.76*inch, fill=LIGHT, stroke=BLUE)
    para(c, "Narrow supported claim", 9.1*inch, 2.42*inch, 3.15*inch, 0.3*inch, 14, BLUE, True, TA_CENTER)
    para(c, "CACC reduces amplification<br/>12.5% vs matched ACC.<br/>Human IDM is already stable.", 9.1*inch, 2.03*inch, 3.15*inch, 0.9*inch, 14, NAVY, True, TA_CENTER, leading=18)
    c.showPage()

    # Slide 6
    title(c, "Stress", "Mobility benefit persists; degraded messages erode it", 6)
    image_fit(c, PLOTS / "04_stress_tests.png", 0.6*inch, 1.75*inch, 7.55*inch, 4.0*inch)
    rounded_box(c, 8.35*inch, 3.55*inch, 4.35*inch, 2.2*inch, fill=LIGHT, stroke=BLUE)
    para(c, "High demand", 8.65*inch, 5.43*inch, 3.75*inch, 0.35*inch, 18, BLUE, True)
    para(c, f"CACC exits <b>{m.loc['high_demand_cacc_50','exited_vehicles']:.0f}</b> vs human <b>{m.loc['high_demand_human','exited_vehicles']:.0f}</b><br/>delay {abs(percent(m.loc['high_demand_cacc_50','total_delay_veh_h'], m.loc['high_demand_human','total_delay_veh_h'])):.1f}% lower<br/>hard brakes {m.loc['high_demand_cacc_50','hard_brake_events']:.0f} vs {m.loc['high_demand_human','hard_brake_events']:.0f}", 8.65*inch, 4.9*inch, 3.75*inch, 1.1*inch, 15, DARK, leading=21)
    rounded_box(c, 8.35*inch, 1.05*inch, 4.35*inch, 2.1*inch, fill=colors.HexColor("#FFF6E8"), stroke=ORANGE)
    para(c, "0.8-s delay + 30% dropout", 8.65*inch, 2.85*inch, 3.75*inch, 0.35*inch, 17, ORANGE, True)
    para(c, f"delay +{percent(degraded.total_delay_veh_h,cacc50.total_delay_veh_h):.1f}%<br/>amplification +{percent(degraded.disturbance_amplification,cacc50.disturbance_amplification):.1f}%<br/>hard brakes +{percent(degraded.hard_brake_events,cacc50.hard_brake_events):.1f}%", 8.65*inch, 2.36*inch, 3.75*inch, 1.0*inch, 15, DARK, leading=20)
    c.showPage()

    # Slide 7
    title(c, "Evidence quality", "Checks passed; two negative results remain visible", 7)
    image_fit(c, PLOTS / "06_sensitivity_tmc.png", 0.55*inch, 2.85*inch, 7.0*inch, 2.85*inch)
    image_fit(c, PLOTS / "05_forecast_evaluation.png", 7.35*inch, 2.85*inch, 5.45*inch, 2.85*inch)
    cards = [
        ("Safety checks", "All final gaps >= 2.0 m; final numerical guard activations = 0", GREEN),
        ("Detector audit", f"{len(audit)} intervals; maximum recount error = {audit.count_error_veh.abs().max():.0f}", GREEN),
        ("Missingness", f"Exp. smoothing MAE {f.iloc[0].exponential_smoothing_mae_veh_per_interval:.3f} -> {f.iloc[1].exponential_smoothing_mae_veh_per_interval:.3f}; pattern-specific", ORANGE),
        ("Ramp control", "Feedback 5.590 vs unmetered 5.442 veh-h; functional negative result", ORANGE),
    ]
    x = 0.66 * inch
    for head, text, color in cards:
        rounded_box(c, x, 0.92*inch, 2.95*inch, 1.62*inch, fill=colors.white, stroke=color)
        para(c, head, x+0.18*inch, 2.28*inch, 2.58*inch, 0.3*inch, 14, color, True, TA_CENTER)
        para(c, text, x+0.18*inch, 1.88*inch, 2.58*inch, 0.75*inch, 11, DARK, align=TA_CENTER, leading=14)
        x += 3.13 * inch
    c.showPage()

    # Slide 8
    title(c, "Decision", "Keep the architecture; reject the present tuning", 8)
    decisions = [
        (0.72, "SUPPORTED", "Predecessor acceleration has incremental value over matched ACC.", GREEN, colors.HexColor("#EAF5EF")),
        (4.82, "NOT SUPPORTED", "Crash reduction, external validation, or dominance over human driving.", RED, colors.HexColor("#FFF0F0")),
        (8.92, "NEXT TEST", "Constrained gain/headway tuning across paired random seeds and measured trajectories.", ORANGE, colors.HexColor("#FFF6E8")),
    ]
    for x0, head, text, stroke, fill in decisions:
        rounded_box(c, x0*inch, 3.87*inch, 3.7*inch, 1.78*inch, fill=fill, stroke=stroke)
        para(c, head, (x0+0.28)*inch, 5.32*inch, 3.1*inch, 0.3*inch, 15, stroke, True, TA_CENTER)
        para(c, text, (x0+0.28)*inch, 4.82*inch, 3.1*inch, 0.85*inch, 13.5, NAVY, True, TA_CENTER, leading=16)
    rounded_box(c, 0.72*inch, 1.28*inch, 11.9*inch, 2.05*inch, fill=NAVY, stroke=NAVY)
    para(c, "Adoption gate", 1.03*inch, 2.96*inch, 2.0*inch, 0.35*inch, 17, colors.HexColor("#FFD493"), True)
    para(c, "No increase in hard braking | fewer safety overrides | zero final-guard activations | stable across paired seeds | measured-trajectory validation", 1.03*inch, 2.45*inch, 11.25*inch, 0.9*inch, 18, colors.white, True, TA_CENTER, leading=24)
    para(c, "Sources: Treiber et al. (2000); Ploeg et al. (2011); Milanes & Shladover (2014); van Arem et al. (2006); FHWA (2006); Papageorgiou et al. (1991).", 1.0*inch, 0.82*inch, 11.3*inch, 0.3*inch, 8.5, GRAY, align=TA_CENTER)
    c.showPage()

    c.save()
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    build()
