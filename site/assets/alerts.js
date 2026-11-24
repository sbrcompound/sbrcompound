(function () {
  "use strict";
  // Signup only appears once a newsletter account is configured in app.js (SBR.config.newsletter).
  // Until then the page says alerts are coming, rather than collecting addresses nobody will email.
  const n = SBR.config.newsletter || {};
  const form = document.getElementById("signup");
  if (n.provider === "buttondown" && n.username) {
    form.action = "https://buttondown.com/api/emails/embed-subscribe/" + encodeURIComponent(n.username);
    form.hidden = false;
  } else {
    document.getElementById("not-ready").hidden = false;
  }
})();
