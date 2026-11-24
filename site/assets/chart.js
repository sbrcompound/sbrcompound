/* Small dependency-free line chart with a hover/touch crosshair and tooltip.
   lineChart(container, points, opts)
     points: [{x: "2026-09" | "2026-11-20", y: number}, ...] sorted by x
     opts: { label, unit, format(y), xLabel(x), height, baseline }
   Colors come from CSS variables --chart-line, --chart-grid, --muted, --ink. */
(function (global) {
  "use strict";
  const NS = "http://www.w3.org/2000/svg";
  const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

  function el(name, attrs, parent) {
    const n = document.createElementNS(NS, name);
    for (const k in attrs) n.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(n);
    return n;
  }

  function defaultXLabel(x) {
    const m = Number(x.slice(5, 7));
    if (x.length === 7) return MONTHS[m - 1] + " " + x.slice(0, 4);
    return MONTHS[m - 1] + " " + Number(x.slice(8, 10)) + ", " + x.slice(0, 4);
  }

  function niceTicks(min, max, count) {
    const span = max - min || Math.abs(max) || 1;
    const step0 = span / count;
    const mag = Math.pow(10, Math.floor(Math.log10(step0)));
    const step = [1, 2, 2.5, 5, 10].map(s => s * mag).find(s => s >= step0);
    const lo = Math.floor(min / step) * step, hi = Math.ceil(max / step) * step;
    const out = [];
    for (let v = lo; v <= hi + step / 2; v += step) out.push(+v.toFixed(10));
    return out;
  }

  function lineChart(container, points, opts) {
    opts = opts || {};
    container.innerHTML = "";
    container.classList.add("chart");
    if (!points || points.length < 2) {
      const p = document.createElement("p");
      p.className = "muted small";
      p.textContent = "Not enough data yet to draw a chart.";
      container.appendChild(p);
      return;
    }
    const fmt = opts.format || (y => y.toLocaleString(undefined, { maximumFractionDigits: 2 }));
    const xLabel = opts.xLabel || defaultXLabel;
    const W = Math.max(300, Math.round(container.clientWidth || 720)), H = opts.height || 240, L = 52, R = 14, T = 12, B = 30;
    const ys = points.map(p => p.y);
    let min = Math.min(...ys), max = Math.max(...ys);
    if (opts.baseline !== undefined) { min = Math.min(min, opts.baseline); max = Math.max(max, opts.baseline); }
    const pad = (max - min) * 0.08 || 1;
    const ticks = niceTicks(min - pad, max + pad, 4);
    const y0 = ticks[0], y1 = ticks[ticks.length - 1];
    const X = i => L + (i / (points.length - 1)) * (W - L - R);
    const Y = v => T + (1 - (v - y0) / (y1 - y0)) * (H - T - B);

    const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, width: W, height: H, role: "img", "aria-label": opts.label || "Line chart" });
    const grid = el("g", {}, svg);
    ticks.forEach(t => {
      el("line", { x1: L, x2: W - R, y1: Y(t), y2: Y(t), stroke: "var(--chart-grid)", "stroke-width": 1 }, grid);
      const tx = el("text", { x: L - 8, y: Y(t) + 4, "text-anchor": "end", "font-size": 12, fill: "var(--muted)" }, grid);
      tx.textContent = fmt(t);
    });
    if (opts.baseline !== undefined) {
      el("line", { x1: L, x2: W - R, y1: Y(opts.baseline), y2: Y(opts.baseline), stroke: "var(--muted)", "stroke-width": 1, "stroke-dasharray": "3 4" }, grid);
    }
    // x labels: first, middle, last
    [0, Math.floor((points.length - 1) / 2), points.length - 1].forEach((i, k) => {
      const tx = el("text", { x: X(i), y: H - 8, "text-anchor": ["start", "middle", "end"][k], "font-size": 12, fill: "var(--muted)" }, grid);
      tx.textContent = xLabel(points[i].x);
    });
    const d = points.map((p, i) => (i ? "L" : "M") + X(i).toFixed(1) + " " + Y(p.y).toFixed(1)).join("");
    el("path", { d, fill: "none", stroke: "var(--chart-line)", "stroke-width": 2, "stroke-linejoin": "round", "stroke-linecap": "round" }, svg);
    const last = points[points.length - 1];
    el("circle", { cx: X(points.length - 1), cy: Y(last.y), r: 4, fill: "var(--chart-line)", stroke: "var(--surface)", "stroke-width": 2 }, svg);

    const cross = el("line", { y1: T, y2: H - B, stroke: "var(--muted)", "stroke-width": 1, visibility: "hidden" }, svg);
    const dot = el("circle", { r: 5, fill: "var(--chart-line)", stroke: "var(--surface)", "stroke-width": 2, visibility: "hidden" }, svg);
    const hit = el("rect", { x: L, y: T, width: W - L - R, height: H - T - B, fill: "transparent" }, svg);
    container.appendChild(svg);

    const tip = document.createElement("div");
    tip.className = "tip";
    tip.hidden = true;
    container.appendChild(tip);

    function show(evt) {
      const box = svg.getBoundingClientRect();
      const px = ((evt.touches ? evt.touches[0].clientX : evt.clientX) - box.left) * (W / box.width);
      const i = Math.max(0, Math.min(points.length - 1, Math.round(((px - L) / (W - L - R)) * (points.length - 1))));
      const p = points[i];
      cross.setAttribute("x1", X(i)); cross.setAttribute("x2", X(i));
      dot.setAttribute("cx", X(i)); dot.setAttribute("cy", Y(p.y));
      cross.setAttribute("visibility", "visible"); dot.setAttribute("visibility", "visible");
      tip.innerHTML = "<strong></strong><span></span>";
      tip.firstChild.textContent = fmt(p.y) + (opts.unit ? " " + opts.unit : "");
      tip.lastChild.textContent = xLabel(p.x);
      tip.hidden = false;
      tip.style.left = (X(i) / W) * box.width + "px";
      tip.style.top = (Y(p.y) / H) * box.height + "px";
    }
    function hide() { tip.hidden = true; cross.setAttribute("visibility", "hidden"); dot.setAttribute("visibility", "hidden"); }
    hit.addEventListener("mousemove", show);
    hit.addEventListener("touchstart", show, { passive: true });
    hit.addEventListener("touchmove", show, { passive: true });
    hit.addEventListener("mouseleave", hide);
    hit.addEventListener("touchend", hide);

    if (container.nextElementSibling && container.nextElementSibling.matches("details.data")) container.nextElementSibling.remove();
    if (opts.table !== false) {
      const det = document.createElement("details");
      det.className = "data";
      det.innerHTML = "<summary>Show the numbers</summary>";
      const wrap = document.createElement("div");
      wrap.className = "table-scroll";
      const tbl = document.createElement("table");
      tbl.innerHTML = "<thead><tr><th>Period</th><th class='num'>Value</th></tr></thead><tbody></tbody>";
      points.slice().reverse().forEach(p => {
        const tr = document.createElement("tr");
        const a = document.createElement("td"); a.textContent = xLabel(p.x);
        const b = document.createElement("td"); b.className = "num"; b.textContent = fmt(p.y) + (opts.unit ? " " + opts.unit : "");
        tr.append(a, b); tbl.tBodies[0].appendChild(tr);
      });
      wrap.appendChild(tbl); det.appendChild(wrap);
      container.after(det);
    }
  }

  function responsive(container, points, opts) {
    lineChart(container, points, opts);
    let last = container.clientWidth, t;
    if (!container._sized) {
      container._sized = true;
      addEventListener("resize", () => {
        clearTimeout(t);
        t = setTimeout(() => { if (Math.abs(container.clientWidth - last) > 20) { last = container.clientWidth; lineChart(container, points, opts); } }, 150);
      });
    }
  }

  global.lineChart = responsive;
  global.monthLabel = defaultXLabel;
})(window);
