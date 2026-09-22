import React from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import Login from "./pages/Login.jsx";
import DashboardLayout from "./layouts/DashboardLayout.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Registros from "./pages/Registros.jsx";
import Personas from "./pages/Personas.jsx";
import PuntosAcceso from "./pages/PuntosAcceso.jsx";
import Reportes from "./pages/Reportes.jsx";
import CambiarPassword from "./pages/CambiarPassword.jsx";
import RutaProtegida from "./components/RutaProtegida.jsx";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />

      <Route
        path="/cambiar-password"
        element={
          <RutaProtegida>
            <CambiarPassword />
          </RutaProtegida>
        }
      />

      <Route
        path="/"
        element={
          <RutaProtegida>
            <DashboardLayout />
          </RutaProtegida>
        }
      >
        <Route index element={<Dashboard />} />
        <Route path="registros" element={<Registros />} />
        <Route path="personas" element={<Personas />} />
        <Route path="puntos-acceso" element={<PuntosAcceso />} />
        <Route path="reportes" element={<Reportes />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
