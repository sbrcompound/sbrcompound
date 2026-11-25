/* Offline support: pages and assets from cache first; data from the network first,
   falling back to the last copy saved on the device. */
const VERSION = "sbr-v4";
const SHELL = ["/", "/markets.html", "/trade.html", "/news.html", "/alerts.html", "/privacy.html",
  "/assets/site.css", "/assets/app.js", "/assets/chart.js", "/assets/home.js", "/assets/markets.js",
  "/assets/trade.js", "/assets/news.js", "/assets/alerts.js", "/assets/fonts/archivo-latin-wdth-normal.woff2",
  "/assets/icons/icon.svg", "/manifest.webmanifest"];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(VERSION).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
});
self.addEventListener("activate", e => {
  e.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k !== VERSION).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});
self.addEventListener("fetch", e => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  const isData = url.pathname.startsWith("/data/") || url.hostname === "market-recycle.com";
  if (isData) {
    e.respondWith(fetch(req).then(res => {
      if (res.ok) { const copy = res.clone(); caches.open(VERSION).then(c => c.put(req, copy)); }
      return res;
    }).catch(() => caches.match(req, { ignoreSearch: false }).then(r => r || Response.error())));
    return;
  }
  if (url.origin !== location.origin) return;
  e.respondWith(caches.match(req, { ignoreSearch: true }).then(hit => {
    const net = fetch(req).then(res => {
      if (res.ok) { const copy = res.clone(); caches.open(VERSION).then(c => c.put(req, copy)); }
      return res;
    }).catch(() => hit);
    return hit || net;
  }));
});
