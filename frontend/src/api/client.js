const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const TOKEN_KEY = "studytime_token";

// Wraps fetch with the two things every authenticated call to the
// backend needs: the base URL, and (once logged in) the Authorization
// header. Nothing here is auth-page-specific - /health, /auth, and
// every future endpoint (documents, flashcards, ...) share this.
export async function apiFetch(path, options = {}) {
  const token = localStorage.getItem(TOKEN_KEY);

  // A FormData body (file uploads) needs the browser to set its own
  // Content-Type, including the multipart boundary string - setting
  // "application/json" here like every other call would make the
  // backend unable to parse the upload at all.
  const isFormData = options.body instanceof FormData;

  const headers = {
    ...(isFormData ? {} : { "Content-Type": "application/json" }),
    ...options.headers,
  };

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    // FastAPI's HTTPException responses look like { "detail": "..." } -
    // surface that message when it's there, fall back to the status
    // code when it's not (a network-level failure, or a non-JSON body).
    let detail = `Request failed: ${response.status}`;
    try {
      const body = await response.json();
      if (body?.detail) detail = body.detail;
    } catch {
      // response wasn't JSON - stick with the generic message above
    }
    throw new Error(detail);
  }

  if (response.status === 204) return null;
  return response.json();
}

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}
