(function () {
  "use strict";
  const { h, day } = SBR;
  const TOPICS = ["All", "Feedstock costs", "Trade policy", "Tire industry", "Sustainability", "Industry"];
  let items = [], topic = "All";

  function render() {
    const list = document.getElementById("list");
    list.innerHTML = "";
    const shown = items.filter(i => topic === "All" || i.category === topic);
    if (!shown.length) {
      list.appendChild(h("li", { class: "muted" }, items.length ? "No headlines on this topic right now. Choose All to see everything." : "Headlines appear here after the first news update."));
      return;
    }
    shown.forEach(i => {
      const li = h("li");
      li.appendChild(h("a", { class: "title", href: i.url, target: "_blank", rel: "noopener" }, i.title));
      li.appendChild(h("p", { class: "meta" }, i.source + (i.published ? " · " + day(i.published) : "") + " · " + i.category));
      if (i.excerpt) li.appendChild(h("p", {}, i.excerpt));
      list.appendChild(li);
    });
  }

  function chips() {
    const ul = document.getElementById("chips");
    ul.innerHTML = "";
    TOPICS.forEach(t => {
      const li = h("li");
      const b = h("button", { type: "button", "aria-pressed": String(t === topic) }, t);
      b.addEventListener("click", () => { topic = t; chips(); render(); });
      li.appendChild(b);
      ul.appendChild(li);
    });
  }

  chips();
  SBR.json("/data/news.json").then(d => { items = d.items || []; render(); }).catch(() => {
    document.getElementById("list").innerHTML = "";
    document.getElementById("list").appendChild(h("li", { class: "muted" }, "News couldn't be loaded. Check your connection and refresh."));
  });
})();
