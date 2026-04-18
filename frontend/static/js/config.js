/**
 * MediSkin AI — API Configuration
 * ─────────────────────────────────────────────────────────────────────────────
 * This file sets the backend base URL for ALL JavaScript API calls.
 *
 * HOW IT WORKS:
 *   • In development  → API_BASE_URL = '' (empty string = same-origin relative URLs)
 *   • In production   → API_BASE_URL = your Render backend URL (absolute URL)
 *
 * HOW TO SET FOR PRODUCTION:
 *   1. After deploying to Render, copy your Render service URL,
 *      e.g.  https://mediskin-backend.onrender.com
 *   2. In Django's settings_prod.py or as a template context variable,
 *      the backend injects this value into every HTML page via the
 *      <script> block in each template, OR you can hard-code it here
 *      before pushing to GitHub for deployment.
 *
 * QUICK DEPLOYMENT CHANGE:
 *   Replace the value of MEDISKIN_API_BASE below with your Render URL,
 *   then push to GitHub. Render will redeploy automatically.
 * ─────────────────────────────────────────────────────────────────────────────
 */

(function () {
    // ── In development: leave as empty string (relative URLs like /api/predict/)
    // ── In production:  set to your Render URL (no trailing slash)
    //    e.g. 'https://mediskin-backend.onrender.com'
    var BACKEND_URL = '';

    // Try to read from a <meta> tag injected by Django (preferred approach)
    // The meta tag format is: <meta name="api-base-url" content="https://...">
    var metaTag = document.querySelector('meta[name="api-base-url"]');
    if (metaTag && metaTag.content && metaTag.content !== '{{ API_BASE_URL }}') {
        BACKEND_URL = metaTag.content.replace(/\/$/, '');  // strip trailing slash
    }

    // Expose globally so all other JS files can use it
    window.MEDISKIN_API_BASE = BACKEND_URL;

    console.log('[MediSkin] API base URL:', window.MEDISKIN_API_BASE || '(same-origin)');
})();
