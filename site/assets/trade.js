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
    if (!d.countries.length) tb.appendChild(h("tr", {}, "")).appendChild(h("td", { colspan: "4", class: "muted" }, "No country detail for this month."));
    d.countries.forEach(c => {
      const tr = h("tr");
      tr.append(h("td", {}, c.name), h("td", { class: "num" }, "$" + big(c.value)),
        h("td", { class: "num" }, c.qty > 0 ? big(c.qty) + (unit ? " " + unit : "") : "—"), h("td", { class: "num" }, c.share_pct.toFixed(1) + "%"));
      tb.appendChild(tr);
    });
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
