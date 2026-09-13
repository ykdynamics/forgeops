// Service worker for the ForgeOps Approval PWA.
//
// Normal production builds keep the installable PWA behavior. The first-touch
// evaluator build does not register this worker at all: its approval surface
// must be deterministic across repeated local runs.
const CACHE = "forgeops-approval-shell-v2";
const SHELL = ["/index.html", "/manifest.webmanifest", "/icons/icon.svg"];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE).then((cache) => cache.addAll(SHELL)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") return;
  const url = new URL(event.request.url);

  // Approval and Automation Center data are live authority state. They must
  // never be fulfilled from a service-worker cache.
  if (url.pathname.startsWith("/api/") || url.pathname.startsWith("/v1/")) return;

  // Navigations are network-first so a new deployment cannot be held behind an
  // old cached shell that references asset hashes no longer present on disk.
  if (event.request.mode === "navigate") {
    event.respondWith(
      fetch(event.request)
        .then((res) => {
          if (res.ok) {
            const copy = res.clone();
            caches.open(CACHE).then((cache) => cache.put("/index.html", copy)).catch(() => {});
          }
          return res;
        })
        .catch(() => caches.match("/index.html"))
    );
    return;
  }

  // Hashed static assets are safe cache-first. Failed asset requests are not
  // replaced with index.html: returning HTML for a JS module creates the opaque
  // MIME-type failure that hides the real missing-asset problem.
  event.respondWith(
    caches.match(event.request).then((hit) => {
      if (hit) return hit;
      return fetch(event.request).then((res) => {
        if (res.ok) {
          const copy = res.clone();
          caches.open(CACHE).then((cache) => cache.put(event.request, copy)).catch(() => {});
        }
        return res;
      });
    })
  );
});

self.addEventListener("push", (event) => {
  const payload = event.data ? event.data.json() : {};
  const title = payload.title || "New ForgeOps proposal awaiting approval";
  const options = {
    body: payload.body || "Open Approvals to review.",
    icon: "/icons/icon.svg",
    badge: "/icons/icon.svg",
    data: payload,
  };
  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const target = (event.notification.data && event.notification.data.url) || "/";
  event.waitUntil(self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((list) => {
    for (const client of list) {
      if ("focus" in client) return client.navigate(target).then((c) => c && c.focus());
    }
    return self.clients.openWindow(target);
  }));
});
