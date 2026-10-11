"use strict";

const $ = (id) => document.getElementById(id);
const els = {
  scenario: $("scenarioSelect"), speed: $("speedSelect"), play: $("playBtn"), playIcon: $("playIcon"),
  playLabel: $("playLabel"), reset: $("resetBtn"), step: $("stepBtn"), record: $("recordBtn"),
  timeline: $("timeline"), timelineCurrent: $("timelineCurrent"), timelineEnd: $("timelineEnd"), live: $("liveBtn"),
  road: $("roadCanvas"), speedChart: $("speedChart"), queueChart: $("queueChart"), tip: $("hoverTip"),
  simClock: $("simClock"), connection: $("connectionStatus"), liveDot: $("liveDot"), toast: $("toast"),
};

let config = null;
let scenarios = new Map();
let state = null;
let selectedVehicleId = null;
let hitboxes = [];
let history = [];
let requestInFlight = false;
let timelineDragging = false;
let recorder = null;
let recordedChunks = [];
let toastTimer = null;

const colors = { human: "#98a8b3", acc: "#f0b763", cacc: "#54d6da", coral: "#ff756f", grid: "rgba(137,164,179,.10)" };

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    cache: "no-store",
    ...options,
  });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error || `HTTP ${response.status}`);
  return payload;
}

function notify(message) {
  els.toast.textContent = message;
  els.toast.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => els.toast.classList.remove("show"), 2800);
}

function setConnected(ok) {
  els.connection.textContent = ok ? "LOCAL ENGINE" : "ENGINE OFFLINE";
  els.liveDot.parentElement.classList.toggle("offline", !ok);
}

function formatTime(seconds, compact = false) {
  const value = Math.max(0, Number(seconds) || 0);
  const minutes = Math.floor(value / 60);
  const secs = value - minutes * 60;
  return compact ? `${String(minutes).padStart(2, "0")}:${String(Math.floor(secs)).padStart(2, "0")}` : `${String(minutes).padStart(2, "0")}:${secs.toFixed(1).padStart(4, "0")}`;
}

function fmt(value, digits = 1, fallback = "—") {
  return value === null || value === undefined || Number.isNaN(Number(value)) ? fallback : Number(value).toFixed(digits);
}

function resizeCanvas(canvas) {
  const rect = canvas.getBoundingClientRect();
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  const width = Math.max(1, Math.round(rect.width * dpr));
  const height = Math.max(1, Math.round(rect.height * dpr));
  if (canvas.width !== width || canvas.height !== height) {
    canvas.width = width;
    canvas.height = height;
  }
  const ctx = canvas.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  return { ctx, width: rect.width, height: rect.height };
}

function roundedRect(ctx, x, y, width, height, radius) {
  const r = Math.min(radius, width / 2, height / 2);
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + width, y, x + width, y + height, r);
  ctx.arcTo(x + width, y + height, x, y + height, r);
  ctx.arcTo(x, y + height, x, y, r);
  ctx.arcTo(x, y, x + width, y, r);
  ctx.closePath();
}

