"""Build demo/index.html: an offline, single-file classroom demo that replays the
recorded simulation traces and lets you play with the tuned fuzzy controller."""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "..", "results")
OUT = os.path.join(HERE, "..", "demo", "index.html")


def main():
    tr = json.load(open(os.path.join(RES, "traces_peak_build_seed1.json")))
    ev = json.load(open(os.path.join(RES, "evaluation.json")))
    data = {
        "traces": {k: {"phase": v["phase"], "queues": v["queues"], "total": v["total_queued"],
                       "avg_delay": v["avg_delay"]} for k, v in tr.items()},
        "fuzzy": {"tuned": ev["decoded"]["ga_fuzzy"], "hand": ev["decoded"]["fuzzy_hand"]},
        "summary": {s: {c: round(ev["main"][s][c]["avg_delay"]["mean"], 3)
                        for c in ("webster", "ga_fixed", "fuzzy_hand", "ga_fuzzy")} for s in ev["main"]},
    }
    if "mixed_training" in ev:
        for s, v in ev["mixed_training"]["scenarios"].items():
            data["summary"][s]["ga_fuzzy_mixed"] = round(v["ga_fuzzy_mixed"]["avg_delay"]["mean"], 3)
        data["fuzzy"]["mixed"] = ev["mixed_training"]["decoded"]["ga_fuzzy_mixed"]
        data["imp_final"] = {s: v["ga_fuzzy_mixed"]["improvement_pct"] for s, v in ev["mixed_training"]["scenarios"].items()}
    html = TEMPLATE.replace("/*__DATA__*/null", json.dumps(data, separators=(",", ":")))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        f.write(html)
    print("wrote", os.path.abspath(OUT), f"{len(html) / 1024:.0f} KB")


TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Fuzzy Corridor Signals</title>
<style>
:root{
  --bg:#f6f5f2; --panel:#fcfcfb; --ink:#0b0b0b; --ink2:#52514e; --muted:#8a8984; --line:#e4e3df;
  --road:#d9d8d3; --fuzzy:#2a78d6; --fixed:#8a8984; --gafixed:#eb6834; --green:#1f9d55; --amber:#e8a200; --red:#d64545;
  --low:#2a78d6; --med:#1baf7a; --high:#eb6834;
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    --bg:#121211; --panel:#1a1a19; --ink:#f0efec; --ink2:#c3c2b7; --muted:#8f8e86; --line:#2e2e2b;
    --road:#3a3a37; --fuzzy:#3987e5; --fixed:#9a9991; --gafixed:#d95926; --green:#2fb36a; --amber:#f0b21a; --red:#e66767;
    --low:#3987e5; --med:#199e70; --high:#d95926;
  }
}
:root[data-theme="dark"]{
  --bg:#121211; --panel:#1a1a19; --ink:#f0efec; --ink2:#c3c2b7; --muted:#8f8e86; --line:#2e2e2b;
  --road:#3a3a37; --fuzzy:#3987e5; --fixed:#9a9991; --gafixed:#d95926; --green:#2fb36a; --amber:#f0b21a; --red:#e66767;
  --low:#3987e5; --med:#199e70; --high:#d95926;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}
.wrap{max-width:1100px;margin:0 auto;padding-block:20px 48px;padding-left:max(16px, env(safe-area-inset-left, 0px));padding-right:max(16px, env(safe-area-inset-right, 0px))}
h1{font-size:22px;margin:0 0 4px}
.sub{color:var(--ink2);margin:0 0 18px}
.tabs{display:flex;gap:8px;margin-bottom:14px;flex-wrap:wrap}
.tab{border:1px solid var(--line);background:var(--panel);color:var(--ink);padding:7px 14px;border-radius:8px;cursor:pointer;font:inherit}
.tab[aria-selected="true"]{border-color:var(--fuzzy);color:var(--fuzzy);font-weight:600}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px;margin-bottom:14px}
.row{display:flex;gap:14px;flex-wrap:wrap;align-items:center}
.ctrl button,.ctrl select,#pset{font:inherit;padding:6px 12px;border-radius:8px;border:1px solid var(--line);background:var(--bg);color:var(--ink);cursor:pointer}
.ctrl button:hover,.tab:hover{border-color:var(--fuzzy)}
.ctrl button:active,.tab:active{transform:translateY(1px)}
.ctrl button.primary{background:var(--fuzzy);border-color:var(--fuzzy);color:#fff;font-weight:600;min-width:104px}
button:focus-visible,select:focus-visible,input:focus-visible{outline:2px solid var(--fuzzy);outline-offset:2px}
input[type=range]{width:100%;accent-color:var(--fuzzy)}
.panel h3{margin:0 0 6px;font-size:15px}
.stat{font-variant-numeric:tabular-nums;color:var(--ink2);font-size:13px}
.stat b{color:var(--ink);font-size:16px}
canvas{width:100%;display:block}
.grid2{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:14px}
.grid2>*{min-width:0}
@media (max-width:760px){.grid2{grid-template-columns:minmax(0,1fr)}}
select{max-width:100%}
table{border-collapse:collapse;width:100%;font-size:13px;font-variant-numeric:tabular-nums}
th,td{padding:5px 6px;border-bottom:1px solid var(--line);text-align:left}
th{color:var(--ink2);font-weight:600}
.pill{display:inline-block;padding:2px 10px;border-radius:999px;font-weight:600;font-size:13px}
.legend{display:flex;gap:14px;font-size:12px;color:var(--ink2);flex-wrap:wrap}
.sw{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:5px;vertical-align:-1px}
.note{font-size:13px;color:var(--ink2)}
[hidden]{display:none!important}
</style>
</head>
<body>
<div class="wrap">
  <h1>Fuzzy + GA traffic signals on a 3-junction corridor</h1>
  <p class="sub">Soft Computing AAT, Topic 12. Replay of the recorded simulation (scenario: peak build-up and decay, seed 1) and an interactive view of the fuzzy controller.</p>
  <div class="tabs" role="tablist">
    <button class="tab" role="tab" aria-selected="true" data-tab="replay">Corridor replay</button>
    <button class="tab" role="tab" aria-selected="false" data-tab="fis">Fuzzy controller</button>
    <button class="tab" role="tab" aria-selected="false" data-tab="results">Results</button>
  </div>

  <section id="tab-replay">
    <div class="card ctrl">
      <div class="row">
        <button id="play" class="primary" aria-label="Play">&#9654; Play</button>
        <button id="reset">Restart</button>
        <label>Speed <select id="speed"><option value="5">5x</option><option value="20">20x</option><option value="60" selected>60x (1 h in 1 min)</option><option value="120">120x</option></select></label>
        <span class="stat">Time <b id="clock">00:00</b></span>
        <label>Compare against <select id="baseline"><option value="webster">Webster fixed-time</option><option value="ga_fixed">GA-tuned fixed-time</option></select></label>
      </div>
      <input id="scrub" type="range" min="0" max="3599" value="0" aria-label="time">
      <p class="note" style="margin:6px 0 0">Keyboard: Space = play/pause, Left/Right arrow = 1 minute back/forward.</p>
    </div>
    <div class="grid2">
      <div class="card panel"><h3 id="baseTitle">Webster fixed-time</h3><div class="stat">Vehicles queued <b id="qBase">0</b> · hour average delay <b id="dBase"></b> s/veh</div><canvas id="cBase" height="300"></canvas></div>
      <div class="card panel"><h3 style="color:var(--fuzzy)">GA-tuned fuzzy (proposed)</h3><div class="stat">Vehicles queued <b id="qFz">0</b> · hour average delay <b id="dFz"></b> s/veh</div><canvas id="cFz" height="300"></canvas></div>
    </div>
    <div class="card">
      <div class="legend"><span><span class="sw" style="background:var(--fixed)" id="swBase"></span><span id="lgBase">Webster fixed-time</span></span><span><span class="sw" style="background:var(--fuzzy)"></span>GA-tuned fuzzy</span><span>Vehicles queued in the whole corridor over the hour (60 s mean). Click to jump.</span></div>
      <canvas id="cLine" height="150"></canvas>
    </div>
    <p class="note">Each small block is one queued vehicle (a number is shown when the queue is longer than the drawn lane). The signal dot on each approach shows green, or amber during the 4 s inter-green. Arterial = 2 lanes per direction, side streets = 1 lane.</p>
  </section>

  <section id="tab-fis" hidden>
    <div class="card">
      <div class="row" style="justify-content:space-between">
        <label>Parameters <select id="pset"><option value="tuned">GA-tuned (peak-trained)</option><option value="mixed">GA-tuned (mixed-trained, final)</option><option value="hand">Hand-tuned</option></select></label>
        <span id="decision" class="pill"></span>
      </div>
      <div class="grid2" style="margin-top:10px">
        <div><label>Green demand G = <b id="gv"></b> veh/lane</label><input id="g" type="range" min="0" max="20" step="0.5" value="4"><canvas id="cG" height="120"></canvas></div>
        <div><label>Red queue R = <b id="rv"></b> veh/lane</label><input id="r" type="range" min="0" max="25" step="0.5" value="6"><canvas id="cR" height="120"></canvas></div>
      </div>
    </div>
    <div class="grid2">
      <div class="card"><h3 style="margin:0 0 6px;font-size:15px">Rule firing (min of antecedents)</h3><table id="rules"></table></div>
      <div class="card"><h3 style="margin:0 0 6px;font-size:15px">Aggregated output and centroid</h3><canvas id="cOut" height="200"></canvas><p class="note" id="outNote"></p></div>
    </div>
  </section>

  <section id="tab-results" hidden>
    <div class="card"><h3 style="margin:0 0 6px;font-size:15px">Mean average delay (s/veh) over 10 unseen seeds</h3><table id="restab"></table>
    <p class="note">The peak-trained GA saw only the "peak build-up" scenario (seeds 1001-1003). The final, mixed-trained GA saw one off-peak, one moderate and one peak build-up hour. Every number here comes from 10 different test seeds. Lower is better, and bold marks the lowest delay. The replay tab uses the peak-trained controller.</p></div>
  </section>
</div>

<script>
const D = /*__DATA__*/null;
const COL = {};  // CSS colour tokens, read once (re-read when the OS theme changes)
const css = n => COL[n] ?? (COL[n] = getComputedStyle(document.documentElement).getPropertyValue(n).trim());
const T = D.traces.webster.phase.length;

// ---------------------------------------------------------------- tabs
document.querySelectorAll('.tab').forEach(b => b.onclick = () => {
  if (b.dataset.tab !== 'replay' && playing) setPlaying(false);
  document.querySelectorAll('.tab').forEach(x => x.setAttribute('aria-selected', x === b));
  ['replay','fis','results'].forEach(t => document.getElementById('tab-'+t).hidden = (t !== b.dataset.tab));
  drawAll();
});

// ---------------------------------------------------------------- replay
let t = 0, playing = false, last = null, acc = 0, baseline = 'webster';
const scrub = document.getElementById('scrub'), playBtn = document.getElementById('play'), speedSel = document.getElementById('speed');
// resize a canvas only when its on-screen size changes (resizing every frame is slow)
function fitCanvas(c){
  // the CSS height is fixed from the original height attribute, so a high-DPI bitmap never stretches the box
  const h = +(c.dataset.h || (c.dataset.h = c.getAttribute('height'))); c.style.height = h + 'px';
  const w = c.clientWidth, dpr = window.devicePixelRatio||1;
  if (c._w !== w || c._dpr !== dpr){ c.width = Math.max(10, Math.round(w*dpr)); c.height = Math.round(h*dpr); c._w = w; c._dpr = dpr; c._ver = (c._ver||0) + 1; }
  const ctx = c.getContext('2d'); ctx.setTransform(dpr,0,0,dpr,0,0); return [ctx, w, h]; }

function drawCorridor(canvas, trace, time){
  const [ctx, W, H] = fitCanvas(canvas); ctx.clearRect(0,0,W,H);
  const midY = H/2, xs = [W*0.17, W*0.5, W*0.83], laneW = 9, car = 5, gap = 1.5;
  ctx.fillStyle = css('--road'); ctx.fillRect(0, midY-2*laneW-2, W, 4*laneW+4);
  xs.forEach(x => ctx.fillRect(x-laneW-1, 0, 2*laneW+2, H));
  const ph = trace.phase[time], q = trace.queues[time];
  xs.forEach((x, j) => {
    ctx.fillStyle = css('--panel'); ctx.strokeStyle = css('--ink2');
    ctx.fillRect(x-2*laneW-2, midY-2*laneW-2, 4*laneW+4, 4*laneW+4); ctx.strokeRect(x-2*laneW-2, midY-2*laneW-2, 4*laneW+4, 4*laneW+4);
    ctx.fillStyle = css('--ink'); ctx.font = '600 12px system-ui'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillText('J'+(j+1), x, midY);
    const half = W*0.33/2 - 2*laneW - 8;
    // approach geometry: [dx, dy] direction away from the junction, lanes, start offset
    const appr = [
      {a:0, dir:[-1,0], lanes:2, base:[x-2*laneW-6, midY+laneW*0.5], laneStep:[0, laneW], max:half},   // EB queues to the west, lower lanes
      {a:1, dir:[1,0], lanes:2, base:[x+2*laneW+6, midY-laneW*1.5], laneStep:[0, laneW], max:half},    // WB to the east, upper lanes
      {a:2, dir:[0,1], lanes:1, base:[x+laneW*0.5, midY+2*laneW+6], laneStep:[0,0], max:H/2-2*laneW-12}, // NB from the south
      {a:3, dir:[0,-1], lanes:1, base:[x-laneW*0.5, midY-2*laneW-6], laneStep:[0,0], max:H/2-2*laneW-12}  // SB from the north
    ];
    appr.forEach(p => {
      const n = q[j][p.a], perLane = Math.ceil(n / p.lanes), fit = Math.floor(p.max/(car+gap));
      ctx.fillStyle = css('--ink2');
      for (let l = 0; l < p.lanes; l++){
        const cnt = Math.min(fit, Math.floor(n/p.lanes) + (l < n % p.lanes ? 1 : 0));
        for (let k = 0; k < cnt; k++){
          const d = k*(car+gap);
          const cx = p.base[0] + p.dir[0]*d + p.laneStep[0]*l - (p.dir[0] ? (p.dir[0] < 0 ? car : 0) : car/2) ;
          const cy = p.base[1] + p.dir[1]*d + p.laneStep[1]*l - (p.dir[1] ? (p.dir[1] < 0 ? car : 0) : car/2);
          ctx.fillRect(cx, cy, car, car);
        }
      }
      if (perLane > fit){ ctx.fillStyle = css('--ink'); ctx.font = '600 11px system-ui';
        const lx = Math.max(12, Math.min(W-12, p.base[0] + p.dir[0]*(p.max+10) + (p.dir[1]?14:0)));
        const ly = Math.max(10, Math.min(H-8, p.base[1] + p.dir[1]*(p.max+4) + (p.dir[0]?laneW/2:0)));
        ctx.fillText(n, lx, ly); }
      const phaseOf = p.a < 2 ? 0 : 1, sig = ph[j] === phaseOf ? css('--green') : (ph[j] === -1 ? css('--amber') : css('--red'));
      ctx.beginPath(); ctx.fillStyle = sig;
      const sx = p.base[0] + (p.dir[1] ? (p.a===2? laneW+4 : -laneW-4) : 0), sy = p.base[1] + (p.dir[0] ? (p.a===0? 2*laneW+4 : -laneW-4) : 0);
      ctx.arc(sx, sy, 4.5, 0, 7); ctx.fill();
    });
  });
}

function smooth(xs, k){ const out = []; let acc = 0; xs.forEach((x,i)=>{ acc += x; if (i>=k) acc -= xs[i-k]; out.push(acc/Math.min(i+1,k)); }); return out; }
const SM = {}; for (const k in D.traces) SM[k] = smooth(D.traces[k].total, 60);
const lineC = document.getElementById('cLine'), PAD = {l:36, r:8, t:8, b:22};
const MAXY = Math.max(...SM.webster, ...SM.ga_fixed, ...SM.ga_fuzzy)*1.05;
let lineCache = null, lineKey = '';
function drawLine(){
  const [ctx, W, H] = fitCanvas(lineC), dpr = window.devicePixelRatio||1;
  const X = i => PAD.l + (W-PAD.l-PAD.r)*i/(T-1), Y = v => H-PAD.b - (H-PAD.t-PAD.b)*v/MAXY;
  const key = [W, dpr, baseline, css('--fuzzy')].join('|');
  if (key !== lineKey){  // the hour-long chart is drawn once, then reused every frame
    lineKey = key; lineCache = document.createElement('canvas'); lineCache.width = lineC.width; lineCache.height = lineC.height;
    const c = lineCache.getContext('2d'); c.setTransform(dpr,0,0,dpr,0,0);
    c.strokeStyle = css('--line'); c.fillStyle = css('--muted'); c.font = '11px system-ui'; c.textAlign = 'right'; c.lineWidth = 1;
    for (let v = 0; v <= MAXY; v += 50){ c.beginPath(); c.moveTo(PAD.l, Y(v)); c.lineTo(W-PAD.r, Y(v)); c.stroke(); c.fillText(v, PAD.l-4, Y(v)+3); }
    c.textAlign = 'center'; for (let m = 0; m <= 60; m += 10) c.fillText(m+' min', X(m*60 >= T ? T-1 : m*60), H-6);
    [[baseline, baseline==='webster'? '--fixed':'--gafixed'], ['ga_fuzzy','--fuzzy']].forEach(([k, col]) => {
      c.strokeStyle = css(col); c.lineWidth = 2; c.beginPath(); SM[k].forEach((v,i)=> i ? c.lineTo(X(i),Y(v)) : c.moveTo(X(i),Y(v))); c.stroke(); });
  }
  ctx.clearRect(0,0,W,H); ctx.drawImage(lineCache, 0, 0, W, H);
  ctx.lineWidth = 1.5; ctx.strokeStyle = css('--ink'); ctx.beginPath(); ctx.moveTo(X(t), PAD.t); ctx.lineTo(X(t), H-PAD.b); ctx.stroke();
}
lineC.onclick = e => { const r = lineC.getBoundingClientRect();
  seek(Math.round((e.clientX - r.left - PAD.l)/(r.width - PAD.l - PAD.r)*(T-1))); };

const el = id => document.getElementById(id);
function drawAll(){
  scrub.value = t; const mm = String(Math.floor(t/60)).padStart(2,'0'), ss = String(t%60).padStart(2,'0');
  el('clock').textContent = mm+':'+ss;
  const B = D.traces[baseline], F = D.traces.ga_fuzzy;
  el('qBase').textContent = B.total[t]; el('qFz').textContent = F.total[t];
  el('dBase').textContent = B.avg_delay.toFixed(1); el('dFz').textContent = F.avg_delay.toFixed(1);
  if (!el('tab-replay').hidden){ drawCorridor(el('cBase'), B, t); drawCorridor(el('cFz'), F, t); drawLine(); }
  if (!el('tab-fis').hidden) drawFis();
}
function seek(v){ t = Math.max(0, Math.min(T-1, v|0)); acc = 0; drawAll(); }
function setPlaying(p){
  playing = p; last = null; acc = 0;
  playBtn.innerHTML = p ? '&#10074;&#10074; Pause' : '&#9654; Play'; playBtn.setAttribute('aria-label', p ? 'Pause' : 'Play');
  if (p){ if (t >= T-1) t = 0; drawAll(); requestAnimationFrame(tick); }
}
function tick(ts){
  if (!playing) return;
  if (last !== null){
    acc += Math.min(ts - last, 100)/1000 * (+speedSel.value);  // capped so a background tab does not jump
    const step = Math.floor(acc);
    if (step > 0){ acc -= step; t = Math.min(T-1, t + step); drawAll(); }
  }
  last = ts;
  if (t >= T-1){ setPlaying(false); return; }
  requestAnimationFrame(tick);
}
playBtn.onclick = () => setPlaying(!playing);
el('reset').onclick = () => { seek(0); };
scrub.oninput = () => seek(+scrub.value);
el('baseline').onchange = e => { baseline = e.target.value;
  const name = baseline === 'webster' ? 'Webster fixed-time' : 'GA-tuned fixed-time';
  el('baseTitle').textContent = name; el('lgBase').textContent = name;
  el('swBase').style.background = css(baseline==='webster'?'--fixed':'--gafixed'); drawAll(); };
document.addEventListener('keydown', e => {
  if (el('tab-replay').hidden || ['INPUT','SELECT','TEXTAREA'].includes(e.target.tagName) && e.target.type !== 'range') return;
  if (e.code === 'Space'){ e.preventDefault(); setPlaying(!playing); }
  else if (e.code === 'ArrowRight' && e.target.type !== 'range'){ e.preventDefault(); seek(t + 60); }
  else if (e.code === 'ArrowLeft' && e.target.type !== 'range'){ e.preventDefault(); seek(t - 60); }
});
matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => { for (const k in COL) delete COL[k]; lineKey = ''; drawAll(); });

