import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, ApiError, parsePage, type Actividad, type Padrino, type Recaudo } from "../api";
import { FilterSelect } from "../components/FilterSelect";
import { Pager } from "../components/Pager";
import { RowActions } from "../components/RowActions";

export function Pagos() {
  const [items, setItems] = useState<Recaudo[]>([]);
  const [actividades, setActividades] = useState<Actividad[]>([]);
  const [padrinos, setPadrinos] = useState<Padrino[]>([]);
  const [actividad, setActividad] = useState("");
  const [padrino, setPadrino] = useState("");
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [count, setCount] = useState(0);
  const [error, setError] = useState("");

  const loadFiltros = async (term = "") => {
    const params = new URLSearchParams({ page: "1" });
    if (term.trim()) params.set("q", term.trim());
    const [acts, pads] = await Promise.all([
      api(`/api/actividades/?${params}`),
      api(`/api/padrinos/?${params}`),
    ]);
    setActividades(parsePage<Actividad>(acts).results);
    setPadrinos(parsePage<Padrino>(pads).results);
  };

  const load = async (pagina = 1, actividadId = actividad, padrinoId = padrino, term = q) => {
    const params = new URLSearchParams({ page: String(pagina) });
    if (actividadId) params.set("actividad", actividadId);
    if (padrinoId) params.set("padrino", padrinoId);
    if (term.trim()) params.set("q", term.trim());
    const data = parsePage<Recaudo>(await api(`/api/recaudos/?${params}`));
    setItems(data.results);
    setPages(data.pages);
    setCount(data.count);
    setPage(data.page);
  };

  useEffect(() => {
    void loadFiltros();
    void load(1, "", "", "");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div>
      <div className="toolbar">
        <div>
          <h1>Pagos</h1>
          <p className="muted">Alta, consulta, edición y baja de cada recaudo. Eliminar borra el PDF y los soportes.</p>
        </div>
        <Link className="btn gold" to="/recaudos/nuevo">
          Nuevo pago
        </Link>
      </div>
      {error ? <div className="error">{error}</div> : null}
      <div className="filters">
        <FilterSelect
          label="Actividad"
          value={actividad}
          emptyLabel="Todas"
          placeholder="Filtrar actividad"
          options={actividades.map((item) => ({ value: item.id, label: item.nombre }))}
          onSearch={(term) => void loadFiltros(term)}
          onChange={(value) => {
            setActividad(value);
            void load(1, value, padrino, q);
          }}
        />
        <FilterSelect
          label="Padrino"
          value={padrino}
          emptyLabel="Todos"
          placeholder="Filtrar padrino"
          options={padrinos.map((item) => ({ value: item.id, label: item.nombre_completo }))}
          onSearch={(term) => void loadFiltros(term)}
          onChange={(value) => {
            setPadrino(value);
            void load(1, actividad, value, q);
          }}
        />
        <label>
          Recibo o nombre
          <input
            placeholder="Número o aportante"
            value={q}
            onChange={(e) => {
              setQ(e.target.value);
              void load(1, actividad, padrino, e.target.value);
            }}
          />
        </label>
      </div>
      <div className="list">
        {items.map((item) => (
          <div className="list-item has-actions" key={item.id}>
            <Link className="list-item-main" to={`/recaudos/${item.id}`}>
              <strong>
                Recibo {item.numero_formateado} · {item.aportante_nombre}
              </strong>
              <div className="muted">
                {item.actividad_nombre} · {item.padrino_nombre} · {item.valor_formato}
              </div>
            </Link>
            <div className="list-item-meta">
              <span className={`badge ${item.estado}`}>{item.estado_display}</span>
              <RowActions
                editTo={item.estado === "confirmado" ? `/recaudos/${item.id}/editar` : undefined}
                confirmText={`¿Eliminar el recibo ${item.numero_formateado}? Se borra el PDF y los soportes. El número no se reutiliza.`}
                onDelete={async () => {
                  setError("");
                  try {
                    await api(`/api/recaudos/${item.id}/`, { method: "DELETE" });
                    await load(page, actividad, padrino, q);
                  } catch (err) {
                    setError(err instanceof ApiError ? err.message : "No se pudo eliminar el pago.");
                  }
                }}
              />
            </div>
          </div>
        ))}
        {!items.length ? <p className="muted">No hay pagos con ese filtro. Registre el primero.</p> : null}
      </div>
      <Pager page={page} pages={pages} count={count} label="pagos" onChange={(p) => void load(p)} />
    </div>
  );
}
