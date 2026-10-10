import { createContext, useContext, useEffect, useState } from "react";
import api from "@/lib/api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("th_token");
    if (!token) { setLoading(false); return; }
    api.get("/auth/me")
      .then((res) => setUser(res.data))
      .catch(() => { localStorage.removeItem("th_token"); })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!user) return;
    const id = setInterval(() => { if (!document.hidden) api.post("/users/me/ping").catch(() => {}); }, 60000);
    return () => clearInterval(id);
  }, [user]);

  const applyAuth = (data) => {
    localStorage.setItem("th_token", data.token);
    setUser(data.user);
  };

  const login = async (email, password) => {
    const res = await api.post("/auth/login", { email, password });
    applyAuth(res.data);
    return res.data.user;
  };

  const register = async (email, password, name) => {
    const res = await api.post("/auth/register", { email, password, name });
    applyAuth(res.data);
    return res.data.user;
  };

  const logout = () => {
    localStorage.removeItem("th_token");
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, setUser, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
