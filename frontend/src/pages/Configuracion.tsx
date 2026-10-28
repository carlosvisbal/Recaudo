import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, ApiError } from "../api";
import { useAuth } from "../auth";

type Org = { nombre: string; nit: string; ciudad: string; telefono: string; correo: string };

export function Configuracion() {
  const { refresh, smtp } = useAuth();
  const [org, setOrg] = useState<Org>({ nombre: "", nit: "", ciudad: "", telefono: "", correo: "" });
  const [mensaje, setMensaje] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    void api<Org>("/api/organizacion/").then(setOrg);
  }, []);

  return (
    <div className="form form-wide">
      <div>
        <h1>Configuración</h1>
        <p className="muted">Un único administrador autenticado. Los padrinos no tienen cuenta de usuario.</p>
      </div>
      {mensaje ? <div className="note">{mensaje}</div> : null}
      <form
        className="form-card"
        onSubmit={async (event) => {
          event.preventDefault();
          setError("");
          try {
            await api("/api/organizacion/", { method: "PUT", body: JSON.stringify(org) });
            await refresh();
            setMensaje("Nombre de la organización actualizado. Los nuevos recibos usarán este nombre.");
          } catch (err) {
            setError(err instanceof ApiError ? err.message : "No se pudo guardar.");
          }
        }}
      >
        <h2>Datos impresos en el recibo</h2>
        {error ? <div className="error">{error}</div> : null}
        <div className="form-grid">
          <label className="span-2">
            Nombre de la organización
            <input required value={org.nombre} onChange={(e) => setOrg({ ...org, nombre: e.target.value })} />
          </label>
          <label>
            NIT (opcional)
            <input value={org.nit} onChange={(e) => setOrg({ ...org, nit: e.target.value })} />
          </label>
          <label>
            Ciudad
            <input value={org.ciudad} onChange={(e) => setOrg({ ...org, ciudad: e.target.value })} />
          </label>
          <label>
            Teléfono
            <input value={org.telefono} onChange={(e) => setOrg({ ...org, telefono: e.target.value })} />
          </label>
          <label>
            Correo
            <input type="email" value={org.correo} onChange={(e) => setOrg({ ...org, correo: e.target.value })} />
          </label>
        </div>
        <button className="btn">Guardar</button>
      </form>
      <div className="card">
        <strong>Correo saliente</strong>
        <p className="muted">
          {smtp
            ? "SMTP configurado. El envío directo de recibos queda registrado."
            : "SMTP no configurado. Se abrirá el cliente de correo del dispositivo y deberá adjuntar el PDF descargado."}
        </p>
      </div>
      <div className="card">
        <strong>Catálogos</strong>
        <p>
          <Link to="/padrinos">Padrinos</Link> · <Link to="/familias">Familias</Link> ·{" "}
          <Link to="/actividades">Actividades</Link>
        </p>
      </div>
    </div>
  );
}
