// Lightweight API client for SocietyHub.
const API = (() => {
  const BASE = "/api";
  const TOKEN_KEY = "societyhub_token";
  const USER_KEY = "societyhub_user";

  function getToken() {
    return localStorage.getItem(TOKEN_KEY);
  }
  function setSession(token, user) {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    if (user) localStorage.setItem(USER_KEY, JSON.stringify(user));
  }
  function getUser() {
    const raw = localStorage.getItem(USER_KEY);
    return raw ? JSON.parse(raw) : null;
  }
  function clear() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  }

  async function request(method, path, body) {
    const headers = { "Content-Type": "application/json" };
    const token = getToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;

    const res = await fetch(BASE + path, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });

    if (res.status === 204) return null;

    let data = null;
    try {
      data = await res.json();
    } catch (_) {
      /* no body */
    }

    if (!res.ok) {
      const detail =
        data && data.detail
          ? Array.isArray(data.detail)
            ? data.detail.map((d) => d.msg).join(", ")
            : data.detail
          : `Request failed (${res.status})`;
      if (res.status === 401) {
        clear();
      }
      throw new Error(detail);
    }
    return data;
  }

  return {
    getToken,
    getUser,
    setSession,
    clear,
    get: (p) => request("GET", p),
    post: (p, b) => request("POST", p, b),
    put: (p, b) => request("PUT", p, b),
    patch: (p, b) => request("PATCH", p, b),
    del: (p) => request("DELETE", p),
  };
})();