function drawRoad() {
  const { ctx, width: w, height: h } = resizeCanvas(els.road);
  ctx.clearRect(0, 0, w, h);
  const bg = ctx.createLinearGradient(0, 0, 0, h);
  bg.addColorStop(0, "#0a151d"); bg.addColorStop(1, "#071017");
  ctx.fillStyle = bg; ctx.fillRect(0, 0, w, h);

  for (let x = 0; x <= w; x += 42) {
    ctx.strokeStyle = colors.grid; ctx.lineWidth = .5; ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke();
  }
  for (let y = 0; y <= h; y += 42) {
    ctx.strokeStyle = colors.grid; ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke();
  }
  if (!state) return;

  const road = state.road;
  const left = 34, right = w - 34, roadY = h * .47;
  const viewSpanM = Math.min(650, Math.max(140, (right - left) / 1.55));
  const viewCenterM = road.ramp_position_m + 130;
  const viewStartM = Math.max(0, Math.min(road.length_m - viewSpanM, viewCenterM - viewSpanM / 2));
  const viewEndM = viewStartM + viewSpanM;
  const mapX = (x) => left + ((x - viewStartM) / viewSpanM) * (right - left);
  $("viewStartLabel").textContent = `MERGE DETAIL · x = ${Math.round(viewStartM)} m`;
  $("viewEndLabel").textContent = `x = ${Math.round(viewEndM)} m · FIXED VEHICLE SCALE`;
  const bottleStart = mapX(road.bottleneck_start_m), bottleEnd = mapX(road.bottleneck_end_m);

  if (road.bottleneck_end_m >= viewStartM && road.bottleneck_start_m <= viewEndM) {
    const clippedStart = Math.max(left, bottleStart), clippedEnd = Math.min(right, bottleEnd);
    ctx.fillStyle = "rgba(240,183,99,.055)"; ctx.fillRect(clippedStart, roadY - 73, clippedEnd - clippedStart, 146);
    ctx.strokeStyle = "rgba(240,183,99,.25)"; ctx.setLineDash([4, 5]);
    ctx.strokeRect(clippedStart, roadY - 73, clippedEnd - clippedStart, 146); ctx.setLineDash([]);
    ctx.fillStyle = "rgba(240,183,99,.55)"; ctx.font = "9px ui-monospace, monospace";
    ctx.fillText(`BOTTLENECK · T = ${road.bottleneck_time_gap_s ?? "?"} s`, clippedStart + 8, roadY - 57);
  }

  const rampMerge = mapX(road.ramp_position_m);
  const rampCurve = {
    p0: { x: left + 10, y: h * .82 },
    p1: { x: left + (right - left) * .30, y: h * .82 },
    p2: { x: mapX(Math.max(0, road.ramp_position_m - 125)), y: roadY + 40 },
    p3: { x: mapX(road.ramp_position_m + 25), y: roadY },
  };
  const cubicPoint = (curve, t) => {
    const u = 1 - t;
    return {
      x: u ** 3 * curve.p0.x + 3 * u ** 2 * t * curve.p1.x + 3 * u * t ** 2 * curve.p2.x + t ** 3 * curve.p3.x,
      y: u ** 3 * curve.p0.y + 3 * u ** 2 * t * curve.p1.y + 3 * u * t ** 2 * curve.p2.y + t ** 3 * curve.p3.y,
    };
  };
  const cubicAngle = (curve, t) => {
    const u = 1 - t;
    const dx = 3 * u ** 2 * (curve.p1.x - curve.p0.x) + 6 * u * t * (curve.p2.x - curve.p1.x) + 3 * t ** 2 * (curve.p3.x - curve.p2.x);
    const dy = 3 * u ** 2 * (curve.p1.y - curve.p0.y) + 6 * u * t * (curve.p2.y - curve.p1.y) + 3 * t ** 2 * (curve.p3.y - curve.p2.y);
    return Math.atan2(dy, dx);
  };
  const traceRamp = () => {
    ctx.beginPath(); ctx.moveTo(rampCurve.p0.x, rampCurve.p0.y);
    ctx.bezierCurveTo(rampCurve.p1.x, rampCurve.p1.y, rampCurve.p2.x, rampCurve.p2.y, rampCurve.p3.x, rampCurve.p3.y);
  };
  ctx.lineCap = "round";
  ctx.strokeStyle = "#1b2a34"; ctx.lineWidth = 42; traceRamp(); ctx.stroke();
  ctx.strokeStyle = "rgba(200,216,224,.28)"; ctx.lineWidth = 1; ctx.setLineDash([8, 9]); traceRamp(); ctx.stroke(); ctx.setLineDash([]);
  ctx.fillStyle = "rgba(174,191,200,.48)"; ctx.font = "8px ui-monospace, monospace"; ctx.textAlign = "left";
  ctx.fillText("ON-RAMP", rampCurve.p0.x + 3, rampCurve.p0.y + 31);

  ctx.strokeStyle = "#1c2d38"; ctx.lineWidth = 64; ctx.beginPath(); ctx.moveTo(left, roadY); ctx.lineTo(right, roadY); ctx.stroke();
  ctx.strokeStyle = "rgba(215,227,232,.32)"; ctx.lineWidth = 1; ctx.setLineDash([12, 12]); ctx.beginPath(); ctx.moveTo(left, roadY); ctx.lineTo(right, roadY); ctx.stroke(); ctx.setLineDash([]);
  ctx.strokeStyle = "rgba(215,227,232,.23)"; ctx.beginPath(); ctx.moveTo(left, roadY - 31); ctx.lineTo(right, roadY - 31); ctx.moveTo(left, roadY + 31); ctx.lineTo(right, roadY + 31); ctx.stroke();

  for (const detector of state.detectors) {
    if (detector.position_m < viewStartM || detector.position_m > viewEndM) continue;
    const x = mapX(detector.position_m);
    ctx.strokeStyle = "rgba(84,214,218,.65)"; ctx.lineWidth = 1; ctx.setLineDash([3, 4]);
    ctx.beginPath(); ctx.moveTo(x, roadY - 44); ctx.lineTo(x, roadY + 44); ctx.stroke(); ctx.setLineDash([]);
    ctx.fillStyle = "#54d6da"; ctx.fillRect(x - 3, roadY - 49, 6, 3);
    ctx.fillStyle = "rgba(173,222,225,.8)"; ctx.font = "9px ui-monospace, monospace"; ctx.textAlign = "center";
    ctx.fillText(detector.sensor_id, x, roadY - 55);
  }

  const meterPoint = cubicPoint(rampCurve, .56);
  const meterX = meterPoint.x, meterY = meterPoint.y;
  ctx.fillStyle = "#8a7ce3"; ctx.fillRect(meterX, meterY - 18, 2, 20);
  ctx.beginPath(); ctx.arc(meterX + 1, meterY - 19, 4, 0, Math.PI * 2);
  ctx.fillStyle = state.queues.ramp ? "#ff756f" : "#54d6da"; ctx.fill();
  ctx.textAlign = "left"; ctx.fillStyle = "rgba(174,191,200,.65)"; ctx.font = "8px ui-monospace, monospace"; ctx.fillText("R1 METER", meterX + 8, meterY - 16);

  ctx.strokeStyle = "rgba(240,183,99,.45)"; ctx.lineWidth = 1;
  ctx.beginPath(); ctx.moveTo(rampMerge - 8, roadY + 22); ctx.lineTo(rampMerge + 12, roadY + 8); ctx.stroke();
  ctx.fillStyle = "rgba(240,183,99,.62)"; ctx.font = "8px ui-monospace, monospace"; ctx.fillText("MERGE", rampMerge + 17, roadY + 24);

  const queueShown = Math.min(state.queues.ramp, 10);
  for (let i = 0; i < queueShown; i++) {
    const p = Math.max(.04, .49 - i * .045);
    const point = cubicPoint(rampCurve, p);
    ctx.save(); ctx.translate(point.x, point.y); ctx.rotate(cubicAngle(rampCurve, p));
    ctx.fillStyle = "#9e8cff"; roundedRect(ctx, -3.5, -2.5, 7, 5, 2); ctx.fill(); ctx.restore();
  }
  if (state.queues.ramp > queueShown) {
    ctx.fillStyle = "rgba(194,183,255,.75)"; ctx.font = "8px ui-monospace, monospace";
    ctx.fillText(`+${state.queues.ramp - queueShown}`, rampCurve.p0.x - 2, rampCurve.p0.y - 11);
  }

  const sorted = [...state.vehicles].sort((a, b) => a.x_m - b.x_m);
  const visualPositions = new Map();
  for (const vehicle of sorted) {
    let visual = { x: mapX(vehicle.x_m), y: roadY, angle: 0 };
    if (vehicle.source === "ramp" && vehicle.age_since_spawn_s < 1.5) {
      // The model inserts the ramp vehicle at x=ramp_position when the accepted
      // gap begins affecting mainline controllers.  Keep that exact x here and
      // animate only the lateral crossing so braking and merging are concurrent.
      const rawProgress = Math.max(0, Math.min(1, vehicle.age_since_spawn_s / 1.5));
      const progress = 1 - (1 - rawProgress) ** 2;
      visual = {
        x: mapX(vehicle.x_m),
        y: roadY + 22 * (1 - progress),
        angle: -.58 * (1 - progress),
      };
    }
    visualPositions.set(vehicle.vehicle_id, visual);
  }

  for (let i = 0; i < sorted.length - 1; i++) {
    const follower = sorted[i], leader = sorted[i + 1];
    if (follower.controller === "cacc" && follower.message_valid && leader.x_m - follower.x_m < 190) {
      const followerPoint = visualPositions.get(follower.vehicle_id), leaderPoint = visualPositions.get(leader.vehicle_id);
      ctx.strokeStyle = "rgba(84,214,218,.36)"; ctx.lineWidth = 1; ctx.setLineDash([2, 3]);
      ctx.beginPath(); ctx.moveTo(followerPoint.x, followerPoint.y - 11); ctx.lineTo(leaderPoint.x, leaderPoint.y - 11); ctx.stroke(); ctx.setLineDash([]);
    }
  }

  hitboxes = [];
  for (const vehicle of sorted) {
    const visual = visualPositions.get(vehicle.vehicle_id);
    const x = visual.x, y = visual.y;
    if (x < left - 12 || x > right + 12) continue;
    // Every active vehicle uses one fixed, normal-size body. Disturbance and
    // braking states are communicated with outlines/lights, never by resizing.
    const carW = 10;
    const carH = 8;
    const color = colors[vehicle.controller] || colors.human;
    ctx.save(); ctx.translate(x, y); ctx.rotate(visual.angle);
    if (vehicle.hard_braking || vehicle.is_disturbance_vehicle) {
      ctx.shadowColor = colors.coral; ctx.shadowBlur = 11;
      ctx.strokeStyle = colors.coral; ctx.lineWidth = 2;
      roundedRect(ctx, -carW / 2 - 2, -carH / 2 - 2, carW + 4, carH + 4, 3); ctx.stroke();
      ctx.shadowBlur = 0;
    }
    ctx.fillStyle = color;
    roundedRect(ctx, -carW / 2, -carH / 2, carW, carH, 2); ctx.fill();
    ctx.fillStyle = "rgba(5,13,18,.72)"; ctx.fillRect(carW / 2 - 2, -carH / 2 + 2, 1, carH - 4);
    if (vehicle.equipped) { ctx.fillStyle = "#f1fbff"; ctx.beginPath(); ctx.arc(-1, 0, 1.1, 0, Math.PI * 2); ctx.fill(); }
    if (vehicle.acceleration_mps2 < -.15) {
      ctx.fillStyle = "#ff4d48";
      ctx.shadowColor = "#ff4d48"; ctx.shadowBlur = 5;
      ctx.fillRect(-carW / 2 - .5, -carH / 2 + 1, 1.5, 1.5);
      ctx.fillRect(-carW / 2 - .5, carH / 2 - 2.5, 1.5, 1.5);
      ctx.shadowBlur = 0;
    }
    if (vehicle.vehicle_id === selectedVehicleId) {
      ctx.strokeStyle = "#ffffff"; ctx.lineWidth = 1; ctx.setLineDash([2, 2]);
      ctx.strokeRect(-carW / 2 - 5, -carH / 2 - 5, carW + 10, carH + 10); ctx.setLineDash([]);
    }
    ctx.restore();
    hitboxes.push({ x: x - 9, y: y - 10, w: 18, h: 20, vehicle });
  }

  if (state.disturbance.active) {
    ctx.fillStyle = "rgba(255,117,111,.9)"; ctx.font = "700 9px ui-monospace, monospace"; ctx.textAlign = "left";
    ctx.fillText("● LEAD-VEHICLE BRAKE ACTIVE", left + 3, 24);
  }
  ctx.textAlign = "right"; ctx.fillStyle = "rgba(148,169,181,.55)"; ctx.font = "9px ui-monospace, monospace";
  ctx.fillText(`${state.vehicles.length} ACTIVE · ${fmt(state.metrics.mean_speed_mps * 3.6, 1)} km/h`, right, 24);
  ctx.textAlign = "left";
}

