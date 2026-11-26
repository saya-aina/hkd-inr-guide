// Google Analytics 4.
// Measurement ID for nriremit.com. Clear it to switch analytics off.
(function () {
  var GA_ID = "G-SGHMR2TL71";
  if (!GA_ID || /^(localhost|127\.)/.test(location.hostname)) return;
  var s = document.createElement("script");
  s.async = true;
  s.src = "https://www.googletagmanager.com/gtag/js?id=" + GA_ID;
  document.head.appendChild(s);
  window.dataLayer = window.dataLayer || [];
  function gtag() { dataLayer.push(arguments); }
  window.gtag = gtag;
  gtag("js", new Date());
  gtag("config", GA_ID, {
    anonymize_ip: true,
    allow_google_signals: false,
    allow_ad_personalization_signals: false
  });
  // Count clicks on provider/affiliate buttons, so we can see what earns.
  document.addEventListener("click", function (e) {
    var a = e.target.closest && e.target.closest("a[href^='http']");
    if (!a || a.hostname === location.hostname) return;
    gtag("event", "outbound_click", { link_domain: a.hostname, link_text: (a.textContent || "").trim().slice(0, 60) });
  });
})();
