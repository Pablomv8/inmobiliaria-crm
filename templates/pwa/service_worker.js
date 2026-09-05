const CACHE_PREFIX = 'inmocrm-static-';
const CACHE_NAME = `${CACHE_PREFIX}{{ pwa_cache_version|escapejs }}`;
const CORE_ASSETS = {{ pwa_core_assets_json|safe }};

self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => cache.addAll(CORE_ASSETS))
            .then(() => self.skipWaiting())
    );
});

self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys()
            .then(keys => Promise.all(
                keys
                    .filter(key => key.startsWith(CACHE_PREFIX) && key !== CACHE_NAME)
                    .map(key => caches.delete(key))
            ))
            .then(() => self.clients.claim())
    );
});

self.addEventListener('fetch', event => {
    const request = event.request;
    if (request.method !== 'GET') return;

    const url = new URL(request.url);
    if (url.origin !== self.location.origin) return;

    // Las pantallas del CRM siempre se solicitan a la red y nunca se guardan.
    if (request.mode === 'navigate') {
        event.respondWith(
            fetch(request).catch(() => caches.match('/offline/'))
        );
        return;
    }

    // Solo los recursos públicos de /static/ pueden persistir en el dispositivo.
    if (!url.pathname.startsWith('/static/')) return;

    event.respondWith(
        caches.match(request).then(cachedResponse => {
            if (cachedResponse) return cachedResponse;

            return fetch(request).then(networkResponse => {
                if (!networkResponse || !networkResponse.ok) {
                    return networkResponse;
                }
                const copy = networkResponse.clone();
                caches.open(CACHE_NAME).then(cache => cache.put(request, copy));
                return networkResponse;
            });
        })
    );
});
