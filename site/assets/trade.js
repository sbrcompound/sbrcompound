(function () {
  "use strict";
  const { h, num, month, big } = SBR;
  const id = new URLSearchParams(location.search).get("id") || "";
  const $ = x => document.getElementById(x);

  if (!/^[a-z0-9-]+$/.test(id)) {
    $("title").textContent = "Choose a material";
    $("sub").textContent = "This page needs a material from the Markets list.";
    $("partners").innerHTML = "";
    return;
  }

  SBR.json("/data/trade/" + id + ".json").then(d => {
    const unit = d.unit === "tire" ? "tires" : d.unit;
    document.title = d.label + " | SBR Compound";
    $("title").textContent = d.label;
    $("sub").textContent = "HTS " + d.hts + " · U.S. " + d.flow + " · through " + month(d.latest_month);
    const hasQty = d.months.some(m => m.qty > 0);
    if (hasQty) {
      lineChart($("qty"), d.months.map(m => ({ x: m.month, y: m.qty })), {
        label: d.label + " monthly volume", unit, height: 200, format: big,
      });
      const uv = d.months.filter(m => m.unit_value !== null).map(m => ({ x: m.month, y: m.unit_value }));
      lineChart($("uv"), uv, { label: d.label + " unit value", unit: d.unit ? "$/" + d.unit : "", height: 200, format: y => "$" + num(y) });
    } else {
      // Census reports dollar value only at this level: chart value, drop unit value.
      $("qty").closest("section").querySelector("h3").textContent = "Monthly value";
      lineChart($("qty"), d.months.map(m => ({ x: m.month, y: m.value })), {
        label: d.label + " monthly value", unit: "$", height: 200, format: y => "$" + big(y),
      });
      $("uv").appendChild(h("p", { class: "pending-note" }, "Census doesn't report quantities for this code, so there's no unit value."));
    }
    $("partners-h").textContent = "Top partner countries, " + month(d.latest_month);
    const tb = $("partners");
    tb.innerHTML = "";
    if (!d.countries.length) tb.appendChild(h("tr", {}, "")).appendChild(h("td", { colspan: "5", class: "muted" }, "No country detail for this month."));
    d.countries.forEach(c => {
      const tr = h("tr");
      tr.append(h("td", {}, c.name), h("td", { class: "num" }, "$" + big(c.value)),
        h("td", { class: "num" }, c.qty > 0 ? big(c.qty) + (unit ? " " + unit : "") : "—"),
        h("td", { class: "num" }, c.qty > 0 && d.unit ? "$" + num(c.value / c.qty) + "/" + d.unit : "—"),
        h("td", { class: "num" }, c.share_pct.toFixed(1) + "%"));
      tb.appendChild(tr);
    });
    if (d.grades && d.grades.months.length) {
      const G = d.grades, gm = G.months;
      $("grades-sec").hidden = false;
      $("grades-note").textContent = G.bands.note || "";
      const perLb = v => (v * 100 / 2.20462).toFixed(1) + "¢/lb";
      const unc = gm.filter(r => r.uncured.unit_value !== null);
      lineChart($("g-uv"), unc.map(r => ({ x: r.month, y: r.uncured.unit_value })), {
        label: "Estimated uncured scrap export price", unit: "$/kg", height: 200, format: y => "$" + num(y) + "/kg",
      });
      lineChart($("g-q"), gm.map(r => ({ x: r.month, y: r.uncured.qty })), {
        label: "Estimated uncured scrap export volume", unit: "kg", height: 200, format: big,
      });
      const lastU = unc[unc.length - 1];
      if (lastU) {
        $("g-uv-now").textContent = perLb(lastU.uncured.unit_value);
        $("g-q-now").textContent = big(gm[gm.length - 1].uncured.qty) + " kg";
      }
      const yr = gm.slice(-12), sums = {};
      ["uncured", "mixed", "cured"].forEach(k => {
        sums[k] = yr.reduce((a, r) => ({ q: a.q + r[k].qty, v: a.v + r[k].value }), { q: 0, v: 0 });
      });
      const allQ = sums.uncured.q + sums.mixed.q + sums.cured.q || 1;
      const names = { uncured: "Likely uncured", mixed: "Mixed or unclear", cured: "Likely cured" };
      ["uncured", "mixed", "cured"].forEach(k => {
        const x = sums[k];
        const tr = h("tr");
        tr.append(h("td", {}, names[k]), h("td", { class: "num" }, big(x.q) + " kg"),
          h("td", { class: "num" }, (x.q / allQ * 100).toFixed(1) + "%"), h("td", { class: "num" }, "$" + big(x.v)),
          h("td", { class: "num" }, x.q ? perLb(x.v / x.q) : "—"));
        $("grades").appendChild(tr);
      });
    }
    if (d.ports && d.ports.rows.length) {
      $("ports-sec").hidden = false;
      const [a, b] = d.ports.months;
      $("ports-h").textContent = (d.flow === "exports" ? "Top U.S. export ports, " : "Top U.S. entry ports, ") + (a === b ? month(a) : month(a) + " to " + month(b));
      const pb = $("ports");
      d.ports.rows.forEach(r => {
        const tr = h("tr");
        tr.append(h("td", {}, r.name), h("td", { class: "num" }, "$" + big(r.value)), h("td", { class: "num" }, r.share_pct.toFixed(1) + "%"));
        pb.appendChild(tr);
      });
    }
  }).catch(() => {
    $("sub").textContent = "No data yet for this material. Census figures appear after the first monthly update.";
    $("partners").innerHTML = "";
    ["qty", "uv"].forEach(x => { $(x).appendChild(h("p", { class: "pending-note" }, "Data pending")); });
  });
})();
