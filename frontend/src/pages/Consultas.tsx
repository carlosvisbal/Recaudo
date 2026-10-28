import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  api,
  cop,
  parsePage,
  type Actividad,
  type Padrino,
  type Recaudo,
  type Totales,
} from "../api";
import { FilterSelect } from "../components/FilterSelect";
import { Pager, slicePage } from "../components/Pager";

const VISTAS = [
  { id: "actividad", label: "Por actividad" },
  { id: "padrino", label: "Por padrino" },
  { id: "fecha", label: "Por fecha" },
  { id: "cruzado", label: "Padrino × actividad" },
  { id: "pendientes", label: "Pendientes" },
  { id: "pagos", label: "Pagos" },
] as const;

type Vista = (typeof VISTAS)[number]["id"];

export function Consultas() {
  const [padrinos, setPadrinos] = useState<Padrino[]>([]);
  const [actividades, setActividades] = useState<Actividad[]>([]);
  const [filtros, setFiltros] = useState({
    padrino: "",
    actividad: "",
    fecha_inicial: "",
    fecha_final: "",
  });
  const [vista, setVista] = useState<Vista>("actividad");
  const [informe, setInforme] = useState<Totales | null>(null);
  const [resultados, setResultados] = useState<Recaudo[]>([]);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [count, setCount] = useState(0);
  const [pagTabla, setPagTabla] = useState(1);
  const [pagPend, setPagPend] = useState(1);
  const [busy, setBusy] = useState(false);

  const loadPadrinos = useCallback(async (term = "") => {
    const params = new URLSearchParams({ page: "1" });
    if (term.trim()) params.set("q", term.trim());
    setPadrinos(parsePage<Padrino>(await api(`/api/padrinos/?${params}`)).results);
  }, []);

  const loadActividades = useCallback(async (term = "") => {
    const params = new URLSearchParams({ page: "1" });
    if (term.trim()) params.set("q", term.trim());
    setActividades(parsePage<Actividad>(await api(`/api/actividades/?${params}`)).results);
  }, []);

  const query = (pagina = 1) => {
    const params = new URLSearchParams();
    Object.entries(filtros).forEach(([k, v]) => {
      if (v) params.set(k, v);
    });
    params.set("page", String(pagina));
    return params.toString();
  };

  const consultar = async (paginaPend = 1, paginaPagos = 1) => {
    setBusy(true);
    try {
      const paramsInforme = new URLSearchParams(query(paginaPend));
      const data = await api<Totales>(`/api/informes/?${paramsInforme}`);
      setInforme(data);
      setPagPend(data.pendientes?.page || paginaPend);
      const pagos = await api<{ resultados: Recaudo[]; totales: Totales }>(`/api/recaudos/?${query(paginaPagos)}`);
      const parsed = parsePage<Recaudo>(pagos);
      setResultados(parsed.results);
      setPages(parsed.pages);
      setCount(parsed.count);
      setPage(parsed.page);
      setPagTabla(1);
    } finally {
      setBusy(false);
    }
  };

  useEffect(() => {
    void loadPadrinos();
    void loadActividades();
    void consultar(1, 1);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    setPagTabla(1);
  }, [vista]);

  const cruzado = informe?.por_padrino_actividad || [];
  const pendientes = informe?.pendientes;

  return (
    <div>
      <div className="toolbar">
        <div>
          <div className="eyebrow">Reportes</div>
          <h1>Informes</h1>
          <p className="muted">
            Totales por actividad, padrino y fecha. Pendientes: familias activas sin pago confirmado, por padrino y
            actividad.
          </p>
        </div>
        <a className="btn secondary" href={`/api/informes/exportar/?${query()}`}>
          Exportar Excel
        </a>
      </div>

      <div className="report-tabs" role="tablist" aria-label="Tipo de informe">
        {VISTAS.map((item) => (
          <button
            key={item.id}
            type="button"
            role="tab"
            aria-selected={vista === item.id}
            className={vista === item.id ? "on" : ""}
            onClick={() => setVista(item.id)}
          >
            {item.label}
            {item.id === "pendientes" && pendientes?.count ? ` (${pendientes.count})` : ""}
          </button>
        ))}
      </div>

      <div className="grid">
        <div className="card">
          <div className="muted">Recaudado</div>
          <div className="kpi">{informe?.total_confirmado_formato || cop("0")}</div>
        </div>
        <div className="card">
          <div className="muted">Pagos confirmados</div>
          <div className="kpi">{informe?.cantidad_confirmados ?? 0}</div>
        </div>
        <div className="card">
          <div className="muted">Pendientes</div>
          <div className="kpi">{pendientes?.count ?? 0}</div>
          <p className="muted" style={{ margin: "6px 0 0" }}>
            {pendientes?.familias_al_dia ?? 0} familia(s) al día de {pendientes?.familias_asignadas ?? 0}
          </p>
        </div>
      </div>

      <div className="form-card">
        <div className="form-grid">
          <FilterSelect
            label="Padrino"
            value={filtros.padrino}
            emptyLabel="Todos los padrinos"
            placeholder="Escriba para filtrar padrinos"
            options={padrinos.map((p) => ({ value: p.id, label: p.nombre_completo }))}
            onSearch={(term) => void loadPadrinos(term)}
            onChange={(value) => setFiltros({ ...filtros, padrino: value })}
          />
          <FilterSelect
            label="Actividad"
            value={filtros.actividad}
            emptyLabel="Actividades abiertas"
            placeholder="Escriba para filtrar actividades"
            options={actividades.map((a) => ({ value: a.id, label: a.nombre }))}
            onSearch={(term) => void loadActividades(term)}
            onChange={(value) => setFiltros({ ...filtros, actividad: value })}
          />
          <label>
            Fecha inicial
            <input
              type="date"
              value={filtros.fecha_inicial}
              onChange={(e) => setFiltros({ ...filtros, fecha_inicial: e.target.value })}
            />
          </label>
          <label>
            Fecha final
            <input
              type="date"
              value={filtros.fecha_final}
              onChange={(e) => setFiltros({ ...filtros, fecha_final: e.target.value })}
            />
          </label>
        </div>
        <div className="actions">
          <button className="btn" type="button" disabled={busy} onClick={() => void consultar(1, 1)}>
            {busy ? "Consultando…" : "Consultar"}
          </button>
        </div>
      </div>

      {vista === "actividad" ? (
        <>
          <div className="list">
            {slicePage(informe?.por_actividad || [], pagTabla).pageItems.map((row) => (
              <Link className="list-item" key={row.id || row.nombre} to={row.id ? `/actividades/${row.id}` : "/actividades"}>
                <div>
                  <strong>{row.nombre}</strong>
                  <div className="muted">{row.cantidad} pagos</div>
                </div>
                <div>{row.total_formato || cop(row.total)}</div>
              </Link>
            ))}
            {!informe?.por_actividad?.length ? <p className="muted">No hay recaudos en este filtro.</p> : null}
          </div>
          <Pager
            page={pagTabla}
            pages={slicePage(informe?.por_actividad || [], pagTabla).pages}
            count={informe?.por_actividad.length || 0}
            label="actividades"
            onChange={setPagTabla}
          />
        </>
      ) : null}

      {vista === "padrino" ? (
        <>
          <div className="list">
            {slicePage(informe?.por_padrino || [], pagTabla).pageItems.map((row) => (
              <Link className="list-item" key={row.id || row.nombre} to={row.id ? `/padrinos/${row.id}` : "/padrinos"}>
                <div>
                  <strong>{row.nombre}</strong>
                  <div className="muted">{row.cantidad} pagos</div>
                </div>
                <div>{row.total_formato || cop(row.total)}</div>
              </Link>
            ))}
            {!informe?.por_padrino?.length ? <p className="muted">No hay recaudos en este filtro.</p> : null}
          </div>
          <Pager
            page={pagTabla}
            pages={slicePage(informe?.por_padrino || [], pagTabla).pages}
            count={informe?.por_padrino.length || 0}
            label="padrinos"
            onChange={setPagTabla}
          />
        </>
      ) : null}

      {vista === "fecha" ? (
        <>
          <div className="list">
            {slicePage(informe?.por_fecha || [], pagTabla).pageItems.map((row) => (
              <div className="list-item" key={row.fecha || row.nombre}>
                <div>
                  <strong>{row.fecha || row.nombre}</strong>
                  <div className="muted">{row.cantidad} pagos</div>
                </div>
                <div>{row.total_formato || cop(row.total)}</div>
              </div>
            ))}
            {!informe?.por_fecha?.length ? <p className="muted">No hay recaudos en este rango de fechas.</p> : null}
          </div>
          <Pager
            page={pagTabla}
            pages={slicePage(informe?.por_fecha || [], pagTabla).pages}
            count={informe?.por_fecha?.length || 0}
            label="días"
            onChange={setPagTabla}
          />
        </>
      ) : null}

      {vista === "cruzado" ? (
        <>
          <p className="muted">
            Cada tarjeta es un padrino en una actividad: lo recaudado y cuántas de sus familias aún no pagan.
          </p>
          <div className="list">
            {slicePage(cruzado, pagTabla).pageItems.map((row) => (
              <div className="list-item stack-sm" key={`${row.padrino_id}-${row.actividad_id}`}>
                <div>
                  <strong>{row.padrino_nombre}</strong>
                  <div className="muted">{row.actividad_nombre}</div>
                  <div className="muted">
                    Pagaron {row.familias_pagaron} de {row.familias_asignadas}
                  </div>
                </div>
                <div className="list-item-meta">
                  <div>{row.total_formato || cop(row.total)}</div>
                  <div className="muted">{row.cantidad} pagos</div>
                  {row.familias_pendientes ? (
                    <span className="badge warning">{row.familias_pendientes} pendientes</span>
                  ) : (
                    <span className="badge activo">Al día</span>
                  )}
                </div>
              </div>
            ))}
            {!cruzado.length ? <p className="muted">No hay padrinos o actividades para cruzar.</p> : null}
          </div>
          <Pager
            page={pagTabla}
            pages={slicePage(cruzado, pagTabla).pages}
            count={cruzado.length}
            label="filas"
            onChange={setPagTabla}
          />
        </>
      ) : null}

      {vista === "pendientes" ? (
        <>
          <p className="muted">
            Familias activas sin recaudo confirmado en la actividad. Toque Registrar para cargar el pago.
          </p>
          <div className="list">
            {(pendientes?.results || []).map((row) => (
              <div className="list-item stack-sm" key={`${row.familia_id}-${row.actividad_id}`}>
                <div>
                  <strong>{row.familia_nombre}</strong>
                  <div className="muted">
                    {row.padrino_nombre} · {row.actividad_nombre}
                    {row.telefono ? ` · ${row.telefono}` : ""}
                  </div>
                </div>
                <Link
                  className="btn"
                  to={`/recaudos/nuevo?familia=${row.familia_id}&padrino=${row.padrino_id}&actividad=${row.actividad_id}`}
                >
                  Registrar
                </Link>
              </div>
            ))}
            {!pendientes?.count ? (
              <p className="muted">No hay pendientes de pago con este filtro.</p>
            ) : null}
          </div>
          <Pager
            page={pagPend}
            pages={pendientes?.pages || 1}
            count={pendientes?.count || 0}
            label="pendientes"
            onChange={(p) => void consultar(p, page)}
          />
        </>
      ) : null}

      {vista === "pagos" ? (
        <>
          <div className="list">
            {resultados.map((row) => (
              <Link className="list-item" key={row.id} to={`/recaudos/${row.id}`}>
                <div>
                  <strong>{row.aportante_nombre}</strong>
                  <div className="muted">
                    Recibo {row.numero_formateado} · {row.fecha}
                  </div>
                  <div className="muted">
                    {row.padrino_nombre} · {row.actividad_nombre}
                  </div>
                </div>
                <div className="list-item-meta">
                  <div>{row.valor_formato}</div>
                  <span className={`badge ${row.estado}`}>{row.estado_display}</span>
                </div>
              </Link>
            ))}
          </div>
          {!resultados.length ? <p className="muted">No hay pagos en este filtro.</p> : null}
          <Pager page={page} pages={pages} count={count} label="pagos" onChange={(p) => void consultar(pagPend, p)} />
        </>
      ) : null}
    </div>
  );
}