function drawChart(canvas, values, color, maxValue, suffix) {
  const { ctx, width: w, height: h } = resizeCanvas(canvas);
  ctx.clearRect(0, 0, w, h); ctx.fillStyle = "#0a141c"; ctx.fillRect(0, 0, w, h);
  const pad = { left: 34, right: 12, top: 14, bottom: 22 };
  const pw = w - pad.left - pad.right, ph = h - pad.top - pad.bottom;
  ctx.font = "8px ui-monospace, monospace"; ctx.fillStyle = "rgba(145,166,178,.6)"; ctx.textAlign = "right";
  for (let i = 0; i <= 3; i++) {
    const y = pad.top + ph * i / 3;
    ctx.strokeStyle = "rgba(145,166,178,.10)"; ctx.lineWidth = 1; ctx.beginPath(); ctx.moveTo(pad.left, y); ctx.lineTo(w - pad.right, y); ctx.stroke();
    ctx.fillText(`${Math.round(maxValue * (1 - i / 3))}${suffix}`, pad.left - 6, y + 3);
  }
  if (values.length < 2) return;
  const t0 = values[0].t, t1 = Math.max(values[values.length - 1].t, t0 + 1);
  const xMap = (t) => pad.left + (t - t0) / (t1 - t0) * pw;
  const yMap = (v) => pad.top + ph - Math.max(0, Math.min(maxValue, v)) / maxValue * ph;
  const gradient = ctx.createLinearGradient(0, pad.top, 0, pad.top + ph);
  gradient.addColorStop(0, color.replace("1)", ".25)")); gradient.addColorStop(1, color.replace("1)", "0)"));
  ctx.beginPath(); ctx.moveTo(xMap(values[0].t), pad.top + ph);
  for (const point of values) ctx.lineTo(xMap(point.t), yMap(point.v));
  ctx.lineTo(xMap(values[values.length - 1].t), pad.top + ph); ctx.closePath(); ctx.fillStyle = gradient; ctx.fill();
  ctx.beginPath();
  values.forEach((point, index) => index ? ctx.lineTo(xMap(point.t), yMap(point.v)) : ctx.moveTo(xMap(point.t), yMap(point.v)));
  ctx.strokeStyle = color; ctx.lineWidth = 1.6; ctx.stroke();
  ctx.fillStyle = "rgba(145,166,178,.55)"; ctx.textAlign = "left"; ctx.fillText(formatTime(t0, true), pad.left, h - 7);
  ctx.textAlign = "right"; ctx.fillText(formatTime(t1, true), w - pad.right, h - 7);
}

