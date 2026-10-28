import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, ApiError, parsePage, type Familia, type Padrino, type Recaudo, type Totales } from "../api";
import { useConfirm } from "../components/ConfirmDialog";
import { Pager } from "../components/Pager";
import { RowActions } from "../components/RowActions";

export function Padrinos() {
  const [items, setItems] = useState<Padrino[]>([]);
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [count, setCount] = useState(0);
  const [error, setError] = useState("");

  const load = async (term = q, pagina = page) => {
    const params = new URLSearchParams();
    params.set("page", String(pagina));
    if (term.trim()) params.set("q", term.trim());
    const data = parsePage<Padrino>(await api(`/api/padrinos/?${params}`));
    setItems(data.results);
    setPages(data.pages);
    setCount(data.count);
    setPage(data.page);
  };

  useEffect(() => {
    void load("", 1);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div>
      <div className="toolbar">
        <div>
          <h1>Padrinos</h1>
          <p className="muted">Lista paginada. Filtre por nombre o teléfono.</p>
        </div>
        <Link className="btn" to="/padrinos/nuevo">
          Nuevo padrino
        </Link>
      </div>
      {error ? <div className="error">{error}</div> : null}
      <label style={{ marginBottom: 16 }}>
        Filtrar padrinos
        <input
          placeholder="Nombre, teléfono o correo"
          value={q}
          onChange={(e) => {
            setQ(e.target.value);
            void load(e.target.value, 1);
          }}
        />
      </label>
      <div className="list">
        {items.map((item) => (
          <div className="list-item has-actions" key={item.id}>
            <Link className="list-item-main" to={`/padrinos/${item.id}`}>
              <strong>{item.nombre_completo}</strong>
              <div className="muted">
                {item.telefono}
                {typeof item.familias_activas === "number" ? ` · ${item.familias_activas} familia(s)` : ""}
              </div>
            </Link>
            <div className="list-item-meta">
              <span className={`badge ${item.estado}`}>{item.estado}</span>
              <RowActions
                editTo={`/padrinos/${item.id}`}
                confirmText={`¿Eliminar a ${item.nombre_completo}? También se borran sus familias si no tiene pagos.`}
                onDelete={async () => {
                  setError("");
                  try {
                    await api(`/api/padrinos/${item.id}/`, { method: "DELETE" });
                    await load(q, page);
                  } catch (err) {
                    setError(err instanceof ApiError ? err.message : "No se pudo eliminar el padrino.");
                  }
                }}
              />
            </div>
          </div>
        ))}
        {!items.length ? <p className="muted">No hay padrinos con ese filtro.</p> : null}
      </div>
      <Pager page={page} pages={pages} count={count} label="padrinos" onChange={(p) => void load(q, p)} />
    </div>
  );
}

export function PadrinoForm() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { ask, dialog } = useConfirm();
  const [item, setItem] = useState<Partial<Padrino>>({
    nombre_completo: "",
    telefono: "",
    correo: "",
    estado: "activo",
  });
  const [error, setError] = useState("");
  const [familias, setFamilias] = useState<Familia[]>([]);
  const [filtroFamilia, setFiltroFamilia] = useState("");
  const [paginaFamilia, setPaginaFamilia] = useState(1);
  const [pagesFamilia, setPagesFamilia] = useState(1);
  const [countFamilia, setCountFamilia] = useState(0);
  const [totales, setTotales] = useState<Totales | null>(null);
  const [pagos, setPagos] = useState<Recaudo[]>([]);
  const [paginaPago, setPaginaPago] = useState(1);
  const [pagesPago, setPagesPago] = useState(1);
  const [countPago, setCountPago] = useState(0);
  const [nuevaFamilia, setNuevaFamilia] = useState({ nombre: "", telefono: "", contacto_principal: "" });
  const [guardandoFamilia, setGuardandoFamilia] = useState(false);
  const [errorFamilia, setErrorFamilia] = useState("");
  const [okFamilia, setOkFamilia] = useState("");

  const loadFamilias = async (term = filtroFamilia, pagina = 1) => {
    if (!id) return;
    const params = new URLSearchParams({ padrino: id, page: String(pagina) });
    if (term.trim()) params.set("q", term.trim());
    const data = parsePage<Familia>(await api(`/api/familias/?${params}`));
    setFamilias(data.results);
    setPagesFamilia(data.pages);
    setCountFamilia(data.count);
    setPaginaFamilia(data.page);
  };

  const loadPagos = async (pagina = 1) => {
    if (!id) return;
    const data = await api<{ resultados: Recaudo[]; totales: Totales } & Record<string, unknown>>(
      `/api/recaudos/?padrino=${id}&page=${pagina}`
    );
    const page = parsePage<Recaudo>(data);
    setPagos(page.results);
    setPagesPago(page.pages);
    setCountPago(page.count);
    setPaginaPago(page.page);
    setTotales(data.totales);
  };

  useEffect(() => {
    if (!id) return;
    void api<Padrino>(`/api/padrinos/${id}/`).then(setItem);
    void loadFamilias("", 1);
    void loadPagos(1);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const form = (
    <form
      className="form-card"
      onSubmit={async (event) => {
        event.preventDefault();
        setError("");
        try {
          if (id) {
            await api(`/api/padrinos/${id}/`, { method: "PUT", body: JSON.stringify(item) });
            navigate("/padrinos");
          } else {
            const creado = await api<Padrino>("/api/padrinos/", { method: "POST", body: JSON.stringify(item) });
            navigate(`/padrinos/${creado.id}`);
          }
        } catch (err) {
          setError(err instanceof ApiError ? err.message : "No se pudo guardar.");
        }
      }}
    >
      <h2>{id ? "Datos del padrino" : "Nuevo padrino"}</h2>
      {error ? <div className="error">{error}</div> : null}
      <div className="form-grid">
        <label className="span-2">
          Nombre completo
          <input
            required
            value={item.nombre_completo || ""}
            onChange={(e) => setItem({ ...item, nombre_completo: e.target.value })}
          />
        </label>
        <label>
          Teléfono
          <input required value={item.telefono || ""} onChange={(e) => setItem({ ...item, telefono: e.target.value })} />
        </label>
        <label>
          Correo electrónico (opcional)
          <input type="email" value={item.correo || ""} onChange={(e) => setItem({ ...item, correo: e.target.value })} />
        </label>
      </div>
      <div className="actions">
        <button className="btn">Guardar</button>
        {id && item.estado === "activo" ? (
          <button
            type="button"
            className="btn secondary"
            onClick={() =>
              ask({
                title: "Desactivar padrino",
                message: `¿Desactivar a ${item.nombre_completo || "este padrino"}? Dejará de aparecer en los registros nuevos.`,
                confirmLabel: "Sí, desactivar",
                action: async () => {
                  try {
                    await api(`/api/padrinos/${id}/desactivar/`, { method: "POST" });
                    navigate("/padrinos");
                  } catch (err) {
                    setError(err instanceof ApiError ? err.message : "No se pudo desactivar.");
                    throw err;
                  }
                },
              })
            }
          >
            Desactivar
          </button>
        ) : null}
        {id && item.estado === "inactivo" ? (
          <button
            type="button"
            className="btn secondary"
            onClick={() =>
              ask({
                title: "Activar padrino",
                message: `¿Volver a activar a ${item.nombre_completo || "este padrino"}?`,
                confirmLabel: "Sí, activar",
                action: async () => {
                  await api(`/api/padrinos/${id}/activar/`, { method: "POST" });
                  navigate("/padrinos");
                },
              })
            }
          >
            Activar
          </button>
        ) : null}
        {id ? (
          <button
            type="button"
            className="btn danger"
            onClick={() =>
              ask({
                title: "Eliminar padrino",
                message: `¿Eliminar a ${item.nombre_completo || "este padrino"}? También se borran sus familias si no tiene pagos.`,
                confirmLabel: "Sí, eliminar",
                danger: true,
                action: async () => {
                  try {
                    await api(`/api/padrinos/${id}/`, { method: "DELETE" });
                    navigate("/padrinos");
                  } catch (err) {
                    setError(err instanceof ApiError ? err.message : "No se pudo eliminar.");
                    throw err;
                  }
                },
              })
            }
          >
            Eliminar
          </button>
        ) : null}
      </div>
    </form>
  );

  return (
    <div className="form form-wide">
      <div>
        <div className="eyebrow">Padrino</div>
        <h1>{id ? item.nombre_completo || "Padrino" : "Nuevo padrino"}</h1>
        <p className="muted">
          {id
            ? "Agregue aquí las familias de este padrino. Las listas salen de 20 en 20."
            : "Guarde el padrino y enseguida podrá asignarle familias en esta misma ficha."}
        </p>
      </div>
      {id ? (
        <>
          <div className="card">
            <div className="muted">Sumatoria de este padrino</div>
            <div className="kpi">{totales?.total_confirmado_formato || "$0"}</div>
            <p className="muted">{totales?.cantidad_confirmados ?? 0} pagos recibidos</p>
            <div className="actions" style={{ marginTop: 12 }}>
              <Link className="btn gold" to={`/recaudos/nuevo?padrino=${id}`}>
                Registrar pago de una familia
              </Link>
            </div>
          </div>
          <section className="form-card">
            <div className="form-step">
              <span className="step-num">+</span>
              <div>
                <h2>Agregar familia a este padrino</h2>
                <p className="muted">Queda asignada de una vez. No sale a otro formulario.</p>
              </div>
            </div>
            {errorFamilia ? <div className="error">{errorFamilia}</div> : null}
            {okFamilia ? <div className="note">{okFamilia}</div> : null}
            <div className="form-grid">
              <label className="span-2">
                Nombre de la familia
                <input
                  value={nuevaFamilia.nombre}
                  onChange={(e) => setNuevaFamilia({ ...nuevaFamilia, nombre: e.target.value })}
                  placeholder="Apellido o identificación"
                />
              </label>
              <label>
                Contacto (opcional)
                <input
                  value={nuevaFamilia.contacto_principal}
                  onChange={(e) => setNuevaFamilia({ ...nuevaFamilia, contacto_principal: e.target.value })}
                />
              </label>
              <label>
                Celular WhatsApp (opcional)
                <input
                  inputMode="tel"
                  placeholder="3001234567"
                  value={nuevaFamilia.telefono}
                  onChange={(e) => setNuevaFamilia({ ...nuevaFamilia, telefono: e.target.value })}
                />
              </label>
            </div>
            <button
              type="button"
              className="btn"
              disabled={guardandoFamilia}
              onClick={async () => {
                setErrorFamilia("");
                setOkFamilia("");
                if (!nuevaFamilia.nombre.trim()) {
                  setErrorFamilia("Escriba el nombre de la familia.");
                  return;
                }
                setGuardandoFamilia(true);
                try {
                  const creada = await api<Familia>("/api/familias/", {
                    method: "POST",
                    body: JSON.stringify({
                      nombre: nuevaFamilia.nombre.trim(),
                      telefono: nuevaFamilia.telefono.trim(),
                      contacto_principal: nuevaFamilia.contacto_principal.trim(),
                      padrino: id,
                    }),
                  });
                  setNuevaFamilia({ nombre: "", telefono: "", contacto_principal: "" });
                  setOkFamilia(`${creada.nombre} quedó asignada a este padrino.`);
                  void loadFamilias(filtroFamilia, 1);
                } catch (err) {
                  setErrorFamilia(err instanceof ApiError ? err.message : "No se pudo agregar la familia.");
                } finally {
                  setGuardandoFamilia(false);
                }
              }}
            >
              {guardandoFamilia ? "Guardando…" : "Agregar familia"}
            </button>
          </section>
          <section>
            <h2>Familias asignadas</h2>
            <label>
              Filtrar familias de este padrino
              <input
                placeholder="Nombre o celular"
                value={filtroFamilia}
                onChange={(e) => {
                  setFiltroFamilia(e.target.value);
                  void loadFamilias(e.target.value, 1);
                }}
              />
            </label>
            <div className="list" style={{ marginTop: 12 }}>
              {familias.map((f) => (
                <Link className="list-item" key={f.id} to={`/familias/${f.id}`}>
                  <div>
                    <strong>{f.nombre}</strong>
                    <div className="muted">{f.telefono || "Sin celular para WhatsApp"}</div>
                  </div>
                  <span className={`badge ${f.estado}`}>{f.estado}</span>
                </Link>
              ))}
              {!familias.length ? (
                <p className="muted">Aún no tiene familias. Use el recuadro de arriba para agregar la primera.</p>
              ) : null}
            </div>
            <Pager
              page={paginaFamilia}
              pages={pagesFamilia}
              count={countFamilia}
              label="familias"
              onChange={(p) => void loadFamilias(filtroFamilia, p)}
            />
          </section>
          <section>
            <h2>Pagos</h2>
            <div className="list">
              {pagos.map((p) => (
                <Link className="list-item" key={p.id} to={`/recaudos/${p.id}`}>
                  <div>
                    <strong>{p.aportante_nombre}</strong>
                    <div className="muted">
                      Actividad: {p.actividad_nombre} · recibo {p.numero_formateado}
                    </div>
                  </div>
                  <div>{p.valor_formato}</div>
                </Link>
              ))}
              {!pagos.length ? <p className="muted">Aún no hay pagos de este padrino.</p> : null}
            </div>
            <Pager page={paginaPago} pages={pagesPago} count={countPago} label="pagos" onChange={(p) => void loadPagos(p)} />
          </section>
        </>
      ) : null}
      {form}
      {dialog}
    </div>
  );
}