// ---------------------------------------------------------------- fuzzy (same maths as src/fuzzy.py)
const ls = (x,a,b) => x<=a?1:(x>=b?0:(b-x)/(b-a));
const rs = (x,a,b) => x<=a?0:(x>=b?1:(x-a)/(b-a));
const tri = (x,a,b,c) => (x<a||x>c)?0:(x===b?1:(x<b?(x-a)/(b-a):(c-x)/(c-b)));
const terms = p => ({Low:x=>ls(x,p[0],p[1]), Medium:x=>tri(x,p[0],p[1],p[2]), High:x=>rs(x,p[1],p[2])});
const OUT = {Low:y=>tri(y,0,0,0.5), Medium:y=>tri(y,0.25,0.5,0.75), High:y=>tri(y,0.5,1,1)};
const RULES = [['Low','Low','Low'],['Low','Medium','High'],['Low','High','High'],['Medium','Low','Low'],['Medium','Medium','Medium'],['Medium','High','High'],['High','Low','Low'],['High','Medium','Low'],['High','High','Medium']];
const TCOL = {Low:'--low', Medium:'--med', High:'--high'};
function infer(P, g, r){
  const G = terms(P.g_points), R = terms(P.r_points), mg = {}, mr = {};
  for (const k in G) mg[k] = G[k](Math.min(g,20)); for (const k in R) mr[k] = R[k](Math.min(r,25));
  const fired = RULES.map(([a,b,c]) => ({a,b,c,s:Math.min(mg[a], mr[b])}));
  const clip = {Low:0, Medium:0, High:0}; fired.forEach(f => clip[f.c] = Math.max(clip[f.c], f.s));
  const ys = [], agg = []; let num = 0, den = 0;
  for (let k = 0; k <= 100; k++){ const y = k/100; let m = 0; for (const tname in OUT) m = Math.max(m, Math.min(OUT[tname](y), clip[tname])); ys.push(y); agg.push(m); num += y*m; den += m; }
  return {mg, mr, fired, clip, ys, agg, u: den ? num/den : 0.5};
}
function drawMf(canvas, P, x, xmax){
  const [ctx, W, H] = fitCanvas(canvas); ctx.clearRect(0,0,W,H); const pad = 18, X = v => pad + (W-2*pad)*v/xmax, Y = m => H-16 - (H-26)*m;
  const fs = terms(P); ctx.lineWidth = 2;
  for (const k in fs){ ctx.strokeStyle = css(TCOL[k]); ctx.beginPath(); for (let i = 0; i <= 200; i++){ const v = xmax*i/200; i ? ctx.lineTo(X(v),Y(fs[k](v))) : ctx.moveTo(X(v),Y(fs[k](v))); } ctx.stroke(); }
  ctx.strokeStyle = css('--ink'); ctx.lineWidth = 1; ctx.setLineDash([4,3]); ctx.beginPath(); ctx.moveTo(X(x), 6); ctx.lineTo(X(x), H-16); ctx.stroke(); ctx.setLineDash([]);
  ctx.fillStyle = css('--muted'); ctx.font = '11px system-ui'; ctx.textAlign = 'center'; for (let v = 0; v <= xmax; v += 5) ctx.fillText(v, X(v), H-3);
  let i = 0; for (const k in fs){ ctx.fillStyle = css(TCOL[k]); ctx.textAlign = 'left'; ctx.fillText(`${k} ${fs[k](x).toFixed(2)}`, pad + i*((W-2*pad)/3), 12); i++; }
}
function drawFis(){
  const P = D.fuzzy[document.getElementById('pset').value], g = +document.getElementById('g').value, r = +document.getElementById('r').value;
  document.getElementById('gv').textContent = g; document.getElementById('rv').textContent = r;
  drawMf(document.getElementById('cG'), P.g_points, g, 20); drawMf(document.getElementById('cR'), P.r_points, r, 25);
  const res = infer(P, g, r);
  document.getElementById('rules').innerHTML = '<tr><th>#</th><th>IF green</th><th>AND red</th><th>THEN urgency</th><th>strength</th></tr>' +
    res.fired.map((f,i) => `<tr style="opacity:${f.s>0?1:0.45}"><td>${i+1}</td><td>${f.a}</td><td>${f.b}</td><td style="color:var(${TCOL[f.c]});font-weight:600">${f.c}</td><td>${f.s.toFixed(2)}</td></tr>`).join('');
  const c = document.getElementById('cOut'), [ctx, W, H] = fitCanvas(c); ctx.clearRect(0,0,W,H);
  const pad = 22, X = y => pad + (W-2*pad)*y, Y = m => H-20 - (H-34)*m;
  ctx.lineWidth = 1.2; for (const k in OUT){ ctx.strokeStyle = css(TCOL[k]); ctx.setLineDash([3,3]); ctx.beginPath(); res.ys.forEach((y,i)=> i?ctx.lineTo(X(y),Y(OUT[k](y))):ctx.moveTo(X(y),Y(OUT[k](y)))); ctx.stroke(); }
  ctx.setLineDash([]); ctx.fillStyle = css('--fuzzy'); ctx.globalAlpha = 0.28; ctx.beginPath(); ctx.moveTo(X(0), Y(0));
  res.ys.forEach((y,i)=>ctx.lineTo(X(y),Y(res.agg[i]))); ctx.lineTo(X(1),Y(0)); ctx.closePath(); ctx.fill(); ctx.globalAlpha = 1;
  ctx.strokeStyle = css('--ink'); ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(X(res.u), Y(0)); ctx.lineTo(X(res.u), Y(1)); ctx.stroke();
  ctx.strokeStyle = css('--red'); ctx.setLineDash([5,4]); ctx.lineWidth = 1.2; ctx.beginPath(); ctx.moveTo(X(P.theta), Y(0)); ctx.lineTo(X(P.theta), Y(1)); ctx.stroke(); ctx.setLineDash([]);
  ctx.fillStyle = css('--muted'); ctx.font = '11px system-ui'; ctx.textAlign = 'center'; for (let v = 0; v <= 1.0001; v += 0.25) ctx.fillText(v.toFixed(2), X(v), H-6);
  ctx.fillStyle = css('--ink'); ctx.fillText('u = '+res.u.toFixed(3), X(res.u), 10);
  const sw = res.u > P.theta, pill = document.getElementById('decision');
  pill.textContent = sw ? 'END GREEN (switch phase)' : 'HOLD GREEN';
  pill.style.background = sw ? css('--high') : css('--green'); pill.style.color = '#fff';
  document.getElementById('outNote').textContent = `Shaded: aggregated (max of clipped) output set. Solid vertical line: centroid u = ${res.u.toFixed(3)}. Dashed vertical line: threshold theta = ${P.theta.toFixed(2)}. The controller ends the green when u > theta, or at max green (${P.max_green[0].toFixed(0)} s arterial / ${P.max_green[1].toFixed(0)} s side).`;
}
['g','r','pset'].forEach(id => document.getElementById(id).oninput = drawFis);