function updateHistory() {
  if (!state) return;
  const last = history[history.length - 1];
  if (last && state.time_s < last.t) history = [];
  if (!last || state.time_s !== last.t) {
    history.push({ t: state.time_s, speed: state.metrics.mean_speed_mps * 3.6, queue: state.queues.mainline + state.queues.ramp });
    if (history.length > 360) history.shift();
  }
  const speedValues = history.map((d) => ({ t: d.t, v: d.speed }));
  const queueValues = history.map((d) => ({ t: d.t, v: d.queue }));
  const queueMax = Math.max(10, ...queueValues.map((d) => d.v)) * 1.15;
  drawChart(els.speedChart, speedValues, "rgba(84,214,218,1)", 120, "");
  drawChart(els.queueChart, queueValues, "rgba(158,140,255,1)", queueMax, "");
}

function updateInspector() {
  if (!state || !selectedVehicleId) {
    $("emptyInspector").hidden = false; $("vehicleInspector").hidden = true;
    $("selectedBadge").textContent = "No selection"; $("selectedBadge").className = "controller-badge";
    return;
  }
  const vehicle = state.vehicles.find((item) => item.vehicle_id === selectedVehicleId);
  if (!vehicle) {
    selectedVehicleId = null; updateInspector(); return;
  }
  $("emptyInspector").hidden = true; $("vehicleInspector").hidden = false;
  $("selectedBadge").textContent = vehicle.controller.toUpperCase(); $("selectedBadge").className = `controller-badge ${vehicle.controller}`;
  $("inspectorId").textContent = vehicle.vehicle_id; $("inspectorSource").textContent = vehicle.source.toUpperCase();
  $("inspectorSpeed").textContent = `${fmt(vehicle.speed_mps * 3.6, 1)} km/h`;
  $("inspectorAccel").textContent = `${vehicle.acceleration_mps2 >= 0 ? "+" : ""}${fmt(vehicle.acceleration_mps2, 2)} m/s²`;
  $("inspectorGap").textContent = vehicle.gap_m === null ? "open road" : `${fmt(vehicle.gap_m, 1)} m`;
  $("inspectorCommand").textContent = `${vehicle.command_mps2 >= 0 ? "+" : ""}${fmt(vehicle.command_mps2, 2)} m/s²`;
  $("inspectorState").textContent = vehicle.control_state;
  $("inspectorMessage").textContent = vehicle.controller !== "cacc" ? "not used" : vehicle.message_valid ? `valid · ${fmt(vehicle.message_age_s, 2)} s` : "fallback / unavailable";
}

