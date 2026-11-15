/*
  Cross-origin isolation for static hosts that cannot set response headers
  (e.g. GitHub Pages). Loaded as a normal <script> it registers itself as a
  service worker; as a service worker it adds COOP/COEP to every response.
  Being cross-origin isolated lets onnxruntime-web use several WASM threads.
  On a host that already sends the headers (serve.py) it does nothing.
*/
if (typeof window === 'undefined') {
  // ---- service worker ----
  self.addEventListener('install', () => self.skipWaiting());
  self.addEventListener('activate', e => e.waitUntil(self.clients.claim()));
  self.addEventListener('fetch', e => {
    const req = e.request;
    if (req.cache === 'only-if-cached' && req.mode !== 'same-origin') return;
    if (new URL(req.url).origin !== self.location.origin) return;
    e.respondWith(fetch(req).then(res => {
      if (res.status === 0 || res.type === 'opaque') return res;
      const h = new Headers(res.headers);
      h.set('Cross-Origin-Opener-Policy', 'same-origin');
      h.set('Cross-Origin-Embedder-Policy', 'require-corp');
      h.set('Cross-Origin-Resource-Policy', 'same-origin');
      return new Response(res.body, { status: res.status, statusText: res.statusText, headers: h });
    }));
  });
} else {
  // ---- page ----
  (() => {
    const KEY = 'coi-reloaded';
    if (window.crossOriginIsolated) { try { sessionStorage.removeItem(KEY); } catch (e) {} return; }
    if (!window.isSecureContext || !('serviceWorker' in navigator)) return;
    let reloaded = false;
    try { reloaded = sessionStorage.getItem(KEY) === '1'; } catch (e) {}
    navigator.serviceWorker.register(document.currentScript.src).then(() => navigator.serviceWorker.ready).then(() => {
      // reload once so the page itself is served through the worker; never loop
      if (!reloaded) { try { sessionStorage.setItem(KEY, '1'); } catch (e) {} location.reload(); }
    }).catch(err => console.warn('coi-sw: registration failed, running single-threaded', err));
  })();
}
