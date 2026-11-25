const BASE = import.meta.env.VITE_API_URL || "/api";

// --- tiny event bus so the UI can show every request (see ApiLog) ---
const listeners = new Set();
export const onLog = (fn) => {
  listeners.add(fn);
  return () => listeners.delete(fn);
};
const emit = (entry) => listeners.forEach((fn) => fn(entry));

// --- token handling -----------------------------------------------------
// The ACCESS token lives only in memory (a page reload drops it; it is then
// re-obtained from the refresh cookie). The REFRESH token is an HttpOnly cookie
// set by the server, so JavaScript - and therefore any XSS - can never read it.
let accessToken = null;
const SESSION_HINT = "has_session"; // non-sensitive flag: "worth trying a silent refresh"

export const tokens = {
  get access() {
    return accessToken;
  },
  set(access) {
    accessToken = access;
    try { localStorage.setItem(SESSION_HINT, "1"); } catch { /* storage blocked */ }
  },
  clear() {
    accessToken = null;
    try {
      localStorage.removeItem(SESSION_HINT);
      // leftovers from older versions that stored tokens in localStorage
      ["access", "refresh", "user"].forEach((k) => localStorage.removeItem(k));
    } catch { /* storage blocked */ }
  },
  get mayHaveSession() {
    try { return localStorage.getItem(SESSION_HINT) === "1"; } catch { return true; }
  },
};

export class ApiError extends Error {
  constructor(status, data) {
    super(formatError(data));
    this.status = status;
    this.data = data;
  }
}

// Turn DRF error payloads into one readable line
function formatError(data) {
  if (!data) return "Request failed.";
  if (typeof data === "string") return data;
  if (data.detail) return data.detail;
  return Object.entries(data)
    .map(([key, val]) => {
      const msg = Array.isArray(val)
        ? val.join(" ")
        : typeof val === "object"
        ? formatError(val)
        : String(val);
      return key === "non_field_errors" ? msg : `${key}: ${msg}`;
    })
    .join(" | ");
}

// Ask the server for a new access token using the refresh cookie.
// Refresh tokens are single-use (rotated + blacklisted), so concurrent callers
// MUST share one in-flight request - a second parallel call would be rejected.
let refreshing = null;
export function refreshSession() {
  if (!refreshing) {
    refreshing = (async () => {
      try {
        const res = await fetch(`${BASE}/auth/token/refresh/`, {
          method: "POST",
          credentials: "include",
        });
        if (!res.ok) {
          tokens.clear();
          return null;
        }
        const data = await res.json();
        tokens.set(data.access);
        return data.user;
      } catch {
        return null; // network error: keep the hint, the user may just be offline
      } finally {
        refreshing = null;
      }
    })();
  }
  return refreshing;
}

export async function logoutRequest() {
  try {
    await fetch(`${BASE}/auth/logout/`, { method: "POST", credentials: "include" });
  } catch { /* offline: cookie will expire; token also expires server-side */ }
  tokens.clear();
}

async function request(method, path, body, { auth = true, retry = true } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (auth && tokens.access) headers.Authorization = `Bearer ${tokens.access}`;

  let res;
  try {
    res = await fetch(`${BASE}${path}`, {
      method,
      headers,
      credentials: "include", // send/receive the HttpOnly refresh cookie
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch {
    emit({ method, path, status: 0 });
    throw new ApiError(0, "Cannot reach the server. Is the Django backend running?");
  }

  // Access token missing/expired: get a new one from the refresh cookie, replay once
  if (res.status === 401 && auth && retry && (await refreshSession())) {
    return request(method, path, body, { auth, retry: false });
  }

  emit({ method, path, status: res.status });
  if (res.status === 204) return null;

  const data = await res.json().catch(() => null);
  if (!res.ok) {
    if (res.status === 401 && auth) {
      tokens.clear();
      window.dispatchEvent(new Event("auth:logout"));
    }
    throw new ApiError(res.status, data);
  }
  return data;
}

// Fetch every page of a paginated list (for dropdowns that need all rows).
async function getAll(path) {
  const sep = path.includes("?") ? "&" : "?";
  const items = [];
  for (let page = 1; ; page++) {
    const data = await request("GET", `${path}${sep}page_size=100&page=${page}`);
    items.push(...data.results);
    if (!data.next) return items;
  }
}

export const api = {
  get: (path) => request("GET", path),
  getAll,
  post: (path, body, opts) => request("POST", path, body, opts),
  put: (path, body) => request("PUT", path, body),
  del: (path) => request("DELETE", path),
};