function renderDetectors() {
  const container = $("detectorList");
  container.replaceChildren(...state.detectors.map((detector) => {
    const row = document.createElement("div"); row.className = "detector-row";
    const speed = detector.mean_speed_mps === null ? "warming up" : `${fmt(detector.mean_speed_mps * 3.6, 1)} km/h`;
    const occ = detector.occupancy_pct === null ? "—" : `${fmt(detector.occupancy_pct, 1)}% occ.`;
    row.innerHTML = `<b>${detector.sensor_id}</b><span>SPEED<strong>${speed}</strong></span><span>INTERVAL<strong>${detector.count} veh · ${occ}</strong></span>`;
    return row;
  }));
}

function renderScenarioDetails() {
  const scenario = scenarios.get(state.scenario_id);
  if (!scenario) return;
  const rows = [
    ["Controller", scenario.controller.toUpperCase()], ["Penetration", `${Math.round(scenario.penetration * 100)}%`],
    ["Demand", scenario.demand === "high" ? "High" : "Nominal"], ["Brake pulse", scenario.disturbance === "strong" ? "−3.5 m/s²" : "−2.5 m/s²"],
    ["Communication delay", `${scenario.comm_delay_s.toFixed(2)} s`], ["Packet loss", `${Math.round(scenario.dropout_probability * 100)}%`],
  ];
  $("scenarioDetails").replaceChildren(...rows.map(([term, value]) => {
    const div = document.createElement("div"); div.innerHTML = `<dt>${term}</dt><dd>${value}</dd>`; return div;
  }));
}

