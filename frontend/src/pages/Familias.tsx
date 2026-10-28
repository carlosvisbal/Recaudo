import { useEffect, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { api, ApiError, parsePage, type Familia, type Padrino, type Recaudo, type Totales } from "../api";
import { useConfirm } from "../components/ConfirmDialog";
import { FilterSelect } from "../components/FilterSelect";
import { Pager } from "../components/Pager";
import { RowActions } from "../components/RowActions";

export function Familias() {
  const [items, setItems] = useState<Familia[]>([]);
  const [padrinos, setPadrinos] = useState<Padrino[]>([]);
  const [padrino, setPadrino] = useState("");
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [count, setCount] = useState(0);
  const [error, setError] = useState("");

  const loadPadrinos = async (term = "") => {
    const params = new URLSearchParams({ estado: "activo", page: "1" });
    if (term.trim()) params.set("q", term.trim());
    const data = parsePage<Padrino>(await api(`/api/padrinos/?${params}`));
    setPadrinos(data.results);
  };

  const load = async (term = q, padrinoId = padrino, pagina = 1) => {
    const params = new URLSearchParams();
    params.set("page", String(pagina));
    if (term.trim()) params.set("q", term.trim());
    if (padrinoId) params.set("padrino", padrinoId);
    const data = parsePage<Familia>(await api(`/api/familias/?${params}`));
    setItems(data.results);
    setPages(data.pages);
    setCount(data.count);
    setPage(data.page);
  };

  useEffect(() => {
    void loadPadrinos();
    void load("", "", 1);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div>
      <div className="toolbar">
        <div>
          <h1>Familias</h1>
          <p className="muted">Lista paginada. Filtre por padrino para ver solo las suyas.</p>
        </div>
        <Link className="btn" to={padrino ? `/familias/nueva?padrino=${padrino}` : "/familias/nueva"}>
          Nueva familia
        </Link>
      </div>
      {error ? <div className="error">{error}</div> : null}
      <div className="filters">
        <FilterSelect
          label="Padrino"
          value={padrino}
          emptyLabel="Todos los padrinos"
          placeholder="Escriba para filtrar padrinos"
          options={padrinos.map((item) => ({
            value: item.id,
            label: item.nombre_completo,
            hint: typeof item.familias_activas === "number" ? `${item.familias_activas} familia(s)` : undefined,
          }))}
          onSearch={(term) => void loadPadrinos(term)}
          onChange={(value) => {
            setPadrino(value);
            void load(q, value, 1);
          }}
        />
        <label>
          Buscar familia
          <input
            placeholder="Nombre, contacto o celular"
            value={q}
            onChange={(e) => {
              setQ(e.target.value);
              void load(e.target.value, padrino, 1);
            }}
          />
        </label>
      </div>
      <div className="list">
        {items.map((item) => (
          <div className="list-item has-actions" key={item.id}>
            <Link className="list-item-main" to={`/familias/${item.id}`}>
              <strong>{item.nombre}</strong>
              <div className="muted">Padrino: {item.padrino_nombre}</div>
            </Link>
            <div className="list-item-meta">
              <span className={`badge ${item.estado}`}>{item.estado}</span>
              <RowActions
                editTo={`/familias/${item.id}`}
                confirmText={`¿Eliminar a ${item.nombre}? Los pagos quedan, sin familia asignada.`}
                onDelete={async () => {
                  setError("");
                  try {
                    await api(`/api/familias/${item.id}/`, { method: "DELETE" });
                    await load(q, padrino, page);
                  } catch (err) {
                    setError(err instanceof ApiError ? err.message : "No se pudo eliminar la familia.");
                  }
                }}
              />
            </div>
          </div>
        ))}
        {!items.length ? (
          <p className="muted">
            {padrino
              ? "Este padrino no tiene familias con ese criterio."
              : "No hay familias. Cree la primera y asígnela a un padrino."}
          </p>
        ) : null}
      </div>
      <Pager page={page} pages={pages} count={count} label="familias" onChange={(p) => void load(q, padrino, p)} />
    </div>
  );
}

type Historial = {
  id: string;
  padrino_anterior_nombre: string | null;
  padrino_nuevo_nombre: string;
  motivo: string;
  cambiado_en: string;
};

export function FamiliaForm() {
  const { ask, dialog } = useConfirm();
  const { id } = useParams();
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const [padrinos, setPadrinos] = useState<Padrino[]>([]);
  const [historial, setHistorial] = useState<Historial[]>([]);
  const [item, setItem] = useState<Partial<Familia>>({
    nombre: "",
    contacto_principal: "",
    telefono: "",
    correo: "",
    observaciones: "",
    padrino: params.get("padrino") || "",
  });
  const [motivo, setMotivo] = useState("");
  const [error, setError] = useState("");
  const [pagos, setPagos] = useState<Recaudo[]>([]);
  const [totales, setTotales] = useState<Totales | null>(null);
  const [paginaPago, setPaginaPago] = useState(1);
  const [pagesPago, setPagesPago] = useState(1);
  const [countPago, setCountPago] = useState(0);

  const loadPagos = async (pagina = 1) => {
    if (!id) return;
    const data = await api<{ resultados: Recaudo[]; totales: Totales }>(`/api/recaudos/?familia=${id}&page=${pagina}`);
    const page = parsePage<Recaudo>(data);
    setPagos(page.results);
    setPagesPago(page.pages);
    setCountPago(page.count);
    setPaginaPago(page.page);
    setTotales(data.totales);
  };

  const loadPadrinosForm = async (term = "") => {
    const params = new URLSearchParams({ estado: "activo", page: "1" });
    if (term.trim()) params.set("q", term.trim());
    setPadrinos(parsePage<Padrino>(await api(`/api/padrinos/?${params}`)).results);
  };

  useEffect(() => {
    void loadPadrinosForm();
    if (!id) return;
    void api<Familia>(`/api/familias/${id}/`).then(setItem);
    void api<Historial[]>(`/api/familias/${id}/historial/`).then(setHistorial);
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
            await api(`/api/familias/${id}/`, {
              method: "PUT",
              body: JSON.stringify({ ...item, motivo }),
            });
          } else {
            await api("/api/familias/", { method: "POST", body: JSON.stringify(item) });
          }
          navigate("/familias");
        } catch (err) {
          setError(err instanceof ApiError ? err.message : "No se pudo guardar.");
        }
      }}
    >
      <h2>{id ? "Datos de la familia" : "Nueva familia"}</h2>
      {error ? <div className="error">{error}</div> : null}
      <div className="form-grid">
        <label className="span-2">
          Nombre o identificación
          <input required value={item.nombre || ""} onChange={(e) => setItem({ ...item, nombre: e.target.value })} />
        </label>
        <label>
          Contacto principal (opcional)
          <input
            value={item.contacto_principal || ""}
            onChange={(e) => setItem({ ...item, contacto_principal: e.target.value })}
          />
        </label>
        <label>
          Celular para WhatsApp
          <input
            inputMode="tel"
            placeholder="3001234567"
            value={item.telefono || ""}
            onChange={(e) => setItem({ ...item, telefono: e.target.value })}
          />
        </label>
        <label>
          Correo (opcional)
          <input type="email" value={item.correo || ""} onChange={(e) => setItem({ ...item, correo: e.target.value })} />
        </label>
        <FilterSelect
          label="Padrino asignado"
          required
          value={item.padrino || ""}
          emptyLabel="Seleccione el padrino"
          placeholder="Escriba para filtrar padrinos"
          options={[
            item.padrino && !padrinos.some((p) => p.id === item.padrino)
              ? { value: item.padrino, label: item.padrino_nombre || "Padrino asignado" }
              : null,
            ...padrinos.map((p) => ({ value: p.id, label: p.nombre_completo, hint: p.telefono })),
          ].filter((opt): opt is { value: string; label: string; hint?: string } => Boolean(opt))}
          onSearch={(term) => void loadPadrinosForm(term)}
          onChange={(value) => setItem({ ...item, padrino: value })}
        />
        {id ? (
          <label className="span-2">
            Motivo de reasignación (si cambia el padrino)
            <input value={motivo} onChange={(e) => setMotivo(e.target.value)} />
          </label>
        ) : null}
        <label className="span-2">
          Observaciones
          <textarea value={item.observaciones || ""} onChange={(e) => setItem({ ...item, observaciones: e.target.value })} />
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
                title: "Desactivar familia",
                message: `¿Desactivar a ${item.nombre || "esta familia"}? No podrá registrar pagos nuevos a su nombre.`,
                confirmLabel: "Sí, desactivar",
                action: async () => {
                  await api(`/api/familias/${id}/desactivar/`, { method: "POST" });
                  navigate("/familias");
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
                title: "Activar familia",
                message: `¿Volver a activar a ${item.nombre || "esta familia"}?`,
                confirmLabel: "Sí, activar",
                action: async () => {
                  await api(`/api/familias/${id}/activar/`, { method: "POST" });
                  navigate("/familias");
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
                title: "Eliminar familia",
                message: `¿Eliminar a ${item.nombre || "esta familia"}? Los pagos quedan, sin familia asignada.`,
                confirmLabel: "Sí, eliminar",
                danger: true,
                action: async () => {
                  try {
                    await api(`/api/familias/${id}/`, { method: "DELETE" });
                    navigate("/familias");
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
        <div className="eyebrow">Familia</div>
        <h1>{id ? item.nombre || "Familia" : "Nueva familia"}</h1>
        <p className="muted">Cada familia pertenece a un solo padrino. El celular se usa para el recibo de caja.</p>
      </div>
      {id ? (
        <div className="card">
          <div className="muted">Total pagado por esta familia</div>
          <div className="kpi">{totales?.total_confirmado_formato || "$0"}</div>
          <div className="actions" style={{ marginTop: 12 }}>
            <Link
              className="btn gold"
              to={`/recaudos/nuevo?familia=${id}${item.padrino ? `&padrino=${item.padrino}` : ""}`}
            >
              Registrar un pago
            </Link>
          </div>
        </div>
      ) : null}
      {form}
      {id ? (
        <section>
          <h2>Pagos de esta familia</h2>
          <div className="list">
            {pagos.map((p) => (
              <Link className="list-item" key={p.id} to={`/recaudos/${p.id}`}>
                <div>
                  <strong>{p.actividad_nombre}</strong>
                  <div className="muted">Recibo {p.numero_formateado}</div>
                </div>
                <div>{p.valor_formato}</div>
              </Link>
            ))}
            {!pagos.length ? <p className="muted">Aún no registra pagos de esta familia.</p> : null}
          </div>
          <Pager page={paginaPago} pages={pagesPago} count={countPago} label="pagos" onChange={(p) => void loadPagos(p)} />
        </section>
      ) : null}
      {historial.length ? (
        <section>
          <h2>Historial de asignación</h2>
          <div className="list">
            {historial.map((h) => (
              <div className="list-item" key={h.id}>
                <div>
                  {h.padrino_anterior_nombre || "—"} → {h.padrino_nuevo_nombre}
                  <div className="muted">{h.motivo || "Sin motivo"}</div>
                </div>
                <div className="muted">{new Date(h.cambiado_en).toLocaleString("es-CO")}</div>
              </div>
            ))}
          </div>
        </section>
      ) : null}
      {dialog}
    </div>
  );
}
