import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, ApiError, cop, parsePage, type Actividad, type Recaudo, type Totales } from "../api";
import { useConfirm } from "../components/ConfirmDialog";
import { FilterSelect } from "../components/FilterSelect";
import { Pager } from "../components/Pager";
import { RowActions } from "../components/RowActions";

export function Actividades() {
  const [items, setItems] = useState<Actividad[]>([]);
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [count, setCount] = useState(0);
  const [error, setError] = useState("");

  const load = async (term = q, pagina = 1) => {
    const params = new URLSearchParams({ page: String(pagina) });
    if (term.trim()) params.set("q", term.trim());
    const data = parsePage<Actividad>(await api(`/api/actividades/?${params}`));
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
          <h1>Actividades</h1>
          <p className="muted">Lista paginada. Cada pago entra en la sumatoria de la actividad elegida.</p>
        </div>
        <Link className="btn" to="/actividades/nueva">
          Nueva actividad
        </Link>
      </div>
      {error ? <div className="error">{error}</div> : null}
      <label style={{ marginBottom: 16 }}>
        Filtrar actividades
        <input
          placeholder="Nombre de la actividad"
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
            <Link className="list-item-main" to={`/actividades/${item.id}`}>
              <strong>{item.nombre}</strong>
              <div className="muted">{item.cantidad_recaudos || 0} pagos · {cop(item.total_recaudado)}</div>
            </Link>
            <div className="list-item-meta">
              <span className={`badge ${item.estado}`}>{item.estado}</span>
              <RowActions
                editTo={`/actividades/${item.id}`}
                confirmText={`¿Eliminar ${item.nombre}? Se borran sus pagos, recibos y soportes.`}
                onDelete={async () => {
                  setError("");
                  try {
                    await api(`/api/actividades/${item.id}/`, { method: "DELETE" });
                    await load(q, page);
                  } catch (err) {
                    setError(err instanceof ApiError ? err.message : "No se pudo eliminar la actividad.");
                  }
                }}
              />
            </div>
          </div>
        ))}
        {!items.length ? <p className="muted">Cree la primera actividad.</p> : null}
      </div>
      <Pager page={page} pages={pages} count={count} label="actividades" onChange={(p) => void load(q, p)} />
    </div>
  );
}

export function ActividadForm() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { ask, dialog } = useConfirm();
  const [item, setItem] = useState<Partial<Actividad>>({
    nombre: "",
    descripcion: "",
    fecha_inicio: "",
    fecha_fin: "",
    estado: "activa",
  });
  const [pagos, setPagos] = useState<Recaudo[]>([]);
  const [totales, setTotales] = useState<Totales | null>(null);
  const [error, setError] = useState("");
  const [paginaPago, setPaginaPago] = useState(1);
  const [pagesPago, setPagesPago] = useState(1);
  const [countPago, setCountPago] = useState(0);

  const loadPagos = async (pagina = 1) => {
    if (!id) return;
    const data = await api<{ resultados: Recaudo[]; totales: Totales }>(`/api/recaudos/?actividad=${id}&page=${pagina}`);
    const page = parsePage<Recaudo>(data);
    setPagos(page.results);
    setPagesPago(page.pages);
    setCountPago(page.count);
    setPaginaPago(page.page);
    setTotales(data.totales);
  };

  useEffect(() => {
    if (!id) return;
    void api<Actividad>(`/api/actividades/${id}/`).then(setItem);
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
          if (id) await api(`/api/actividades/${id}/`, { method: "PUT", body: JSON.stringify(item) });
          else await api("/api/actividades/", { method: "POST", body: JSON.stringify(item) });
          navigate("/actividades");
        } catch (err) {
          setError(err instanceof ApiError ? err.message : "No se pudo guardar.");
        }
      }}
    >
      <h2>{id ? "Datos de la actividad" : "Nueva actividad"}</h2>
      {error ? <div className="error">{error}</div> : null}
      <div className="form-grid">
        <label className="span-2">
          Nombre
          <input required value={item.nombre || ""} onChange={(e) => setItem({ ...item, nombre: e.target.value })} />
        </label>
        <label className="span-2">
          Descripción
          <textarea value={item.descripcion || ""} onChange={(e) => setItem({ ...item, descripcion: e.target.value })} />
        </label>
        <label>
          Fecha inicial
          <input
            type="date"
            required
            value={item.fecha_inicio || ""}
            onChange={(e) => setItem({ ...item, fecha_inicio: e.target.value })}
          />
        </label>
        <label>
          Fecha final
          <input
            type="date"
            required
            value={item.fecha_fin || ""}
            onChange={(e) => setItem({ ...item, fecha_fin: e.target.value })}
          />
        </label>
        <FilterSelect
          className="span-2"
          label="Estado"
          value={item.estado || "activa"}
          options={[
            { value: "programada", label: "Programada" },
            { value: "activa", label: "Activa" },
            { value: "cerrada", label: "Cerrada" },
          ]}
          onChange={(value) => setItem({ ...item, estado: value as Actividad["estado"] })}
        />
      </div>
      <div className="actions">
        <button className="btn">Guardar datos</button>
        {id ? (
          <button
            type="button"
            className="btn danger"
            onClick={() =>
              ask({
                title: "Eliminar actividad",
                message: "¿Eliminar esta actividad? Se borran sus pagos, recibos y soportes para liberar espacio.",
                confirmLabel: "Sí, eliminar",
                danger: true,
                action: async () => {
                  try {
                    await api(`/api/actividades/${id}/`, { method: "DELETE" });
                    navigate("/actividades");
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

  if (!id) {
    return (
      <div className="form form-wide">
        <div>
          <div className="eyebrow">Actividad</div>
          <h1>Nueva actividad</h1>
          <p className="muted">Al registrar un pago se elige esta actividad: ahí queda la evidencia y la sumatoria.</p>
        </div>
        {form}
        {dialog}
      </div>
    );
  }

  return (
    <div>
      <div className="toolbar">
        <div>
          <div className="eyebrow">Sumatoria de la actividad</div>
          <h1>{item.nombre || "Actividad"}</h1>
        </div>
        <Link className="btn gold" to={`/recaudos/nuevo?actividad=${id}`}>
          Registrar pago
        </Link>
      </div>
      <div className="card">
        <div className="muted">Total de pagos confirmados</div>
        <div className="kpi">{totales?.total_confirmado_formato || cop(item.total_recaudado)}</div>
        <p className="muted">{totales?.cantidad_confirmados ?? 0} familias han pagado</p>
      </div>
      <h2 style={{ margin: "24px 0 12px" }}>Pagos</h2>
      <div className="list">
        {pagos.map((pago) => (
          <Link className="list-item" key={pago.id} to={`/recaudos/${pago.id}`}>
            <div>
              <strong>{pago.aportante_nombre}</strong>
              <div className="muted">
                {pago.padrino_nombre} · recibo {pago.numero_formateado}
                {pago.soportes_count ? ` · ${pago.soportes_count} soporte(s)` : ""}
              </div>
            </div>
            <div style={{ textAlign: "right" }}>
              <div>{pago.valor_formato}</div>
              <span className={`badge ${pago.estado}`}>{pago.estado_display}</span>
            </div>
          </Link>
        ))}
        {!pagos.length ? <p className="muted">Aún no hay pagos. Registre el primero para empezar a sumar.</p> : null}
      </div>
      <Pager page={paginaPago} pages={pagesPago} count={countPago} label="pagos" onChange={(p) => void loadPagos(p)} />
      <h2 style={{ margin: "24px 0 12px" }}>Datos de la actividad</h2>
      {form}
      {dialog}
    </div>
  );
}