function renderState(nextState) {
  state = nextState;
  const metrics = state.metrics;
  els.simClock.textContent = `T+${String(state.time_s.toFixed(1)).padStart(5, "0")} s`;
  els.playIcon.textContent = state.session.playing ? "Ⅱ" : "▶";
  els.playLabel.textContent = state.session.playing ? "Pause" : state.finished ? "Run again" : "Run";
  els.speed.value = String(state.session.speed);
  if (!timelineDragging) els.timeline.value = state.time_s;
  els.timeline.max = state.duration_s; els.timelineCurrent.textContent = formatTime(state.time_s); els.timelineEnd.textContent = formatTime(state.duration_s, true);
  $("meanSpeed").textContent = fmt(metrics.mean_speed_mps * 3.6, 1); $("vehicleCount").textContent = `${metrics.active_vehicles} active vehicles`;
  $("throughput").textContent = Math.round(metrics.throughput_veh_h).toLocaleString(); $("exitedCount").textContent = `${metrics.exited_vehicles} vehicles exited`;
  $("delay").textContent = fmt(metrics.total_delay_veh_h, 2); $("queueCount").textContent = `Boundary queue: ${state.queues.mainline + state.queues.ramp} vehicles`;
  $("minGap").textContent = fmt(metrics.minimum_gap_m, 1); $("brakeCount").textContent = `${metrics.hard_brake_events} hard brakes · ${metrics.safety_interventions} safety overrides`;
  $("meterRate").textContent = `${Math.round(metrics.meter_rate_vph)} veh/h`; $("rampQueue").textContent = `queue ${state.queues.ramp}`;
  $("chartSpeedNow").textContent = `${fmt(metrics.mean_speed_mps * 3.6, 1)} km/h`; $("chartQueueNow").textContent = `${state.queues.mainline + state.queues.ramp} veh`;
  const disturbance = $("disturbanceState"); disturbance.classList.toggle("active", state.disturbance.active);
  disturbance.querySelector("span").textContent = state.disturbance.active ? `Lead-vehicle brake active · ${state.disturbance.vehicle_id}` : state.time_s < state.disturbance.start_s ? `Disturbance begins at ${fmt(state.disturbance.start_s, 1)} s` : "Disturbance complete";
  els.scenario.value = state.scenario_id;
  renderScenarioDetails(); renderDetectors(); updateInspector(); drawRoad(); updateHistory();
}

async function sendControl(action, extra = {}) {
  try {
    const next = await api("/api/control", { method: "POST", body: JSON.stringify({ action, ...extra }) });
    setConnected(true); renderState(next);
  } catch (error) {
    setConnected(false); notify(error.message);
  }
}

async function poll() {
  if (requestInFlight) return;
  requestInFlight = true;
  try { const next = await api("/api/state"); setConnected(true); renderState(next); }
  catch (error) { setConnected(false); }
  finally { requestInFlight = false; }
}

