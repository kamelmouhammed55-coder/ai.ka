const CACHE_NAME = 'moka-ai-v1';
const ASSETS = ['/', '/style.css', '/app.js'];

self.addEventListener('install', (e) => {
    e.waitUntil(caches.open(CACHE_NAME).then(cache => cache.addAll(ASSETS)));
});

self.addEventListener('fetch', (e) => {
    e.respondWith(caches.match(e.request).then(response => response || fetch(e.request)));
});