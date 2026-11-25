(function () {
  "use strict";
  const { h, num, month, day, change, big } = SBR;

  function sparkline(points) {
    const NS = "http://www.w3.org/2000/svg";
    const svg = document.createElementNS(NS, "svg");
    svg.setAttribute("viewBox", "0 0 96 28");
    svg.setAttribute("class", "spark");
    svg.setAttribute("aria-hidden", "true");
    if (!points || points.length < 2) return svg;
    const ys = points.map(p => p[1]), lo = Math.min(...ys), hi = Math.max(...ys), span = hi - lo || 1;
    const d = points.map((p, i) => (i ? "L" : "M") + (i / (points.length - 1) * 94 + 1).toFixed(1) + " " + (26 - (p[1] - lo) / span * 24).toFixed(1)).join("");
    const path = document.createElementNS(NS, "path");
    path.setAttribute("d", d);
    path.setAttribute("fill", "none");
    path.setAttribute("stroke", "var(--chart-line)");
    path.setAttribute("stroke-width", "1.5");
    svg.appendChild(path);
    return svg;
  }

  function priceBlock(sec, data) {
    const [group, key] = sec.dataset.p.split(".");
    const blk = data[group] && data[group][key];
    sec.innerHTML = "";
    const head = h("div", { class: "chart-head" });
    head.appendChild(h("h3", {}, sec.dataset.name));
    sec.appendChild(head);
    if (!blk) { sec.appendChild(h("p", { class: "pending-note" }, "Data pending")); return; }
    const isDaily = !!blk.latest.date;
    const v = h("span", { class: "val" }, "$" + num(blk.latest.value) + " ");
    v.appendChild(h("small", { class: "muted" }, sec.dataset.unit.replace("$", "")));
    head.appendChild(v);
    const sub = h("p", { class: "small muted", style: "margin:2px 0 0" }, (isDaily ? day(blk.latest.date) : month(blk.latest.month)) + " · ");
    sub.appendChild(change(h("span"), isDaily ? blk.change_30d_pct : blk.change_pct, isDaily ? "over 30 days" : "on the month"));
    sec.appendChild(sub);
    const box = h("div");
    sec.appendChild(box);
    lineChart(box, blk.series.map(([x, y]) => ({ x, y })), {
      label: sec.dataset.name + " price", unit: sec.dataset.unit, height: 200, format: y => num(y),
    });
  }

  function tradeTable(groups) {
    const root = document.getElementById("trade");
    root.innerHTML = "";
    groups.forEach(g => {
      root.appendChild(h("h3", { class: "group-title" }, g.name));
      const wrap = h("div", { class: "table-scroll" });
      const t = h("table", { class: "trade-table" });
      t.innerHTML = "<colgroup><col class='c-name'><col class='c-flow'><col class='c-month'><col class='c-qty'><col class='c-chg'><col class='c-uv'><col class='c-spark'></colgroup><thead><tr><th>Material</th><th>Flow</th><th class='num'>Latest month</th><th class='num'>Volume</th><th class='num'>vs 12-mo avg</th><th class='num'>Unit value</th><th class='num'><span class='sr-only'>Trend</span></th></tr></thead>";
      const tb = h("tbody");
      g.lines.forEach(l => {
        const tr = h("tr", { class: "link-row" });
        const href = "/trade.html?id=" + encodeURIComponent(l.id);
        const name = h("td");
        const a = h("a", { href }, l.label);
        name.append(a, h("span", { class: "code" }, "HTS " + l.hts));
        tr.appendChild(name);
        tr.appendChild(h("td", {}, l.flow === "exports" ? "Exports" : "Imports"));
        if (l.latest_month) {
          tr.appendChild(h("td", { class: "num" }, month(l.latest_month)));
          tr.appendChild(l.measure === "value"
            ? h("td", { class: "num", title: "Census reports dollar value only for this code" }, "$" + big(l.value))
            : h("td", { class: "num" }, big(l.qty) + (l.unit ? " " + (l.unit === "tire" ? "tires" : l.unit) : "")));
          tr.appendChild(change(h("td", { class: "num" }), l.qty_vs_12m_pct));
          tr.appendChild(h("td", { class: "num" }, l.unit_value === null || l.unit_value === undefined ? "—" : "$" + num(l.unit_value) + "/" + l.unit));
          const sp = h("td", { class: "num" });
          sp.appendChild(sparkline(l.spark));
          tr.appendChild(sp);
        } else {
          const td = h("td", { class: "num muted", colspan: "5" }, "Data pending");
          tr.appendChild(td);
        }
        tr.addEventListener("click", e => { if (e.target.tagName !== "A") location.href = href; });
        tb.appendChild(tr);
      });
      t.appendChild(tb);
      wrap.appendChild(t);
      root.appendChild(wrap);
    });
  }

  SBR.json("/data/dashboard.json").then(d => {
    const b = document.getElementById("banner");
    b.textContent = d.trade.asof_month
      ? "Census trade data through " + month(d.trade.asof_month) + " (released about five weeks after each month ends). Oil prices update daily; rubber prices monthly."
      : "Figures appear here as each public source reports. Census trade data is released about five weeks after each month ends.";
    document.querySelectorAll("[data-p]").forEach(sec => priceBlock(sec, d));
    tradeTable(d.trade.groups);
  }).catch(() => {
    document.getElementById("banner").textContent = "The market data couldn't be loaded. Check your connection and refresh.";
  });
})();
