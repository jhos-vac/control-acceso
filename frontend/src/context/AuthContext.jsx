import React, { createContext, useContext, useEffect, useState } from "react";
import api from "../api/client.js";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [usuario, setUsuario] = useState(() => {
    const raw = localStorage.getItem("usuario");
    return raw ? JSON.parse(raw) : null;
  });
  const [token, setToken] = useState(() => localStorage.getItem("token"));
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    const handleExpired = () => {
      setToken(null);
      setUsuario(null);
    };
    window.addEventListener("auth:expired", handleExpired);
    return () => window.removeEventListener("auth:expired", handleExpired);
  }, []);

  async function login(usuarioLogin, password) {
    setCargando(true);
    setError(null);
    try {
      const { data } = await api.post("/api/login", {
        usuario: usuarioLogin,
        password,
      });
      localStorage.setItem("token", data.access_token);
      localStorage.setItem("usuario", JSON.stringify(data.usuario));
      setToken(data.access_token);
      setUsuario(data.usuario);
      return true;
    } catch (err) {
      const detalle =
        err?.response?.data?.detail || "No se pudo iniciar sesión. Intenta de nuevo.";
      setError(detalle);
      return false;
    } finally {
      setCargando(false);
    }
  }

  function logout() {
    localStorage.removeItem("token");
    localStorage.removeItem("usuario");
    setToken(null);
    setUsuario(null);
  }

  // Mezcla campos nuevos sobre el usuario guardado (ej. después de
  // cambiar la contraseña, para apagar `debe_cambiar_password` sin
  // tener que volver a loguearse) y lo persiste.
  function actualizarUsuario(cambios) {
    setUsuario((actual) => {
      const nuevo = { ...actual, ...cambios };
      localStorage.setItem("usuario", JSON.stringify(nuevo));
      return nuevo;
    });
  }

  async function cambiarPassword(passwordActual, passwordNueva) {
    await api.post("/api/usuarios/me/password", {
      password_actual: passwordActual,
      password_nueva: passwordNueva,
    });
    actualizarUsuario({ debe_cambiar_password: false });
  }

  const value = {
    usuario,
    token,
    isAuthenticated: Boolean(token),
    cargando,
    error,
    login,
    logout,
    cambiarPassword,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth debe usarse dentro de <AuthProvider>");
  }
  return ctx;
}
