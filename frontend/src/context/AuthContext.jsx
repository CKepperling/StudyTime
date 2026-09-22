import { useEffect, useState } from "react";
import * as authApi from "../api/auth";
import { clearToken, getToken, setToken } from "../api/client";
import { AuthContext } from "./authContext";

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);

  // Figure out synchronously, from localStorage, whether there's even
  // a token worth checking - "checking" only when there is one, so a
  // signed-out visitor never round-trips through a "checking" state at
  // all, and this component never calls setState synchronously inside
  // its effect below (only from the async .then/.catch).
  const [status, setStatus] = useState(() => (getToken() ? "checking" : "signed-out"));

  useEffect(() => {
    if (!getToken()) return;

    authApi
      .fetchCurrentUser()
      .then((currentUser) => {
        setUser(currentUser);
        setStatus("signed-in");
      })
      .catch(() => {
        // Token is expired, revoked, or otherwise invalid - drop it so
        // we're not sending a dead token on every request from here on.
        clearToken();
        setStatus("signed-out");
      });
  }, []);

  async function login(email, password) {
    const { access_token: accessToken } = await authApi.login(email, password);
    setToken(accessToken);
    const currentUser = await authApi.fetchCurrentUser();
    setUser(currentUser);
    setStatus("signed-in");
  }

  async function signup(email, password) {
    await authApi.signup(email, password);
    // /auth/signup doesn't log you in server-side - immediately log in
    // with the same credentials so signing up drops you straight into
    // the app instead of back at a login form.
    await login(email, password);
  }

  function logout() {
    clearToken();
    setUser(null);
    setStatus("signed-out");
  }

  return (
    <AuthContext.Provider value={{ user, status, login, signup, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
