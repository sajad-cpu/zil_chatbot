// Tiny fetch wrapper with JWT support.
// - Dev: requests go to /api/* and Vite proxies them to the backend (see vite.config.js).
// - Prod: set VITE_BACKEND_URL at build time (e.g. https://your-app.onrender.com)
//   and requests will hit that origin directly.

const BASE = import.meta.env.VITE_BACKEND_URL || "/api";

async function request(path, options = {}) {
  const headers = { "Content-Type": "application/json", ...options.headers };

  // Attach JWT if available
  const token = localStorage.getItem("auth_token");
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const res = await fetch(`${BASE}${path}`, {
    ...options,
    headers,
  });

  let data = null;
  try {
    data = await res.json();
  } catch {
    // non-JSON response
  }

  // 401 → token expired or invalid, clear and reload
  if (res.status === 401) {
    localStorage.removeItem("auth_token");
    window.location.reload();
    return;
  }

  if (!res.ok) {
    const msg = data?.detail || data?.error || `Request failed with status ${res.status}`;
    throw new Error(msg);
  }
  return data;
}

// Auth endpoints
export function signup(email, password) {
  return request("/auth/signup", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export function login(email, password) {
  return request("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export function getCurrentUser() {
  return request("/auth/me", { method: "GET" });
}

// Conversation endpoints
export function listConversations() {
  return request("/conversations", { method: "GET" });
}

export function createConversation(title = "New Chat") {
  return request("/conversations", {
    method: "POST",
    body: JSON.stringify({ title }),
  });
}

export function getConversation(conversationId) {
  return request(`/conversations/${conversationId}`, { method: "GET" });
}

export function deleteConversation(conversationId) {
  return request(`/conversations/${conversationId}`, { method: "DELETE" });
}

// Training endpoints
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

// Chat endpoint (requires conversation_id)
export function sendChat(message, conversationId, history = []) {
  return request("/chat", {
    method: "POST",
    body: JSON.stringify({ message, conversation_id: conversationId, history }),
  });
}
