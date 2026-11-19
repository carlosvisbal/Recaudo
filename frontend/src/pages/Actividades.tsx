import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  api,
  ApiError,
  cop,
  parsePage,
  unwrapList,
  type Actividad,
  type ActividadControl,
  type Familia,
  type Padrino,
  type Recaudo,
  type Totales,
} from "../api";
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
          <p className="muted">Elija quiénes pagan y cada cuánto. Luego registre cada pago.</p>
        </div>
        <Link className="btn" to="/actividades/nueva">
          Nueva actividad
        </Link>
      </div>
      {error ? <div className="error">{error}</div> : null}
      <label style={{ marginBottom: 16 }}>
        Buscar
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
              <div className="muted">
                {item.tipo_label || (item.tipo === "general" ? "Personas" : "Padrinos y familias")}
                {" · "}
                {item.cobro_cada_label ||
                  (item.cobro_cada === "una_vez"
                    ? "Un solo pago"
                    : item.cobro_cada === "quincena"
                      ? "Cada quincena"
                      : "Cada mes")}
                {" · "}
                {item.tipo === "general"
                  ? `${item.cantidad_personas ?? item.personas?.length ?? 0} persona(s)`
                  : `${item.cantidad_familias ?? item.participantes?.length ?? 0} familia(s)`}
                {" · "}
                {item.cantidad_recaudos || 0} pagos · {cop(item.total_recaudado)}
              </div>
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

type FormState = {
  nombre: string;
  descripcion: string;
  fecha_inicio: string;
  fecha_fin: string;
  tipo: "apadrinamiento" | "general";
  cobro_cada: "una_vez" | "mes" | "quincena";
  estado: Actividad["estado"];
};

type PersonaDraft = { id?: string; nombre: string; telefono: string };