// ---------------------------------------------------------------- results table
const LAB = {webster:'Webster fixed-time', ga_fixed:'GA fixed-time', fuzzy_hand:'Fuzzy hand-tuned', ga_fuzzy:'GA fuzzy (peak-trained)', ga_fuzzy_mixed:'GA fuzzy (mixed-trained, final)'};
const SL = {offpeak:'Off-peak', moderate:'Moderate', peak:'Peak (steady)', peak_build:'Peak build-up (training scenario)', tidal:'Tidal shift', side_surge:'Side-street surge at J3'};
document.getElementById('restab').innerHTML = '<tr><th>Scenario</th>' + Object.values(LAB).map(l=>`<th>${l}</th>`).join('') + '<th>Final fuzzy vs Webster</th></tr>' +
  Object.entries(D.summary).map(([s,v]) => { const best = Math.min(...Object.values(v)); const imp = D.imp_final ? D.imp_final[s] : 100*(1 - v.ga_fuzzy/v.webster);
    return `<tr><td>${SL[s]||s}</td>` + Object.keys(LAB).map(k=>`<td style="${v[k]===best?'font-weight:700':''}">${v[k]!==undefined?v[k].toFixed(1):'-'}</td>`).join('') + `<td>${imp>=0?'-':'+'}${Math.abs(imp).toFixed(1)} %</td></tr>`; }).join('');

let rz; window.addEventListener('resize', () => { cancelAnimationFrame(rz); rz = requestAnimationFrame(drawAll); });
// deep links, e.g. index.html#t=1800 or index.html#tab=fis&g=2&r=8
const H = new URLSearchParams(location.hash.slice(1));
if (H.get('t')) t = Math.max(0, Math.min(T-1, +H.get('t')));
if (H.get('g')) document.getElementById('g').value = H.get('g');
if (H.get('r')) document.getElementById('r').value = H.get('r');
const tok = {replay:'replay', fuzzy:'fis', fis:'fis', results:'results'}[H.get('tab') || location.hash.slice(1)];
if (tok) { const b = document.querySelector(`.tab[data-tab="${tok}"]`); if (b) { b.click(); } }
drawAll();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main()
