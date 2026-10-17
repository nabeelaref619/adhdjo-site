/* Privacy controls for pages with the Google AdSense tag. No tool data is read. */
(() => {
  'use strict';
  const button = document.querySelector('[data-ad-privacy]');
  if (!button) return;
  window.googlefc = window.googlefc || {};
  window.googlefc.callbackQueue = window.googlefc.callbackQueue || [];
  window.googlefc.callbackQueue.push({
    CONSENT_API_READY: () => {
      if (typeof window.__tcfapi !== 'function') return;
      window.__tcfapi('addEventListener', 0, (data, success) => {
        button.hidden = !(success && data && data.gdprApplies);
      });
    }
  });
  button.addEventListener('click', () => {
    window.googlefc.callbackQueue.push({
      CONSENT_API_READY: () => window.googlefc.showRevocationMessage()
    });
  });
})();
