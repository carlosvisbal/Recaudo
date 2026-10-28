import { useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../auth";
import {
  IconChart,
  IconFamily,
  IconFlag,
  IconGear,
  IconGrid,
  IconHome,
  IconMore,
  IconPeople,
  IconPlus,
} from "./Icons";

const links = [
  { to: "/", label: "Inicio", end: true, icon: IconHome },
  { to: "/recaudos/nuevo", label: "Registrar pago", icon: IconPlus },
  { to: "/pagos", label: "Pagos", icon: IconGrid },
  { to: "/consultas", label: "Informes", icon: IconChart },
  { to: "/padrinos", label: "Padrinos", icon: IconPeople },
  { to: "/familias", label: "Familias", icon: IconFamily },
  { to: "/actividades", label: "Actividades", icon: IconFlag },
  { to: "/configuracion", label: "Ajustes", icon: IconGear },
];

export function Layout() {
  const { usuario, organizacion, logout } = useAuth();
  const navigate = useNavigate();
  const [more, setMore] = useState(false);
  const inicial = (usuario?.nombre || "A").slice(0, 1).toUpperCase();

  async function salir() {
    setMore(false);
    await logout();
    navigate("/login");
  }

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark sm">R</span>
          <div>
            <div className="logo">Recaudo</div>
            <div className="brand-sub">{organizacion?.nombre}</div>
          </div>
        </div>
        <nav className="side-nav">
          {links.map((link) => (
            <NavLink key={link.to} to={link.to} end={link.end} className={({ isActive }) => (isActive ? "active" : "")}>
              <link.icon size={18} />
              {link.label}
            </NavLink>
          ))}
        </nav>
        <div className="spacer" />
        <div className="side-user">
          <span className="avatar">{inicial}</span>
          <div>
            <div className="side-user-name">{usuario?.nombre}</div>
            <button className="linkish" type="button" onClick={() => void salir()}>
              Cerrar sesión
            </button>
          </div>
        </div>
      </aside>

      <div className="shell">
        <header className="topbar">
          <div>
            <div className="topbar-kicker">Recaudo</div>
            <div className="topbar-title">{organizacion?.nombre}</div>
          </div>
          <span className="avatar">{inicial}</span>
        </header>
        <main className="main">
          <Outlet />
        </main>
      </div>

      <nav className="bottom-nav">
        <NavLink to="/" end>
          <IconHome />
          Inicio
        </NavLink>
        <NavLink to="/recaudos/nuevo" className="fab">
          <span className="fab-dot">
            <IconPlus size={22} />
          </span>
          Pago
        </NavLink>
        <NavLink to="/consultas">
          <IconChart />
          Informes
        </NavLink>
        <button type="button" className={more ? "active" : ""} onClick={() => setMore(true)}>
          <IconMore />
          Más
        </button>
      </nav>

      {more ? (
        <div className="sheet-backdrop" onClick={() => setMore(false)}>
          <div className="sheet" onClick={(e) => e.stopPropagation()}>
            <div className="sheet-handle" />
            <h2>Menú</h2>
            <div className="sheet-grid">
              <NavLink to="/padrinos" onClick={() => setMore(false)}>
                <IconPeople /> Padrinos
              </NavLink>
              <NavLink to="/familias" onClick={() => setMore(false)}>
                <IconFamily /> Familias
              </NavLink>
              <NavLink to="/actividades" onClick={() => setMore(false)}>
                <IconFlag /> Actividades
              </NavLink>
              <NavLink to="/pagos" onClick={() => setMore(false)}>
                <IconGrid /> Pagos
              </NavLink>
              <NavLink to="/configuracion" onClick={() => setMore(false)}>
                <IconGear /> Ajustes
              </NavLink>
              <NavLink to="/consultas" onClick={() => setMore(false)}>
                <IconGrid /> Informes
              </NavLink>
            </div>
            <button className="btn secondary block" type="button" onClick={() => void salir()}>
              Cerrar sesión
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
