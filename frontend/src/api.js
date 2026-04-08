// Tiny fetch wrapper.
// - Dev: requests go to /api/* and Vite proxies them to the backend (see vite.config.js).
// - Prod: set VITE_BACKEND_URL at build time (e.g. https://your-app.onrender.com)
//   and requests will hit that origin directly.

const BASE = import.meta.env.VITE_BACKEND_URL || "/api";

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  let data = null;
  try {
    data = await res.json();
  } catch {
    // non-JSON response
  }

  if (!res.ok) {
    const msg = data?.error || `Request failed with status ${res.status}`;
    throw new Error(msg);
  }
  return data;
}

export function trainBot(content) {
  return request("/train", {
    method: "POST",
    body: JSON.stringify({ content }),
  });
}

export function clearKnowledge() {
  return request("/train/clear", { method: "DELETE" });
}

export function getStats() {
  return request("/train/stats", { method: "GET" });
}

export function sendChat(message, history = []) {
  return request("/chat", {
    method: "POST",
    body: JSON.stringify({ message, history }),
  });
}
