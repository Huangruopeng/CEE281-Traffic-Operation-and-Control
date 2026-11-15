"use strict";

const $ = (id) => document.getElementById(id);
const els = {
  run: $("runSelect"), cav: $("cavSelect"), meter: $("meterSelect"), seed: $("seedSelect"), speed: $("speedSelect"), play: $("playBtn"), playIcon: $("playIcon"),
  playLabel: $("playLabel"), reset: $("resetBtn"), step: $("stepBtn"), record: $("recordBtn"),
  timeline: $("timeline"), timelineCurrent: $("timelineCurrent"), timelineEnd: $("timelineEnd"), live: $("liveBtn"),
  road: $("roadCanvas"), speedChart: $("speedChart"), meterChart: $("meterChart"), queueChart: $("queueChart"), tip: $("hoverTip"),
  panLeft: $("panLeftBtn"), panRight: $("panRightBtn"), centerMerge: $("centerMergeBtn"),
  simClock: $("simClock"), connection: $("connectionStatus"), liveDot: $("liveDot"), toast: $("toast"),
};

let config = null;
let state = null;
let selectedVehicleId = null;
let hitboxes = [];
let requestInFlight = false;
let timelineDragging = false;
let recorder = null;
let recordedChunks = [];
let toastTimer = null;
let cameraCenterM = null;
let cameraDrag = null;
let suppressRoadClick = false;

const colors = { human: "#98a8b3", acc: "#f0b763", cacc: "#54d6da", cav: "#54d6da", coral: "#ff756f", grid: "rgba(137,164,179,.10)" };

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

function defaultCameraCenter(road) {
  return road.ramp_position_m + 130;
}

function cameraGeometry(width, road) {
  const left = 34;
  const right = width - 34;
  const viewSpanM = Math.min(650, Math.max(140, (right - left) / 1.55));
  const fallbackCenter = defaultCameraCenter(road);
  const requestedCenter = cameraCenterM === null ? fallbackCenter : cameraCenterM;
  const minCenter = Math.min(viewSpanM / 2, road.length_m / 2);
  const maxCenter = Math.max(minCenter, road.length_m - viewSpanM / 2);
  const viewCenterM = Math.max(minCenter, Math.min(maxCenter, requestedCenter));
  const viewStartM = Math.max(0, viewCenterM - viewSpanM / 2);
  const viewEndM = Math.min(road.length_m, viewStartM + viewSpanM);
  cameraCenterM = viewCenterM;
  return { left, right, viewSpanM, viewStartM, viewEndM, viewCenterM, pixelsPerMeter: (right - left) / viewSpanM };
}

function moveCamera(deltaM) {
  if (!state) return;
  const width = els.road.getBoundingClientRect().width;
  const geometry = cameraGeometry(width, state.road);
  cameraCenterM = geometry.viewCenterM + deltaM;
  drawRoad();
}

function panCamera(direction) {
  if (!state) return;
  const geometry = cameraGeometry(els.road.getBoundingClientRect().width, state.road);
  moveCamera(direction * geometry.viewSpanM * .75);
}