function pointerPosition(event) {
  const rect = els.road.getBoundingClientRect();
  return { x: event.clientX - rect.left, y: event.clientY - rect.top };
}

function hitTest(point) {
  return hitboxes.findLast((box) => point.x >= box.x && point.x <= box.x + box.w && point.y >= box.y && point.y <= box.y + box.h);
}

els.road.addEventListener("mousemove", (event) => {
  const point = pointerPosition(event); const hit = hitTest(point);
  if (!hit) { els.tip.hidden = true; return; }
  els.tip.hidden = false; els.tip.style.left = `${point.x}px`; els.tip.style.top = `${point.y}px`;
  els.tip.textContent = `${hit.vehicle.vehicle_id} · ${hit.vehicle.controller.toUpperCase()} · ${fmt(hit.vehicle.speed_mps * 3.6, 1)} km/h`;
});
els.road.addEventListener("mouseleave", () => { els.tip.hidden = true; });
els.road.addEventListener("click", (event) => { const hit = hitTest(pointerPosition(event)); if (hit) { selectedVehicleId = hit.vehicle.vehicle_id; updateInspector(); drawRoad(); } });

els.play.addEventListener("click", () => sendControl(state?.session.playing ? "pause" : "play"));
els.reset.addEventListener("click", () => { history = []; selectedVehicleId = null; sendControl("reset", { scenario_id: els.scenario.value }); });
els.step.addEventListener("click", () => sendControl("step"));
els.speed.addEventListener("change", () => sendControl("speed", { value: Number(els.speed.value) }));
els.scenario.addEventListener("change", () => { history = []; selectedVehicleId = null; sendControl("reset", { scenario_id: els.scenario.value }); });
els.timeline.addEventListener("input", () => { timelineDragging = true; els.timelineCurrent.textContent = formatTime(Number(els.timeline.value)); });
els.timeline.addEventListener("change", async () => { timelineDragging = false; history = []; await sendControl("seek", { time_s: Number(els.timeline.value) }); notify(`Jumped to ${formatTime(Number(els.timeline.value))}`); });
els.live.addEventListener("click", () => sendControl("play"));

els.record.addEventListener("click", () => {
  if (recorder?.state === "recording") { recorder.stop(); return; }
  if (!els.road.captureStream || typeof MediaRecorder === "undefined") { notify("Canvas recording is not supported by this browser"); return; }
  recordedChunks = [];
  const stream = els.road.captureStream(30);
  const preferred = MediaRecorder.isTypeSupported("video/webm;codecs=vp9") ? "video/webm;codecs=vp9" : "video/webm";
  recorder = new MediaRecorder(stream, { mimeType: preferred });
  recorder.ondataavailable = (event) => { if (event.data.size) recordedChunks.push(event.data); };
  recorder.onstop = () => {
    const blob = new Blob(recordedChunks, { type: "video/webm" });
    const link = document.createElement("a"); link.href = URL.createObjectURL(blob);
    link.download = `cav-flow-${state.scenario_id}-${Math.round(state.time_s)}s.webm`; link.click();
    setTimeout(() => URL.revokeObjectURL(link.href), 1500);
    els.record.classList.remove("recording"); els.record.querySelector("span").textContent = "Record canvas"; notify("Recording saved as WebM");
  };
  recorder.start(1000); els.record.classList.add("recording"); els.record.querySelector("span").textContent = "Stop & save"; notify("Recording the roadway canvas");
});

window.addEventListener("keydown", (event) => {
  if (["SELECT", "INPUT"].includes(document.activeElement.tagName)) return;
  if (event.code === "Space") { event.preventDefault(); els.play.click(); }
  if (event.key.toLowerCase() === "r") els.reset.click();
  if (event.key === "ArrowRight") els.step.click();
});

new ResizeObserver(() => { drawRoad(); updateHistory(); }).observe(document.querySelector(".workspace"));

async function initialize() {
  try {
    config = await api("/api/config");
    scenarios = new Map(config.scenarios.map((scenario) => [scenario.scenario_id, scenario]));
    for (const scenario of config.scenarios) {
      const option = document.createElement("option"); option.value = scenario.scenario_id; option.textContent = scenario.label; els.scenario.appendChild(option);
    }
    setConnected(true); await poll(); setInterval(poll, 100);
  } catch (error) {
    setConnected(false); notify(`Cannot connect to the local simulation engine: ${error.message}`);
  }
}

initialize();
