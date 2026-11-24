(function () {
  "use strict";
  const $ = id => document.getElementById(id);
  const { h, num, month, day, change } = SBR;

  function pending(li, text) {
    const v = li.querySelector(".val");
    v.innerHTML = "";
    v.appendChild(h("span", { class: "pending" }, text || "Data pending"));
  }

  function value(li, n, unit) {
    const v = li.querySelector(".val");
    v.textContent = n;
    if (unit) v.appendChild(h("small", {}, unit));
  }

  function context(li, text, pct, suffix) {
    const p = li.querySelector(".ctx");
    p.textContent = text + " ";
    const s = h("span");
    change(s, pct, suffix);
    p.appendChild(s);
  }

  function renderIndex(rec) {
    $("index-name").textContent = rec.name || "Uncured Rubber Scrap Index";
    const v = $("index-value"), meta = $("index-meta");
    meta.textContent = "";
    const link = h("a", { href: "https://market-recycle.com/" }, "Published by market-recycle.com");
    if (!rec.latest) {
      v.className = "index-value pending";
      v.textContent = "First value publishes when the methodology takes effect.";
      meta.appendChild(link);
      return;
    }
    v.className = "index-value";
    v.textContent = rec.latest.value.toFixed(1);
    meta.appendChild(document.createTextNode(month(rec.latest.month) + " · "));
    const c = h("span", { class: rec.latest.change_pct >= 0 ? "up" : "down" },
      rec.latest.change_pct === null ? "first value" :
      (rec.latest.change_pct >= 0 ? "▲ " : "▼ ") + Math.abs(rec.latest.change_pct).toFixed(1) + "% on the month");
    meta.append(c, h("br"), link);
  }

  function renderOutlook(o) {
    const p = $("outlook-text");
    if (o && o.status === "published" && o.text) {
      p.className = "outlook-text";
      p.textContent = o.text;
      if (o.month) p.appendChild(h("span", { class: "asof" }, " Outlook for " + month(o.month) + "."));
    } else {
      p.className = "outlook-text pending";
      p.textContent = "A written outlook publishes each month alongside the index.";
    }
  }

  function renderFactors(d) {
    const f = d.factors || {};
    const li = k => document.querySelector(`[data-f="${k}"]`);

    if (f.scrap) {
      value(li("scrap"), "$" + num(f.scrap.value, 3), "/kg");
      context(li("scrap"), "U.S. exports, three months to " + month(f.scrap.month) + ".", f.scrap.change_yoy_pct, "vs a year earlier");
    } else pending(li("scrap"));

    if (f.virgin) {
      value(li("virgin"), "$" + num(f.virgin.value), "/kg");
      context(li("virgin"), "TSR20, " + month(f.virgin.month) + ".", f.virgin.change_pct, "on the month");
    } else pending(li("virgin"));

    const rows = li("currencies").querySelector(".fx-rows");
    rows.innerHTML = "";
    const fx = Object.entries(d.fx || {}).filter(([, v]) => v.latest);
    if (fx.length) {
      const avg = fx.reduce((s, [, v]) => s + (v.strength_30d_pct || 0), 0) / fx.length;
      value(li("currencies"), avg >= 0 ? "Stronger" : "Weaker");
      fx.forEach(([code, v]) => {
        const row = h("div");
        row.append(h("dt", {}, v.country), change(h("dd"), v.strength_30d_pct));
        rows.appendChild(row);
      });
      rows.appendChild(Object.assign(h("p", { class: "ctx small" }, "Average move against the dollar over 30 days. Up means the currency buys more dollars, which makes U.S. scrap cheaper for buyers there."), { style: "grid-column:1/-1;margin:4px 0 0" }));
    } else pending(li("currencies"));

    if (f.energy) {
      value(li("energy"), "$" + num(f.energy.value), "/bbl");
      context(li("energy"), "Brent crude, " + day(f.energy.date) + ".", f.energy.change_30d_pct, "over 30 days");
    } else pending(li("energy"));

    if (f.policy) {
      value(li("policy"), String(f.policy.count_30d), f.policy.count_30d === 1 ? "headline" : "headlines");
      const p = li("policy").querySelector(".ctx");
      p.textContent = "";
      if (f.policy.latest.length) {
        p.append("Latest: ");
        const a = h("a", { href: f.policy.latest[0].url, rel: "noopener", target: "_blank" }, f.policy.latest[0].title);
        p.append(a, " (" + f.policy.latest[0].source + ")");
      } else p.textContent = "No tariff or trade headlines in industry news in the last 30 days.";
    } else pending(li("policy"));

    const dates = [f.energy && day(f.energy.date), f.virgin && "rubber " + month(f.virgin.month), d.trade && d.trade.asof_month && "trade " + month(d.trade.asof_month)].filter(Boolean);
    $("asof").textContent = dates.length ? "Latest data: " + dates.join(" · ") : "Data is being collected. Figures appear here as each public source reports.";
  }

  SBR.json("/data/dashboard.json").then(renderFactors).catch(() => {
    $("asof").textContent = "The market data couldn't be loaded. Check your connection and refresh.";
    document.querySelectorAll(".factor").forEach(li => pending(li, "Unavailable"));
  });
  SBR.json("/data/outlook.json").then(renderOutlook).catch(() => renderOutlook(null));
  SBR.json(SBR.config.indexUrl).then(renderIndex).catch(() => {
    $("index-value").className = "index-value pending";
    $("index-value").textContent = "The index couldn't be loaded right now.";
    $("index-meta").textContent = "";
    $("index-meta").appendChild(h("a", { href: "https://market-recycle.com/" }, "See market-recycle.com"));
  });
})();