function centerCameraOnMerge() {
  if (!state) return;
  cameraCenterM = defaultCameraCenter(state.road);
  drawRoad();
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
  const roadY = h * .47;
  const { left, right, viewSpanM, viewStartM, viewEndM } = cameraGeometry(w, road);
  const mapX = (x) => left + ((x - viewStartM) / viewSpanM) * (right - left);
  $("viewStartLabel").textContent = `DRAG TO PAN · x = ${Math.round(viewStartM)} m`;
  $("viewEndLabel").textContent = `x = ${Math.round(viewEndM)} m · FIXED VEHICLE SCALE`;
  els.panLeft.disabled = viewStartM <= .01;
  els.panRight.disabled = viewEndM >= road.length_m - .01;

  // Whole-road overview strip: every vehicle as a dot colored by speed (red = stopped, green = v0),
  // the merge (the bottleneck), the detectors, and a box marking the merge-detail window below.
  const ovY = 48, ovX = (x) => left + (x / road.length_m) * (right - left);
  ctx.strokeStyle = "rgba(215,227,232,.35)"; ctx.lineWidth = 1;
  ctx.beginPath(); ctx.moveTo(left, ovY); ctx.lineTo(right, ovY); ctx.stroke();
  ctx.strokeStyle = "rgba(240,183,99,.8)";
  ctx.beginPath(); ctx.moveTo(ovX(road.ramp_position_m), ovY + 3); ctx.lineTo(ovX(road.ramp_position_m), ovY + 10); ctx.stroke();
  for (const detector of state.detectors) {
    ctx.strokeStyle = "rgba(84,214,218,.8)";
    ctx.beginPath(); ctx.moveTo(ovX(detector.position_m), ovY - 9); ctx.lineTo(ovX(detector.position_m), ovY - 4); ctx.stroke();
  }
  for (const vehicle of state.vehicles) {
    const hue = Math.round(120 * Math.min(vehicle.speed_mps / 33.33, 1));
    ctx.fillStyle = `hsl(${hue}, 75%, 55%)`;
    ctx.fillRect(ovX(vehicle.x_m) - 1, ovY - 2, 2, 4);
  }
  ctx.strokeStyle = "rgba(255,255,255,.45)"; ctx.setLineDash([2, 2]);
  ctx.strokeRect(ovX(viewStartM), ovY - 10, ovX(viewEndM) - ovX(viewStartM), 20); ctx.setLineDash([]);
  ctx.fillStyle = "rgba(174,191,200,.6)"; ctx.font = "8px ui-monospace, monospace"; ctx.textAlign = "left";
  ctx.fillText(`WHOLE ROAD 0-${road.length_m / 1000} km · dashed box = detail view below · amber tick = ramp merge (the bottleneck)`, left, ovY - 14);

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
  const rampVisible = road.ramp_position_m + 50 >= viewStartM && road.ramp_position_m - 250 <= viewEndM;
  if (rampVisible) {
    ctx.lineCap = "round";
    ctx.strokeStyle = "#1b2a34"; ctx.lineWidth = 42; traceRamp(); ctx.stroke();
    ctx.strokeStyle = "rgba(200,216,224,.28)"; ctx.lineWidth = 1; ctx.setLineDash([8, 9]); traceRamp(); ctx.stroke(); ctx.setLineDash([]);
    ctx.fillStyle = "rgba(174,191,200,.48)"; ctx.font = "8px ui-monospace, monospace"; ctx.textAlign = "left";
    ctx.fillText("ON-RAMP", rampCurve.p0.x + 3, rampCurve.p0.y + 31);
  }
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

  if (rampVisible) {
    const meterPoint = cubicPoint(rampCurve, .56);
    const meterX = meterPoint.x, meterY = meterPoint.y;
    ctx.fillStyle = "#8a7ce3"; ctx.fillRect(meterX, meterY - 18, 2, 20);
    ctx.beginPath(); ctx.arc(meterX + 1, meterY - 19, 4, 0, Math.PI * 2);
    ctx.fillStyle = !state.tmc.metered ? "#5b6b75" : state.tmc.green ? "#58d68d" : "#ff756f"; ctx.fill();
    ctx.textAlign = "left"; ctx.fillStyle = "rgba(174,191,200,.65)"; ctx.font = "8px ui-monospace, monospace";
    ctx.fillText(state.tmc.metered ? `METER ${Math.round(state.tmc.rate_vph)} veh/h` : "NO METER", meterX + 8, meterY - 16);

    ctx.strokeStyle = "rgba(240,183,99,.45)"; ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(rampMerge - 8, roadY + 22); ctx.lineTo(rampMerge + 12, roadY + 8); ctx.stroke();
    ctx.fillStyle = "rgba(240,183,99,.62)"; ctx.font = "8px ui-monospace, monospace"; ctx.fillText("MERGE = BOTTLENECK", rampMerge + 17, roadY + 24);

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
    if (follower.controller === "cav" && follower.message_valid && leader.x_m - follower.x_m < 190) {
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
    // Every active vehicle uses one fixed, normal-size body. Braking
    // is shown with outlines/lights, never by resizing.
    const carW = 10;
    const carH = 8;
    const color = colors[vehicle.controller] || colors.human;
    ctx.save(); ctx.translate(x, y); ctx.rotate(visual.angle);
    if (vehicle.hard_braking) {
      ctx.shadowColor = colors.coral; ctx.shadowBlur = 11;
      ctx.strokeStyle = colors.coral; ctx.lineWidth = 2;
      roundedRect(ctx, -carW / 2 - 2, -carH / 2 - 2, carW + 4, carH + 4, 3); ctx.stroke();
      ctx.shadowBlur = 0;
    }
    ctx.fillStyle = color;
    roundedRect(ctx, -carW / 2, -carH / 2, carW, carH, 2); ctx.fill();
    ctx.fillStyle = "rgba(5,13,18,.72)"; ctx.fillRect(carW / 2 - 2, -carH / 2 + 2, 1, carH - 4);
    if (vehicle.controller === "cav") { ctx.fillStyle = "#f1fbff"; ctx.beginPath(); ctx.arc(-1, 0, 1.1, 0, Math.PI * 2); ctx.fill(); }
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

  ctx.textAlign = "right"; ctx.fillStyle = "rgba(148,169,181,.55)"; ctx.font = "9px ui-monospace, monospace";
  ctx.fillText(`${state.vehicles.length} ACTIVE · ${fmt(state.metrics.mean_speed_mps * 3.6, 1)} km/h`, right, 24);
  ctx.textAlign = "left";
}

function drawChart(canvas, series, { maxValue, duration, threshold = null, emptyText = null, suffix = "" }) {
  const { ctx, width: w, height: h } = resizeCanvas(canvas);
  ctx.clearRect(0, 0, w, h); ctx.fillStyle = "#0a141c"; ctx.fillRect(0, 0, w, h);
  const pad = { left: 38, right: 12, top: 14, bottom: 22 };
  const pw = w - pad.left - pad.right, ph = h - pad.top - pad.bottom;
  const xMap = (t) => pad.left + Math.max(0, Math.min(1, t / duration)) * pw;
  const yMap = (v) => pad.top + ph - Math.max(0, Math.min(maxValue, v)) / maxValue * ph;
  ctx.font = "8px ui-monospace, monospace"; ctx.fillStyle = "rgba(145,166,178,.6)"; ctx.textAlign = "right";
  for (let i = 0; i <= 3; i++) {
    const y = pad.top + ph * i / 3;
    ctx.strokeStyle = "rgba(145,166,178,.10)"; ctx.lineWidth = 1; ctx.beginPath(); ctx.moveTo(pad.left, y); ctx.lineTo(w - pad.right, y); ctx.stroke();
    ctx.fillText(`${Math.round(maxValue * (1 - i / 3))}${suffix}`, pad.left - 6, y + 3);
  }
  ctx.textAlign = "left"; ctx.fillText("0", pad.left, h - 7);
  ctx.textAlign = "right"; ctx.fillText(`${Math.round(duration / 60)} min`, w - pad.right, h - 7);
  if (threshold !== null) {
    ctx.strokeStyle = "rgba(255,117,111,.7)"; ctx.setLineDash([4, 4]); ctx.beginPath();
    ctx.moveTo(pad.left, yMap(threshold)); ctx.lineTo(w - pad.right, yMap(threshold)); ctx.stroke(); ctx.setLineDash([]);
  }
  if (emptyText) {
    ctx.fillStyle = "rgba(174,191,200,.7)"; ctx.textAlign = "center"; ctx.font = "10px ui-monospace, monospace";
    ctx.fillText(emptyText, pad.left + pw / 2, pad.top + ph / 2); return;
  }
  for (const { points, color, step } of series) {
    const valid = points.filter((p) => p.v !== null && p.v !== undefined);
    if (!valid.length) continue;
    ctx.beginPath();
    valid.forEach((p, k) => {
      if (step) {   // a 30-s interval value holds from the start to the end of its interval
        const t0 = Math.max(0, p.t - step);
        if (k === 0) ctx.moveTo(xMap(t0), yMap(p.v)); else ctx.lineTo(xMap(t0), yMap(p.v));
        ctx.lineTo(xMap(p.t), yMap(p.v));
      } else if (k === 0) ctx.moveTo(xMap(p.t), yMap(p.v)); else ctx.lineTo(xMap(p.t), yMap(p.v));
    });
    ctx.strokeStyle = color; ctx.lineWidth = 2; ctx.stroke();
  }
}

function updateCharts() {
  if (!state) return;
  const duration = state.duration_s, interval = config.simulation.detector_interval_s;
  const d1 = state.d1.history.map((r) => ({ t: r.t, v: r.speed_kmh }));
  drawChart(els.speedChart, [{ points: d1, color: "rgba(84,214,218,1)", step: interval }], { maxValue: 120, duration, threshold: 40 });
  if (state.tmc.metered) {
    // the rate chosen at time t applies until the next update, 30 s later
    const rate = state.tmc.history.map((r) => ({ t: r.t + interval, v: r.rate }));
    drawChart(els.meterChart, [{ points: rate, color: "rgba(240,183,99,1)", step: interval }], { maxValue: 1000, duration });
  } else {
    drawChart(els.meterChart, [], { maxValue: 1000, duration, emptyText: "no meter: ramp vehicles merge whenever the gap allows" });
  }
  const main = state.samples.map((d) => ({ t: d.t, v: d.mainline })), ramp = state.samples.map((d) => ({ t: d.t, v: d.ramp }));
  const qMax = Math.ceil(Math.max(10, ...state.samples.map((d) => Math.max(d.mainline, d.ramp))) * 1.15 / 10) * 10;
  drawChart(els.queueChart, [{ points: main, color: "rgba(84,214,218,1)" }, { points: ramp, color: "rgba(158,140,255,1)" }], { maxValue: qMax, duration });
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
  $("inspectorState").textContent = vehicle.control_state;
  $("inspectorMessage").textContent = vehicle.controller !== "cav" ? "not used" : vehicle.message_valid ? "from the CAV ahead" : "none (vehicle ahead is not a CAV)";
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

function rows(container, items) {
  container.replaceChildren(...items.map(([term, value]) => {
    const div = document.createElement("div"); div.innerHTML = `<dt>${term}</dt><dd>${value}</dd>`; return div;
  }));
}

function renderScenarioDetails() {
  const c = state.case;
  rows($("scenarioDetails"), [
    ["Run", `Run ${c.run}`], ["Human time gap T", `${c.T.toFixed(1)} s`], ["CAV share", `${Math.round(100 * c.penetration)}%`],
    ["Capacity (with this CAV share)", `${c.capacity_vph.toLocaleString()} veh/h`],
    ["Demand", `${c.mainline_vph.toLocaleString()} + ${c.ramp_vph} veh/h`], ["Demand / capacity", `${c.demand_pct}%`],
    ["Ramp meter", c.meter_label], ["Seed", String(c.seed)],
  ]);
}

function renderSystems() {
  const d1 = state.d1, tmc = state.tmc, c = state.case;
  $("congestionRow").classList.toggle("congested", d1.congested);
  $("congestionStatus").textContent = d1.congested ? `CONGESTED since ${formatTime(d1.since_s, true)}` : "not congested";
  $("slowCount").textContent = `${Math.min(d1.slow_in_a_row, 4)} / 4 slow`;
  $("meterMode").textContent = `Ramp meter: ${c.meter_label}`;
  $("meterRate").textContent = tmc.metered ? `${Math.round(tmc.rate_vph)} veh/h` : "off";
  $("rampQueue").textContent = `ramp queue ${state.queues.ramp} / ${config.ramp_meter.storage_vehicles}`;
  const items = [];
  if (c.meter_mode === "alinea") {
    const occ = tmc.last && tmc.last.occ !== null ? `${fmt(tmc.last.occ, 1)}%` : tmc.d2_lost ? "lost" : "—";
    items.push(["Update", "every 30 s: r = r + 70 × (target − D2 occupancy)"], ["Target occupancy", `${c.target_pct}%`],
               ["D2 occupancy (last 30 s)", occ], ["Last decision", tmc.last ? tmc.last.reason : "—"]);
  } else if (c.meter_mode === "fixed") {
    items.push(["Rate", `fixed ${c.fixed_rate_vph} veh/h`]);
  }
  $("tmcDetail").innerHTML = items.map(([a, b]) => `<div><span>${a}</span><strong>${b}</strong></div>`).join("");
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
  $("minGap").textContent = fmt(metrics.minimum_gap_m, 1); $("brakeCount").textContent = `hardest braking ${fmt(metrics.hardest_braking_mps2, 1)} m/s²`;
  const lastD1 = state.d1.history[state.d1.history.length - 1];
  $("chartSpeedNow").textContent = lastD1 && lastD1.speed_kmh !== null ? `${fmt(lastD1.speed_kmh, 0)} km/h` : "—";
  $("chartMeterNow").textContent = state.tmc.metered ? `${Math.round(state.tmc.rate_vph)} veh/h` : "off";
  const lastSample = state.samples[state.samples.length - 1];
  $("chartQueueNow").textContent = lastSample ? `${lastSample.mainline} + ${lastSample.ramp} veh` : "0 veh";
  const sc = state.session.case;
  for (const [el, value] of [[els.run, sc.run], [els.cav, sc.penetration], [els.meter, sc.meter], [els.seed, sc.seed]]) {
    if (document.activeElement !== el) el.value = String(value);
  }
  renderScenarioDetails(); renderSystems(); renderDetectors(); updateInspector(); drawRoad(); updateCharts();
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
  if (cameraDrag?.moved) { els.tip.hidden = true; return; }
  const point = pointerPosition(event); const hit = hitTest(point);
  if (!hit) { els.tip.hidden = true; return; }
  els.tip.hidden = false; els.tip.style.left = `${point.x}px`; els.tip.style.top = `${point.y}px`;
  els.tip.textContent = `${hit.vehicle.vehicle_id} · ${hit.vehicle.controller.toUpperCase()} · ${fmt(hit.vehicle.speed_mps * 3.6, 1)} km/h`;
});
els.road.addEventListener("mouseleave", () => { els.tip.hidden = true; });
els.road.addEventListener("pointerdown", (event) => {
  if (event.button !== 0 || !state) return;
  const geometry = cameraGeometry(els.road.getBoundingClientRect().width, state.road);
  cameraDrag = { pointerId: event.pointerId, startX: event.clientX, startCenterM: geometry.viewCenterM, pixelsPerMeter: geometry.pixelsPerMeter, moved: false };
  els.road.setPointerCapture(event.pointerId);
});
els.road.addEventListener("pointermove", (event) => {
  if (!cameraDrag || cameraDrag.pointerId !== event.pointerId) return;
  const dx = event.clientX - cameraDrag.startX;
  if (Math.abs(dx) >= 4) cameraDrag.moved = true;
  if (!cameraDrag.moved) return;
  cameraCenterM = cameraDrag.startCenterM - dx / cameraDrag.pixelsPerMeter;
  els.road.classList.add("is-panning");
  els.tip.hidden = true;
  drawRoad();
});
function endCameraDrag(event) {
  if (!cameraDrag || cameraDrag.pointerId !== event.pointerId) return;
  const moved = cameraDrag.moved;
  cameraDrag = null;
  els.road.classList.remove("is-panning");
  if (els.road.hasPointerCapture(event.pointerId)) els.road.releasePointerCapture(event.pointerId);
  if (moved) {
    suppressRoadClick = true;
    setTimeout(() => { suppressRoadClick = false; }, 0);
  }
}
els.road.addEventListener("pointerup", endCameraDrag);
els.road.addEventListener("pointercancel", endCameraDrag);
els.road.addEventListener("click", (event) => {
  if (suppressRoadClick) return;
  const hit = hitTest(pointerPosition(event));
  if (hit) { selectedVehicleId = hit.vehicle.vehicle_id; updateInspector(); drawRoad(); }
});

els.panLeft.addEventListener("click", () => panCamera(-1));
els.panRight.addEventListener("click", () => panCamera(1));
els.centerMerge.addEventListener("click", centerCameraOnMerge);

els.play.addEventListener("click", () => sendControl(state?.session.playing ? "pause" : "play"));
function chosenCase() {
  return { run: Number(els.run.value), penetration: Number(els.cav.value), meter: els.meter.value, seed: Number(els.seed.value) };
}
els.reset.addEventListener("click", () => { selectedVehicleId = null; sendControl("reset", { case: chosenCase() }); });
els.step.addEventListener("click", () => sendControl("step"));
els.speed.addEventListener("change", () => sendControl("speed", { value: Number(els.speed.value) }));
for (const el of [els.run, els.cav, els.meter, els.seed]) {
  el.addEventListener("change", () => { selectedVehicleId = null; sendControl("reset", { case: chosenCase() }); el.blur(); });
}
els.timeline.addEventListener("input", () => { timelineDragging = true; els.timelineCurrent.textContent = formatTime(Number(els.timeline.value)); });
els.timeline.addEventListener("change", async () => { timelineDragging = false; await sendControl("seek", { time_s: Number(els.timeline.value) }); notify(`Jumped to ${formatTime(Number(els.timeline.value))}`); });
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
  if (event.shiftKey && event.key === "ArrowLeft") { event.preventDefault(); panCamera(-1); return; }
  if (event.shiftKey && event.key === "ArrowRight") { event.preventDefault(); panCamera(1); return; }
  if (event.key.toLowerCase() === "m") centerCameraOnMerge();
  if (event.key === "ArrowRight") els.step.click();
});

new ResizeObserver(() => { drawRoad(); updateCharts(); }).observe(document.querySelector(".workspace"));

async function initialize() {
  try {
    config = await api("/api/config");
    const add = (select, value, text) => { const o = document.createElement("option"); o.value = String(value); o.textContent = text; select.appendChild(o); };
    const o = config.options;
    for (const r of o.runs) add(els.run, r.id, `Run ${r.id}: T = ${r.T} s, ramp ${r.ramp} veh/h`);
    for (const p of o.cav_shares) add(els.cav, p, `${Math.round(100 * p)}%`);
    for (const m of o.meters) add(els.meter, m.id, m.label);
    for (const seed of o.seeds) add(els.seed, seed, String(seed));
    setConnected(true); await poll(); setInterval(poll, 100);
  } catch (error) {
    setConnected(false); notify(`Cannot connect to the local simulation engine: ${error.message}`);
  }
}

initialize();
