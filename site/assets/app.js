/* Shared helpers for every SBR Compound page. */
(function (g) {
  "use strict";
  const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];

  const SBR = {
    config: { indexUrl: "https://market-recycle.com/data/index.json", newsletter: { provider: "buttondown", username: "" } },

    json(url) {
      return fetch(url, { cache: "no-cache" }).then(r => { if (!r.ok) throw new Error(url + " " + r.status); return r.json(); });
    },
    month(m) { return m ? MONTHS[Number(m.slice(5, 7)) - 1] + " " + m.slice(0, 4) : "—"; },
    day(d) {
      if (!d) return "—";
      const x = new Date(d.length === 10 ? d + "T12:00:00Z" : d);
      return x.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric", timeZone: "UTC" });
    },
    num(v, digits) {
      if (v === null || v === undefined) return "—";
      return Number(v).toLocaleString("en-US", { minimumFractionDigits: digits ?? 2, maximumFractionDigits: digits ?? 2 });
    },
    big(v) {
      if (v === null || v === undefined) return "—";
      const a = Math.abs(v);
      if (a >= 1e9) return (v / 1e9).toFixed(1) + "B";
      if (a >= 1e6) return (v / 1e6).toFixed(1) + "M";
      if (a >= 1e3) return (v / 1e3).toFixed(0) + "K";
      return String(Math.round(v));
    },
    /* A signed percent with a direction word for screen readers and color-blind readers. */
    change(el, pct, suffix) {
      el.textContent = "";
      if (pct === null || pct === undefined) { el.textContent = "no change data yet"; el.className = "chg"; return el; }
      const s = document.createElement("span");
      s.className = "chg " + (pct > 0 ? "up" : pct < 0 ? "down" : "");
      s.textContent = (pct > 0 ? "▲ up " : pct < 0 ? "▼ down " : "unchanged ") + (pct ? Math.abs(pct).toFixed(1) + "%" : "");
      el.appendChild(s);
      if (suffix) el.appendChild(document.createTextNode(" " + suffix));
      return el;
    },
    h(tag, attrs, text) {
      const n = document.createElement(tag);
      for (const k in attrs || {}) n.setAttribute(k, attrs[k]);
      if (text !== undefined) n.textContent = text;
      return n;
    },
  };

  // Offline notice, and the service worker that lets the app open without a connection.
  function offline() {
    let bar = document.querySelector(".offline");
    if (!navigator.onLine && !bar) {
      bar = SBR.h("div", { class: "offline", role: "status" }, "You're offline. Showing the last data saved on this device.");
      document.body.prepend(bar);
    } else if (navigator.onLine && bar) bar.remove();
  }
  addEventListener("online", offline);
  addEventListener("offline", offline);
  offline();
  if ("serviceWorker" in navigator) addEventListener("load", () => navigator.serviceWorker.register("/sw.js").catch(() => {}));

  g.SBR = SBR;
})(window);
