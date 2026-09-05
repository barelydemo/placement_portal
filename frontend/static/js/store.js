/**
 * Shared auth state + API helper.
 *
 * The JWT is kept in localStorage so a refresh does not end the session: on
 * load the stored token is restored and validated against /api/auth/me, and it
 * is cleared whenever the server rejects it (expired, revoked or tampered).
 */
window.PPA = window.PPA || {};

(function () {
  const { reactive } = Vue;

  const TOKEN_KEY = "ppa.access_token";

  // localStorage can throw in private-browsing modes — never let that break the app.
  function readToken() {
    try {
      return window.localStorage.getItem(TOKEN_KEY);
    } catch (err) {
      return null;
    }
  }

  function persistToken(token) {
    try {
      if (token) window.localStorage.setItem(TOKEN_KEY, token);
      else window.localStorage.removeItem(TOKEN_KEY);
    } catch (err) {
      /* session simply won't survive a refresh */
    }
  }

  const state = reactive({
    token: readToken(),
    user: null,
    booting: true,
  });

  async function api(path, { method = "GET", body = null } = {}) {
    const headers = { Accept: "application/json" };
    if (body) headers["Content-Type"] = "application/json";
    if (state.token) headers["Authorization"] = `Bearer ${state.token}`;

    const response = await fetch(path, {
      method,
      headers,
      body: body ? JSON.stringify(body) : null,
    });

    let data = {};
    try {
      data = await response.json();
    } catch (err) {
      /* empty or non-JSON body */
    }

    if (!response.ok) {
      const error = new Error(data.error || `Request failed (${response.status}).`);
      error.status = response.status;
      error.field = data.field || null;
      throw error;
    }
    return data;
  }

  async function login(credentials) {
    const data = await api("/api/auth/login", { method: "POST", body: credentials });
    state.token = data.access_token;
    persistToken(state.token);
    state.user = data.user;
    return data.user;
  }

  async function register(payload) {
    return api("/api/auth/register", { method: "POST", body: payload });
  }

  /** Restore a stored session on load; drop the token if the server rejects it. */
  async function checkSession() {
    if (!state.token) {
      state.user = null;
      state.booting = false;
      return;
    }
    try {
      const data = await api("/api/auth/me");
      state.user = data.user;
    } catch (err) {
      state.token = null;
      persistToken(null);
      state.user = null;
    } finally {
      state.booting = false;
    }
  }

  async function logout() {
    try {
      if (state.token) await api("/api/auth/logout", { method: "POST" });
    } catch (err) {
      /* revoking is best-effort; the client drops the token regardless */
    }
    state.token = null;
    persistToken(null);
    state.user = null;
  }

  /** Landing route for a role — used for post-login redirects. */
  function homeFor(role) {
    return role ? `#/${role}` : "#/login";
  }

  window.PPA.store = { state, api, login, register, checkSession, logout, homeFor };
})();
