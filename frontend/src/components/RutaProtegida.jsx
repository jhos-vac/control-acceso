import React from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";

export default function RutaProtegida({ children }) {
  const { isAuthenticated, usuario } = useAuth();
  const location = useLocation();

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // Primer ingreso (o después de un reseteo de contraseña por un
  // ADMIN): no se puede usar el resto del panel hasta elegir una
  // contraseña propia. No aplica si ya está yendo justo a esa pantalla
  // (si no, sería un redirect infinito).
  if (usuario?.debe_cambiar_password && location.pathname !== "/cambiar-password") {
    return <Navigate to="/cambiar-password" replace />;
  }

  return children;
}
