import { createContext, useContext, useEffect, useState } from "react";
import { api, logoutRequest, refreshSession, tokens } from "./api";

const AuthContext = createContext(null);
export const useAuth = () => useContext(AuthContext);

export function AuthProvider({ children }) {
  // The user lives in memory only. On load we try to restore the session
  // silently from the HttpOnly refresh cookie.
  const [user, setUser] = useState(null);
  const [booting, setBooting] = useState(true);

  useEffect(() => {
    let alive = true;
    (async () => {
      const restored = tokens.mayHaveSession ? await refreshSession() : null;
      if (alive) {
        setUser(restored);
        setBooting(false);
      }
    })();
    return () => {
      alive = false;
    };
  }, []);

  useEffect(() => {
    const onLogout = () => setUser(null);
    window.addEventListener("auth:logout", onLogout);
    return () => window.removeEventListener("auth:logout", onLogout);
  }, []);

  const login = async (email, password) => {
    const data = await api.post("/auth/login/", { email, password }, { auth: false });
    tokens.set(data.access);
    setUser(data.user);
  };

  // The server answers identically whether or not the email already exists
  // (so it can't be used to discover accounts). The user then logs in.
  const register = (name, email, password) =>
    api.post("/auth/register/", { name, email, password }, { auth: false });

  const logout = async () => {
    await logoutRequest(); // revokes the refresh token server-side + clears the cookie
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, booting, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