export function ActividadForm() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { ask, dialog } = useConfirm();
  const today = new Date().toISOString().slice(0, 10);
  const [item, setItem] = useState<FormState>({
    nombre: "",
    descripcion: "",
    fecha_inicio: today,
    fecha_fin: today,
    tipo: "apadrinamiento",
    cobro_cada: "mes",
    estado: "activa",
  });
  const [selectedFamilias, setSelectedFamilias] = useState<string[]>([]);
  const [personasDraft, setPersonasDraft] = useState<PersonaDraft[]>([]);
  const [padrinos, setPadrinos] = useState<Padrino[]>([]);
  const [familias, setFamilias] = useState<Familia[]>([]);
  const [padrinoVista, setPadrinoVista] = useState("");
  const [control, setControl] = useState<ActividadControl | null>(null);
  const [pagos, setPagos] = useState<Recaudo[]>([]);
  const [totales, setTotales] = useState<Totales | null>(null);
  const [error, setError] = useState("");
  const [okMsg, setOkMsg] = useState("");
  const [paginaPago, setPaginaPago] = useState(1);
  const [pagesPago, setPagesPago] = useState(1);
  const [countPago, setCountPago] = useState(0);
  const [showNuevaFamilia, setShowNuevaFamilia] = useState(false);
  const [nuevaFamilia, setNuevaFamilia] = useState({
    nombre: "",
    telefono: "",
    padrino: "",
  });
  const [busyFamilia, setBusyFamilia] = useState(false);

  const loadCatalogos = async () => {
    const [pData, fData] = await Promise.all([
      api(`/api/padrinos/?estado=activo&page_size=50`),
      api(`/api/familias/?estado=activo&page_size=50`),
    ]);
    setPadrinos(unwrapList<Padrino>(pData as never));
    setFamilias(unwrapList<Familia>(fData as never));
  };

  const loadPagos = async (pagina = 1) => {
    if (!id) return;
    const data = await api<{ resultados: Recaudo[]; totales: Totales }>(
      `/api/recaudos/?actividad=${id}&page=${pagina}`
    );
    const page = parsePage<Recaudo>(data);
    setPagos(page.results);
    setPagesPago(page.pages);
    setCountPago(page.count);
    setPaginaPago(page.page);
    setTotales(data.totales);
  };

  const loadControl = async () => {
    if (!id) return;
    setControl(await api<ActividadControl>(`/api/actividades/${id}/control/`));
  };

  useEffect(() => {
    void loadCatalogos();
  }, []);

  useEffect(() => {
    if (!id) return;
    void api<Actividad>(`/api/actividades/${id}/`).then((act) => {
      setItem({
        nombre: act.nombre,
        descripcion: act.descripcion || "",
        fecha_inicio: act.fecha_inicio,
        fecha_fin: act.fecha_fin,
        tipo: act.tipo || "apadrinamiento",
        cobro_cada: act.cobro_cada || "mes",
        estado: act.estado,
      });
      setSelectedFamilias((act.participantes || []).map((p) => p.familia));
      setPersonasDraft(
        (act.personas || []).map((p) => ({ id: p.id, nombre: p.nombre, telefono: p.telefono || "" }))
      );
    });
    void loadPagos(1);
    void loadControl();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const familiasPorPadrino = useMemo(() => {
    const map = new Map<string, Familia[]>();
    for (const fam of familias) {
      const list = map.get(fam.padrino) || [];
      list.push(fam);
      map.set(fam.padrino, list);
    }
    return map;
  }, [familias]);

  const padrinoActivo = padrinoVista || padrinos[0]?.id || "";
  const familiasVisibles = padrinoActivo ? familiasPorPadrino.get(padrinoActivo) || [] : [];

  const toggleFamilia = (familiaId: string) => {
    setSelectedFamilias((prev) =>
      prev.includes(familiaId) ? prev.filter((x) => x !== familiaId) : [...prev, familiaId]
    );
  };

  const seleccionarTodas = () => {
    const ids = familiasVisibles.map((f) => f.id);
    setSelectedFamilias((prev) => Array.from(new Set([...prev, ...ids])));
  };

  const quitarTodas = () => {
    const ids = new Set(familiasVisibles.map((f) => f.id));
    setSelectedFamilias((prev) => prev.filter((idFam) => !ids.has(idFam)));
  };

  const guardar = async () => {
    setError("");
    setOkMsg("");
    const body =
      item.tipo === "general"
        ? {
            ...item,
            personas_data: personasDraft
              .filter((p) => p.nombre.trim())
              .map((p) => ({
                ...(p.id ? { id: p.id } : {}),
                nombre: p.nombre.trim(),
                telefono: p.telefono.trim(),
              })),
            familias: [],
          }
        : {
            ...item,
            familias: selectedFamilias,
            personas_data: [],
          };
    if (id) {
      await api(`/api/actividades/${id}/`, { method: "PUT", body: JSON.stringify(body) });
      setOkMsg("Actividad guardada.");
      await loadControl();
      const act = await api<Actividad>(`/api/actividades/${id}/`);
      setPersonasDraft(
        (act.personas || []).map((p) => ({ id: p.id, nombre: p.nombre, telefono: p.telefono || "" }))
      );
    } else {
      const creada = await api<Actividad>("/api/actividades/", {
        method: "POST",
        body: JSON.stringify(body),
      });
      navigate(`/actividades/${creada.id}`);
    }
  };

  const crearFamilia = async () => {
    setBusyFamilia(true);
    setError("");
    try {
      const padrino = nuevaFamilia.padrino || padrinoActivo;
      if (!nuevaFamilia.nombre.trim()) throw new ApiError("Escriba el nombre de la familia.", 400, null);
      if (!padrino) throw new ApiError("Elija el padrino de la familia.", 400, null);
      const creada = await api<Familia>("/api/familias/", {
        method: "POST",
        body: JSON.stringify({
          nombre: nuevaFamilia.nombre.trim(),
          telefono: nuevaFamilia.telefono.trim(),
          padrino,
          estado: "activo",
          contacto_principal: "",
          correo: "",
          observaciones: "",
        }),
      });
      await loadCatalogos();
      setSelectedFamilias((prev) => (prev.includes(creada.id) ? prev : [...prev, creada.id]));
      setPadrinoVista(creada.padrino);
      setNuevaFamilia({ nombre: "", telefono: "", padrino: creada.padrino });
      setShowNuevaFamilia(false);
      setOkMsg(`Familia ${creada.nombre} agregada y marcada para esta actividad.`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo crear la familia.");
    } finally {
      setBusyFamilia(false);
    }
  };

  const form = (
    <form
      className="form-card"
      onSubmit={async (event) => {
        event.preventDefault();
        try {
          await guardar();
        } catch (err) {
          setError(err instanceof ApiError ? err.message : "No se pudo guardar.");
        }
      }}
    >
      <h2>{id ? "Datos de la actividad" : "Nueva actividad"}</h2>
      <p className="muted" style={{ marginTop: 0 }}>
        Tres pasos: nombre, cada cuánto se cobra, y quiénes pagan.
      </p>
      {error ? <div className="error">{error}</div> : null}
      {okMsg ? <div className="success-banner">{okMsg}</div> : null}

      <div className="step-block">
        <div className="step-label">1. Nombre</div>
        <div className="form-grid">
          <label className="span-2">
            Nombre de la actividad
            <input
              required
              value={item.nombre}
              onChange={(e) => setItem({ ...item, nombre: e.target.value })}
              placeholder="Ej. Aporte del colegio"
            />
          </label>
          <label className="span-2">
            Nota (opcional)
            <textarea
              value={item.descripcion}
              onChange={(e) => setItem({ ...item, descripcion: e.target.value })}
              rows={2}
            />
          </label>
          <label>
            Fecha inicial
            <input
              type="date"
              required
              value={item.fecha_inicio}
              onChange={(e) => setItem({ ...item, fecha_inicio: e.target.value })}
            />
          </label>
          <label>
            Fecha final
            <input
              type="date"
              required
              value={item.fecha_fin}
              onChange={(e) => setItem({ ...item, fecha_fin: e.target.value })}
            />
          </label>
          {id ? (
            <FilterSelect
              className="span-2"
              label="Estado"
              value={item.estado}
              options={[
                { value: "programada", label: "Programada" },
                { value: "activa", label: "Activa" },
                { value: "cerrada", label: "Cerrada" },
              ]}
              onChange={(value) => setItem({ ...item, estado: value as Actividad["estado"] })}
            />
          ) : null}
        </div>
      </div>

      <div className="step-block">
        <div className="step-label">2. Tipo de recaudo</div>
        <div className="choice-row" role="group" aria-label="Tipo de recaudo">
          <button
            type="button"
            className={`choice-btn ${item.tipo === "apadrinamiento" ? "on" : ""}`}
            onClick={() => setItem({ ...item, tipo: "apadrinamiento" })}
          >
            Padrinos y familias
          </button>
          <button
            type="button"
            className={`choice-btn ${item.tipo === "general" ? "on" : ""}`}
            onClick={() => setItem({ ...item, tipo: "general" })}
          >
            Personas (nombre y celular)
          </button>
        </div>
      </div>

      <div className="step-block">
        <div className="step-label">3. Cada cuánto se cobra</div>
        <div className="choice-row" role="group" aria-label="Cada cuánto se cobra">
          <button
            type="button"
            className={`choice-btn ${item.cobro_cada === "una_vez" ? "on" : ""}`}
            onClick={() => setItem({ ...item, cobro_cada: "una_vez" })}
          >
            Un solo pago
          </button>
          <button
            type="button"
            className={`choice-btn ${item.cobro_cada === "mes" ? "on" : ""}`}
            onClick={() => setItem({ ...item, cobro_cada: "mes" })}
          >
            Cada mes
          </button>
          <button
            type="button"
            className={`choice-btn ${item.cobro_cada === "quincena" ? "on" : ""}`}
            onClick={() => setItem({ ...item, cobro_cada: "quincena" })}
          >
            Cada quincena
          </button>
        </div>
        <p className="muted" style={{ margin: "8px 0 0" }}>
          {item.cobro_cada === "una_vez"
            ? "Cada persona o familia paga una sola vez en toda la actividad."
            : item.cobro_cada === "quincena"
              ? "Se revisa quién pagó en la quincena actual (1–15 o 16–fin de mes)."
              : "Se revisa quién pagó en el mes actual."}
        </p>
      </div>

      <div className="step-block">
        <div className="step-label">4. Quiénes pagan</div>
        {item.tipo === "general" ? (
          <>
            <p className="muted" style={{ marginTop: 0 }}>
              Agregue personas con nombre y celular. No hace falta padrino ni familia.
            </p>
            <div className="family-check-list">
              {personasDraft.map((persona, index) => (
                <div key={persona.id || `new-${index}`} className="family-check on" style={{ display: "grid", gap: 8 }}>
                  <label>
                    Nombre
                    <input
                      value={persona.nombre}
                      onChange={(e) => {
                        const next = [...personasDraft];
                        next[index] = { ...persona, nombre: e.target.value };
                        setPersonasDraft(next);
                      }}
                      placeholder="Nombre de la persona"
                    />
                  </label>
                  <label>
                    Celular
                    <input
                      inputMode="tel"
                      value={persona.telefono}
                      onChange={(e) => {
                        const next = [...personasDraft];
                        next[index] = { ...persona, telefono: e.target.value };
                        setPersonasDraft(next);
                      }}
                      placeholder="3001234567"
                    />
                  </label>
                  <button
                    type="button"
                    className="btn secondary"
                    onClick={() => setPersonasDraft(personasDraft.filter((_, i) => i !== index))}
                  >
                    Quitar
                  </button>
                </div>
              ))}
            </div>
            <button
              type="button"
              className="btn gold"
              onClick={() => setPersonasDraft([...personasDraft, { nombre: "", telefono: "" }])}
            >
              Agregar persona
            </button>
            <p className="muted">
              Personas: <strong>{personasDraft.filter((p) => p.nombre.trim()).length}</strong>
            </p>
          </>
        ) : !padrinos.length ? (
          <p className="muted">Primero cree un padrino en el menú Padrinos.</p>
        ) : (
          <>
            <p className="muted" style={{ marginTop: 0 }}>
              Elija el padrino y marque las familias. Puede agregar una familia nueva aquí mismo.
            </p>
            <label>
              Padrino
              <select value={padrinoActivo} onChange={(e) => setPadrinoVista(e.target.value)}>
                {padrinos.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.nombre_completo}
                  </option>
                ))}
              </select>
            </label>
            <div className="family-tools">
              <button type="button" className="btn secondary" onClick={seleccionarTodas}>
                Marcar todas
              </button>
              <button type="button" className="btn secondary" onClick={quitarTodas}>
                Quitar todas
              </button>
              <button
                type="button"
                className="btn gold"
                onClick={() => {
                  setNuevaFamilia((prev) => ({ ...prev, padrino: padrinoActivo }));
                  setShowNuevaFamilia(true);
                }}
              >
                Agregar familia
              </button>
            </div>
            <div className="family-check-list">
              {familiasVisibles.map((fam) => {
                const checked = selectedFamilias.includes(fam.id);
                return (
                  <label key={fam.id} className={`family-check ${checked ? "on" : ""}`}>
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => toggleFamilia(fam.id)}
                    />
                    <span>
                      <strong>{fam.nombre}</strong>
                      {fam.telefono ? <span className="muted"> · {fam.telefono}</span> : null}
                    </span>
                  </label>
                );
              })}
              {!familiasVisibles.length ? (
                <p className="muted">Este padrino aún no tiene familias. Use “Agregar familia”.</p>
              ) : null}
            </div>
            <p className="muted">
              Seleccionadas en total: <strong>{selectedFamilias.length}</strong>
            </p>
          </>
        )}
      </div>

      {showNuevaFamilia ? (
        <div className="form-card nested-card">
          <h2>Agregar familia</h2>
          <div className="form-grid">
            <label className="span-2">
              Nombre de la familia
              <input
                autoFocus
                value={nuevaFamilia.nombre}
                onChange={(e) => setNuevaFamilia({ ...nuevaFamilia, nombre: e.target.value })}
              />
            </label>
            <label>
              Celular
              <input
                value={nuevaFamilia.telefono}
                onChange={(e) => setNuevaFamilia({ ...nuevaFamilia, telefono: e.target.value })}
                inputMode="tel"
              />
            </label>
            <label>
              Padrino
              <select
                value={nuevaFamilia.padrino || padrinoActivo}
                onChange={(e) => setNuevaFamilia({ ...nuevaFamilia, padrino: e.target.value })}
              >
                {padrinos.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.nombre_completo}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <div className="actions">
            <button type="button" className="btn" disabled={busyFamilia} onClick={() => void crearFamilia()}>
              {busyFamilia ? "Guardando…" : "Guardar familia"}
            </button>
            <button type="button" className="btn secondary" onClick={() => setShowNuevaFamilia(false)}>
              Cancelar
            </button>
          </div>
        </div>
      ) : null}

      <div className="actions">
        <button className="btn">Guardar actividad</button>
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
          <p className="muted">Indique cada cuánto se cobra y qué familias van a pagar.</p>
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
          <div className="eyebrow">Actividad</div>
          <h1>{item.nombre || "Actividad"}</h1>
          <p className="muted">
            {item.tipo === "general" ? "Personas" : "Padrinos y familias"}
            {" · "}
            {item.cobro_cada === "una_vez"
              ? "Un solo pago"
              : item.cobro_cada === "quincena"
                ? "Cada quincena"
                : "Cada mes"}
            {control ? ` · ${control.etiqueta_periodo}` : ""}
          </p>
        </div>
        <Link className="btn gold" to={`/recaudos/nuevo?actividad=${id}`}>
          Registrar pago
        </Link>
      </div>

      <div className="grid">
        <div className="card">
          <div className="muted">Total recaudado</div>
          <div className="kpi">{totales?.total_confirmado_formato || cop("0")}</div>
        </div>
        <div className="card">
          <div className="muted">Pagaron</div>
          <div className="kpi success-text">{control?.cantidad_pagaron ?? 0}</div>
        </div>
        <div className="card">
          <div className="muted">Faltan por pagar</div>
          <div className="kpi danger-text">{control?.cantidad_faltan ?? 0}</div>
        </div>
      </div>

      {control ? (
        <div className="form-card" style={{ marginTop: 16 }}>
          <h2>Control · {control.etiqueta_periodo}</h2>
          <p className="muted" style={{ marginTop: 0 }}>
            {control.tipo === "general"
              ? `Personas de esta actividad: ${control.cantidad_personas ?? control.cantidad_familias}`
              : `Familias de esta actividad: ${control.cantidad_familias}`}
          </p>
          <div className="control-columns">
            <div>
              <h3 className="success-text">Pagaron ({control.cantidad_pagaron})</h3>
              <div className="list compact">
                {control.pagaron.map((row) => (
                  <div className="list-item" key={row.persona_id || row.familia_id}>
                    <div>
                      <strong>{row.persona_nombre || row.familia_nombre}</strong>
                      <div className="muted">
                        {row.padrino_nombre || row.telefono || ""}
                      </div>
                    </div>
                    <span className="badge confirmado">Pagó</span>
                  </div>
                ))}
                {!control.pagaron.length ? <p className="muted">Nadie ha pagado aún en este tramo.</p> : null}
              </div>
            </div>
            <div>
              <h3 className="danger-text">Faltan por pagar ({control.cantidad_faltan})</h3>
              <div className="list compact">
                {control.faltan.map((row) => (
                  <div className="list-item" key={row.persona_id || row.familia_id}>
                    <div>
                      <strong>{row.persona_nombre || row.familia_nombre}</strong>
                      <div className="muted">
                        {row.padrino_nombre ? `${row.padrino_nombre}` : ""}
                        {row.telefono ? `${row.padrino_nombre ? " · " : ""}${row.telefono}` : ""}
                      </div>
                    </div>
                    <span className="badge warning">Falta</span>
                  </div>
                ))}
                {!control.faltan.length ? <p className="muted">Todas al día en este tramo.</p> : null}
              </div>
            </div>
          </div>
        </div>
      ) : null}

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
        {!pagos.length ? <p className="muted">Aún no hay pagos. Registre el primero.</p> : null}
      </div>
      <Pager page={paginaPago} pages={pagesPago} count={countPago} label="pagos" onChange={(p) => void loadPagos(p)} />
      <h2 style={{ margin: "24px 0 12px" }}>Editar actividad</h2>
      {form}
      {dialog}
    </div>
  );
}
