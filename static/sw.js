// Service Worker para PWA smarttradetecnologies-ar
// IMPORTANTE: Incrementar versión cada vez que haya cambios en archivos HTML/JS/CSS
const CACHE_NAME = 'stc-ar-v3-admin-crud';
const CACHE_URLS = [
  '/',
  '/static/manifest.json',
  '/static/demo/candlestick.html',
  '/auth/login',
  '/trading-charts',
  '/admin/users',
  '/static/venezuela-flag.jpg',
  '/static/icons/icon-192x192.png',
  '/static/icons/icon-512x512.png',
  'https://unpkg.com/lightweight-charts@4.1.1/dist/lightweight-charts.standalone.production.js',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css'
];

// Instalar Service Worker y cachear recursos
self.addEventListener('install', (event) => {
  console.log('🔧 Service Worker: Instalando...');
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => {
        console.log('✅ Service Worker: Recursos cacheados');
        return cache.addAll(CACHE_URLS);
      })
      .catch((error) => {
        console.error('❌ Service Worker: Error al cachear:', error);
      })
  );
  self.skipWaiting();
});

// Activar Service Worker y limpiar cachés antiguos
self.addEventListener('activate', (event) => {
  console.log('⚡ Service Worker: Activando...');
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== CACHE_NAME) {
            console.log('🗑️ Service Worker: Eliminando caché antiguo:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
  return self.clients.claim();
});

// Estrategia: Network First con Fallback a Cache
self.addEventListener('fetch', (event) => {
  // Solo cachear GET requests
  if (event.request.method !== 'GET') {
    return;
  }

  // Para APIs de datos en tiempo real, siempre ir a la red
  if (event.request.url.includes('/api/')) {
    event.respondWith(
      fetch(event.request).catch(() => {
        return new Response(JSON.stringify({ error: 'Sin conexión' }), {
          headers: { 'Content-Type': 'application/json' }
        });
      })
    );
    return;
  }

  // Para recursos estáticos: Network First, luego Cache
  event.respondWith(
    fetch(event.request)
      .then((response) => {
        // Clonar la respuesta para guardarla en caché
        const responseToCache = response.clone();
        caches.open(CACHE_NAME).then((cache) => {
          cache.put(event.request, responseToCache);
        });
        return response;
      })
      .catch(() => {
        // Si falla la red, buscar en caché
        return caches.match(event.request).then((response) => {
          if (response) {
            return response;
          }
          // Si no está en caché, mostrar página offline básica
          return new Response('Offline - Sin conexión', {
            headers: { 'Content-Type': 'text/html' }
          });
        });
      })
  );
});

// Mensajes desde el cliente
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});
