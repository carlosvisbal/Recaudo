import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth";
import { Layout } from "./components/Layout";
import { ActividadForm, Actividades } from "./pages/Actividades";
import { Configuracion } from "./pages/Configuracion";
import { Consultas } from "./pages/Consultas";
import { FamiliaForm, Familias } from "./pages/Familias";
import { Inicio } from "./pages/Inicio";
import { Login } from "./pages/Login";
import { PadrinoForm, Padrinos } from "./pages/Padrinos";
import { Pagos } from "./pages/Pagos";
import { RecaudoDetalle } from "./pages/RecaudoDetalle";
import { RecaudoEditar, RecaudoNuevo } from "./pages/RecaudoNuevo";

function Private({ children }: { children: React.ReactNode }) {
  const { usuario, loading } = useAuth();
  if (loading) return <p style={{ padding: 24 }}>Cargando…</p>;
  if (!usuario) return <Navigate to="/login" replace />;
  return children;
}

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/"
        element={
          <Private>
            <Layout />
          </Private>
        }
      >
        <Route index element={<Inicio />} />
        <Route path="padrinos" element={<Padrinos />} />
        <Route path="padrinos/nuevo" element={<PadrinoForm />} />
        <Route path="padrinos/:id" element={<PadrinoForm />} />
        <Route path="familias" element={<Familias />} />
        <Route path="familias/nueva" element={<FamiliaForm />} />
        <Route path="familias/:id" element={<FamiliaForm />} />
        <Route path="actividades" element={<Actividades />} />
        <Route path="actividades/nueva" element={<ActividadForm />} />
        <Route path="actividades/:id" element={<ActividadForm />} />
        <Route path="pagos" element={<Pagos />} />
        <Route path="recaudos/nuevo" element={<RecaudoNuevo />} />
        <Route path="recaudos/:id/editar" element={<RecaudoEditar />} />
        <Route path="recaudos/:id" element={<RecaudoDetalle />} />
        <Route path="consultas" element={<Consultas />} />
        <Route path="configuracion" element={<Configuracion />} />
      </Route>
    </Routes>
  );
}
