import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import {
  api,
  ApiError,
  cop,
  parsePage,
  type Actividad,
  type ActividadControl,
  type Familia,
  type Padrino,
  type Recaudo,
} from "../api";
import { FilterSelect } from "../components/FilterSelect";

const MAX_SOPORTE_BYTES = 5 * 1024 * 1024;

type FilaParticipante = {
  key: string;
  nombre: string;
  telefono: string;
  ya_pago: boolean;
  familia_id?: string;
  padrino_id?: string;
  padrino_nombre?: string;
  persona_id?: string;
};

function tipoDeActividad(lista: Actividad[], idAct: string): "apadrinamiento" | "general" {
  const found = lista.find((a) => a.id === idAct);
  return found?.tipo === "general" ? "general" : "apadrinamiento";
}

function today() {
  return new Date().toISOString().slice(0, 10);
}

function parseValor(raw: string): string {
  const trimmed = raw.trim().replace(/\s/g, "");
  if (!trimmed) return "";
  const hasComma = trimmed.includes(",");
  const hasDot = trimmed.includes(".");
  let normalized = trimmed;
  if (hasComma && hasDot) {
    normalized = trimmed.replace(/\./g, "").replace(",", ".");
  } else if (hasComma) {
    normalized = trimmed.replace(",", ".");
  }
  const value = Number(normalized);
  if (Number.isNaN(value)) return "";
  return value.toFixed(2);
}

export function RecaudoEditar() {
  return <RecaudoNuevo />;
}

export function RecaudoNuevo() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [soportesExistentes, setSoportesExistentes] = useState(0);
  const [familia, setFamilia] = useState<Familia | null>(null);
  const [personaId, setPersonaId] = useState(params.get("persona") || "");
  const [personaNombre, setPersonaNombre] = useState("");
  const [actividades, setActividades] = useState<Actividad[]>([]);
  const [filtroActividad, setFiltroActividad] = useState("");
  const [padrinos, setPadrinos] = useState<Padrino[]>([]);
  const [actividad, setActividad] = useState(params.get("actividad") || "");
  const [padrino, setPadrino] = useState(params.get("padrino") || "");
  const [control, setControl] = useState<ActividadControl | null>(null);
  const [cargandoControl, setCargandoControl] = useState(false);
  const [qFamilia, setQFamilia] = useState("");
  const [filtroEstado, setFiltroEstado] = useState<"todas" | "faltan" | "pagaron">("faltan");
  const [fecha, setFecha] = useState(today());
  const [valor, setValor] = useState("");
  const [medio, setMedio] = useState<"efectivo" | "transferencia">("efectivo");
  const [concepto, setConcepto] = useState("");
  const [referencia, setReferencia] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [confirmar, setConfirmar] = useState(false);
  const [crearFamilia, setCrearFamilia] = useState(false);
  const [nuevaFamilia, setNuevaFamilia] = useState({ nombre: "", telefono: "", padrino: "" });
  const [guardandoFamilia, setGuardandoFamilia] = useState(false);
  const [errorFamilia, setErrorFamilia] = useState("");

  const loadActividades = useCallback(async (term = "") => {
    const query = new URLSearchParams({ page: "1", page_size: "50" });
    if (term.trim()) query.set("q", term.trim());
    const data = parsePage<Actividad>(await api(`/api/actividades/?${query}`));
    setActividades(data.results.filter((a) => a.estado !== "cerrada"));
  }, []);

  const loadPadrinos = useCallback(async (term = "") => {
    const query = new URLSearchParams({ estado: "activo", page: "1", page_size: "50" });
    if (term.trim()) query.set("q", term.trim());
    setPadrinos(parsePage<Padrino>(await api(`/api/padrinos/?${query}`)).results);
  }, []);

  const loadControl = useCallback(async (actividadId: string, fechaRef = fecha) => {
    if (!actividadId) {
      setControl(null);
      return;
    }
    setCargandoControl(true);
    try {
      const query = new URLSearchParams();
      if (fechaRef) query.set("fecha", fechaRef);
      const data = await api<ActividadControl>(`/api/actividades/${actividadId}/control/?${query}`);
      setControl(data);
    } catch {
      setControl(null);
    } finally {
      setCargandoControl(false);
    }
  }, [fecha]);

  useEffect(() => {
    void loadActividades();
    void loadPadrinos();
  }, [loadActividades, loadPadrinos]);

  useEffect(() => {
    if (!id) return;
    void api<Recaudo>(`/api/recaudos/${id}/`).then((item) => {
      setActividad(item.actividad);
      setPadrino(item.padrino);
      setFecha(item.fecha);
      setValor(String(Number(item.valor)));
      setMedio(item.medio_pago);
      setConcepto(item.concepto || "");
      setReferencia(item.referencia_consignacion || "");
      setSoportesExistentes(item.soportes?.length || item.soportes_count || 0);
      setActividades((actual) =>
        actual.some((a) => a.id === item.actividad)
          ? actual
          : [
              {
                id: item.actividad,
                nombre: item.actividad_nombre,
                descripcion: "",
                fecha_inicio: "",
                fecha_fin: "",
                estado: "activa",
                cobro_cada: "mes",
              },
              ...actual,
            ]
      );
      if (item.familia) {
        void api<Familia>(`/api/familias/${item.familia}/`).then(setFamilia);
      }
    });
  }, [id]);

  useEffect(() => {
    const familiaId = params.get("familia");
    if (familiaId) {
      void api<Familia>(`/api/familias/${familiaId}/`).then((item) => {
        setFamilia(item);
        setPadrino(item.padrino);
      });
    }
    const actId = params.get("actividad");
    if (actId) {
      void api<Actividad>(`/api/actividades/${actId}/`).then((item) => {
        setActividad(item.id);
        setActividades((actual) => (actual.some((a) => a.id === item.id) ? actual : [item, ...actual]));
      });
    }
  }, [params]);

  useEffect(() => {
    if (!actividad) {
      setControl(null);
      return;
    }
    void loadControl(actividad, fecha);
  }, [actividad, fecha, loadControl]);

  const valorOk = useMemo(() => parseValor(valor), [valor]);
  const actividadActual =
    actividades.find((a) => a.id === actividad) ||
    (actividad ? ({ id: actividad, nombre: "Actividad seleccionada" } as Actividad) : undefined);
  const esGeneral =
    control?.tipo === "general" ||
    actividadActual?.tipo === "general" ||
    tipoDeActividad(actividades, actividad) === "general";
  const padrinoActual = padrinos.find((item) => item.id === padrino);
  const yaRecaudado = Number(actividadActual?.total_recaudado || 0);
  const nuevoTotal = yaRecaudado + Number(valorOk || 0);
  const muchasActividades = actividades.length > 8;
  const atajosActividad = useMemo(() => {
    return [...actividades]
      .sort((a, b) => (b.cantidad_recaudos || 0) - (a.cantidad_recaudos || 0))
      .slice(0, 4);
  }, [actividades]);
  const actividadesVisibles = useMemo(() => {
    const term = filtroActividad.trim().toLowerCase();
    const base = term
      ? actividades.filter((item) => item.nombre.toLowerCase().includes(term))
      : actividades;
    return base.slice(0, 8);
  }, [actividades, filtroActividad]);
  const coincidenciasActividad = useMemo(() => {
    const term = filtroActividad.trim().toLowerCase();
    if (!term) return actividades.length;
    return actividades.filter((item) => item.nombre.toLowerCase().includes(term)).length;
  }, [actividades, filtroActividad]);

  const filas = useMemo<FilaParticipante[]>(() => {
    if (!control) return [];
    const mapRow = (row: ActividadControl["pagaron"][number], ya_pago: boolean): FilaParticipante => {
      if (row.persona_id) {
        return {
          key: row.persona_id,
          nombre: row.persona_nombre || "",
          telefono: row.telefono || "",
          ya_pago,
          persona_id: row.persona_id,
        };
      }
      return {
        key: row.familia_id || "",
        nombre: row.familia_nombre || "",
        telefono: row.telefono || "",
        ya_pago,
        familia_id: row.familia_id,
        padrino_id: row.padrino_id,
        padrino_nombre: row.padrino_nombre,
      };
    };
    return [
      ...control.faltan.map((row) => mapRow(row, false)),
      ...control.pagaron.map((row) => mapRow(row, true)),
    ];
  }, [control]);

  const filasVisibles = useMemo(() => {
    const term = qFamilia.trim().toLowerCase();
    return filas.filter((row) => {
      if (filtroEstado === "faltan" && row.ya_pago) return false;
      if (filtroEstado === "pagaron" && !row.ya_pago) return false;
      if (!esGeneral && padrino && row.padrino_id !== padrino) return false;
      if (!term) return true;
      return (
        row.nombre.toLowerCase().includes(term) ||
        (row.padrino_nombre || "").toLowerCase().includes(term) ||
        row.telefono.includes(term)
      );
    });
  }, [filas, filtroEstado, qFamilia, padrino, esGeneral]);

  const yaPagoSeleccionado = useMemo(() => {
    if (!control || id) return false;
    if (esGeneral && personaId) {
      return control.pagaron.some((row) => row.persona_id === personaId);
    }
    if (familia) {
      return control.pagaron.some((row) => row.familia_id === familia.id);
    }
    return false;
  }, [control, id, esGeneral, personaId, familia]);

  function elegirParticipante(row: FilaParticipante) {
    setError("");
    if (row.persona_id) {
      setPersonaId(row.persona_id);
      setPersonaNombre(row.nombre);
      setFamilia(null);
      setPadrino("");
      return;
    }
    setPersonaId("");
    setPersonaNombre("");
    setFamilia({
      id: row.familia_id || "",
      nombre: row.nombre,
      contacto_principal: "",
      telefono: row.telefono,
      correo: "",
      padrino: row.padrino_id || "",
      padrino_nombre: row.padrino_nombre || "",
      observaciones: "",
      estado: "activo",
    });
    setPadrino(row.padrino_id || "");
  }

  function validar(): boolean {
    setError("");
    if (!actividad) {
      setError("Seleccione arriba la actividad en la que registra este recaudo.");
      return false;
    }
    if (esGeneral) {
      if (!personaId) {
        setError("Toque la persona que está pagando.");
        return false;
      }
    } else {
      if (!familia) {
        setError("Toque la familia que está pagando.");
        return false;
      }
      if (!padrino) {
        setError("Falta el padrino de esa familia.");
        return false;
      }
    }
    if (!valorOk) {
      setError("Indique el valor recibido.");
      return false;
    }
    if (medio === "transferencia" && files.length === 0 && !soportesExistentes) {
      setError("Adjunte el comprobante de la transferencia (archivo PDF o imagen, no una foto de la cámara).");
      return false;
    }
    const pesado = files.find((file) => file.size > MAX_SOPORTE_BYTES);
    if (pesado) {
      setError(`"${pesado.name}" pesa más de 5 MB. Use un archivo más liviano.`);
      return false;
    }
    return true;
  }

  async function guardar() {
    if (!valorOk) return;
    if (esGeneral && !personaId) return;
    if (!esGeneral && !familia) return;
    setBusy(true);
    setError("");
    try {
      const body = new FormData();
      body.append("fecha", fecha);
      body.append("actividad", actividad);
      body.append("valor", valorOk);
      body.append("medio_pago", medio);
      body.append("concepto", concepto);
      body.append("referencia_consignacion", referencia);
      if (esGeneral) {
        body.append("persona", personaId);
        body.append("aportante_nombre", personaNombre);
      } else if (familia) {
        body.append("padrino", padrino);
        body.append("familia", familia.id);
        body.append("aportante_nombre", familia.nombre);
      }
      if (medio === "transferencia") {
        files.forEach((file) => body.append("soportes", file));
      }
      const creado = await api<{ id: string }>(id ? `/api/recaudos/${id}/` : "/api/recaudos/", {
        method: id ? "PUT" : "POST",
        body,
      });
      navigate(id ? `/recaudos/${creado.id}` : `/recaudos/${creado.id}?nuevo=1`);
    } catch (err) {
      setConfirmar(false);
      setError(err instanceof ApiError ? err.message : "No se pudo registrar el pago.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form
      className="form form-wide"
      onSubmit={(event) => {
        event.preventDefault();
        if (validar()) setConfirmar(true);
      }}
    >
      <div>
        <div className="eyebrow">{id ? "Edición de recaudo" : "Registro de recaudo"}</div>
        <h1>{id ? "Editar pago" : "Registrar pago"}</h1>
        <p className="muted">
          Elija la actividad, toque la familia y digite el valor. Si esa familia ya pagó en el mes o la quincena, se lo
          avisamos para que no duplique.
        </p>
      </div>

      <section className="form-card">
        <div className="form-step">
          <span className="step-num">1</span>
          <div>
            <h2>¿En qué actividad se registra este recaudo?</h2>
            <p className="muted">
              {muchasActividades
                ? `Hay ${actividades.length} actividades. Búsquela por nombre; no se listan todas a la vez.`
                : "Toque la actividad. El valor suma solo en la que elija."}
            </p>
          </div>
        </div>
        {muchasActividades ? (
          <>
            <FilterSelect
              label="Buscar actividad"
              required
              value={actividad}
              placeholder="Escriba el nombre (ej. kermés, rifa, domingo)"
              emptyLabel="Seleccione la actividad"
              options={actividades.map((item) => ({
                value: item.id,
                label: item.nombre,
                hint: `${cop(item.total_recaudado)} · ${item.cantidad_recaudos || 0} pagos · ${item.estado}`,
              }))}
              onSearch={(term) => void loadActividades(term)}
              onChange={(value) => {
                setActividad(value);
                setFamilia(null);
                setPersonaId("");
                setPersonaNombre("");
                setPadrino("");
                setFiltroEstado("faltan");
              }}
            />
            {atajosActividad.length ? (
              <>
                <p className="muted">Atajos: las que más pagos tienen</p>
                <div className="chips">
                  {atajosActividad.map((item) => (
                    <button
                      type="button"
                      key={item.id}
                      className={actividad === item.id ? "chip on" : "chip"}
                      onClick={() => {
                        setActividad(item.id);
                        setFamilia(null);
                        setPersonaId("");
                        setPersonaNombre("");
                        setPadrino("");
                        setFiltroEstado("faltan");
                      }}
                    >
                      {item.nombre}
                    </button>
                  ))}
                </div>
              </>
            ) : null}
          </>
        ) : (
          <>
            {actividades.length > 4 ? (
              <label>
                Filtrar actividades
                <input
                  value={filtroActividad}
                  onChange={(e) => setFiltroActividad(e.target.value)}
                  placeholder="Escriba el nombre de la actividad"
                />
              </label>
            ) : null}
            <div className="activity-strip">
              {actividadesVisibles.map((item) => (
                <button
                  type="button"
                  key={item.id}
                  className={actividad === item.id ? "activity-card on" : "activity-card"}
                  onClick={() => {
                    setActividad(item.id);
                    setFamilia(null);
                    setPersonaId("");
                    setPersonaNombre("");
                    setPadrino("");
                    setFiltroEstado("faltan");
                  }}
                >
                  <div className="card-top">
                    <strong>{item.nombre}</strong>
                    <span className={`badge ${item.estado}`}>{item.estado}</span>
                  </div>
                  <div className="muted">{cop(item.total_recaudado)} recaudado</div>
                  <div className="muted">{item.cantidad_recaudos || 0} pagos</div>
                  {actividad === item.id ? <span className="badge activo">Seleccionada</span> : null}
                </button>
              ))}
            </div>
            {coincidenciasActividad > actividadesVisibles.length ? (
              <p className="muted">
                Mostrando {actividadesVisibles.length} de {coincidenciasActividad}. Escriba más letras del nombre.
              </p>
            ) : null}
          </>
        )}
        {!actividades.length ? (
          <p className="muted">
            No hay actividades abiertas. <Link to="/actividades/nueva">Cree una actividad</Link> para recaudar.
          </p>
        ) : muchasActividades ? null : !actividadesVisibles.length ? (
          <p className="muted">Ninguna actividad coincide con el filtro.</p>
        ) : null}
        {actividadActual ? (
          <div className="activity-card on" style={{ minHeight: 0, cursor: "default" }}>
            <div className="kicker">Esta es la actividad del recaudo</div>
            <strong>{actividadActual.nombre}</strong>
            <div className="muted">
              {valorOk
                ? `Este pago suma ${cop(valorOk)} y el total quedaría en ${cop(nuevoTotal)}`
                : `Va ${cop(actividadActual.total_recaudado)} · ${actividadActual.cantidad_recaudos || 0} pagos`}
            </div>
          </div>
        ) : (
          <p className="muted">Seleccione una actividad para continuar. Hasta no elegirla no se registra el pago.</p>
        )}
      </section>

      <div className="context-banner">
        <div>
          <div className="kicker">Se registra en</div>
          <strong>{actividadActual?.nombre || "Elija la actividad"}</strong>
          <div className="muted">Actividad del recaudo</div>
        </div>
        <div>
          <div className="kicker">Quién realiza el pago</div>
          <strong>
            {esGeneral ? personaNombre || "Elija la persona" : familia?.nombre || "Elija la familia"}
          </strong>
          <div className="muted">
            {esGeneral
              ? "Persona de la actividad"
              : familia?.telefono
                ? `Celular ${familia.telefono}`
                : "Familia aportante"}
          </div>
        </div>
        {!esGeneral ? (
          <div>
            <div className="kicker">A quién se evidencia</div>
            <strong>{padrinoActual?.nombre_completo || "Elija el padrino"}</strong>
            <div className="muted">Padrino que recibe</div>
          </div>
        ) : null}
      </div>

      {error ? <div className="error">{error}</div> : null}

      <section className="form-card">
        <div className="form-step">
          <span className="step-num">2</span>
          <div>
            <h2>¿Quién paga?</h2>
            <p className="muted">
              {control
                ? `${control.etiqueta_periodo}. Toque ${esGeneral ? "la persona" : "la familia"}. Quien ya pagó se marca.`
                : "Primero elija la actividad."}
            </p>
          </div>
        </div>

        {!actividad ? (
          <p className="muted">Elija la actividad arriba para ver quiénes faltan por pagar.</p>
        ) : cargandoControl ? (
          <p className="muted">Cargando participantes…</p>
        ) : (
          <>
            <div className="choice-row" role="group" aria-label="Filtrar">
              <button
                type="button"
                className={`choice-btn ${filtroEstado === "faltan" ? "on" : ""}`}
                onClick={() => setFiltroEstado("faltan")}
              >
                Faltan ({control?.cantidad_faltan ?? 0})
              </button>
              <button
                type="button"
                className={`choice-btn ${filtroEstado === "pagaron" ? "on" : ""}`}
                onClick={() => setFiltroEstado("pagaron")}
              >
                Ya pagaron ({control?.cantidad_pagaron ?? 0})
              </button>
              <button
                type="button"
                className={`choice-btn ${filtroEstado === "todas" ? "on" : ""}`}
                onClick={() => setFiltroEstado("todas")}
              >
                Todas (
                {esGeneral
                  ? (control?.cantidad_personas ?? control?.cantidad_familias ?? 0)
                  : (control?.cantidad_familias ?? 0)}
                )
              </button>
            </div>

            <label>
              Buscar
              <input
                placeholder={esGeneral ? "Nombre o celular" : "Nombre, padrino o celular"}
                value={qFamilia}
                onChange={(e) => setQFamilia(e.target.value)}
              />
            </label>

            {!esGeneral ? (
              <FilterSelect
                label="Filtrar por padrino (opcional)"
                value={padrino}
                placeholder="Todos los padrinos de la actividad"
                emptyLabel="Todos los padrinos"
                options={Array.from(
                  new Map(
                    filas
                      .filter((row) => row.padrino_id)
                      .map((row) => [
                        row.padrino_id!,
                        { value: row.padrino_id!, label: row.padrino_nombre || "" },
                      ])
                  ).values()
                )}
                onChange={(value) => {
                  setPadrino(value);
                  if (familia && value && familia.padrino !== value) setFamilia(null);
                }}
              />
            ) : null}

            {yaPagoSeleccionado ? (
              <div className="warn-banner">
                <strong>{esGeneral ? personaNombre : familia?.nombre}</strong> ya pagó{" "}
                {control?.etiqueta_periodo.toLowerCase() || "en este período"}. Si continúa, se registrará{" "}
                <strong>otro pago</strong> (posible duplicado).
              </div>
            ) : null}

            <div className="pick-list">
              {filasVisibles.map((row) => {
                const selected = esGeneral
                  ? personaId === row.persona_id
                  : familia?.id === row.familia_id;
                return (
                  <button
                    type="button"
                    key={row.key}
                    className={selected ? "pick-item on" : "pick-item"}
                    onClick={() => elegirParticipante(row)}
                  >
                    <div>
                      <strong>{row.nombre}</strong>
                      <div className="muted">
                        {row.padrino_nombre || ""}
                        {row.telefono ? `${row.padrino_nombre ? " · " : ""}${row.telefono}` : ""}
                      </div>
                    </div>
                    {row.ya_pago ? (
                      <span className="badge confirmado">Ya pagó</span>
                    ) : selected ? (
                      <span className="badge activo">Paga ahora</span>
                    ) : (
                      <span className="badge warning">Falta</span>
                    )}
                  </button>
                );
              })}
            </div>

            {!filas.length ? (
              <p className="muted">
                Esta actividad aún no tiene {esGeneral ? "personas" : "familias"}. Agréguelas abajo o en{" "}
                <Link to={`/actividades/${actividad}`}>la actividad</Link>.
              </p>
            ) : !filasVisibles.length ? (
              <p className="muted">
                {filtroEstado === "faltan"
                  ? "Nadie falta por pagar en este tramo. Cambie a “Ya pagaron” o “Todas” si necesita otro pago."
                  : "Nadie coincide con el filtro."}
              </p>
            ) : null}

            {crearFamilia ? (
              <div className="note" style={{ display: "grid", gap: 10 }}>
                <strong>{esGeneral ? "Agregar persona" : "Agregar familia a esta actividad"}</strong>
                {errorFamilia ? <div className="error">{errorFamilia}</div> : null}
                <label>
                  Nombre
                  <input
                    value={nuevaFamilia.nombre}
                    onChange={(e) => setNuevaFamilia({ ...nuevaFamilia, nombre: e.target.value })}
                    placeholder={esGeneral ? "Nombre de la persona" : "Apellido o identificación"}
                  />
                </label>
                <label>
                  Celular (opcional)
                  <input
                    inputMode="tel"
                    placeholder="3001234567"
                    value={nuevaFamilia.telefono}
                    onChange={(e) => setNuevaFamilia({ ...nuevaFamilia, telefono: e.target.value })}
                  />
                </label>
                {!esGeneral ? (
                  <label>
                    Padrino
                    <select
                      value={nuevaFamilia.padrino || padrino || padrinos[0]?.id || ""}
                      onChange={(e) => setNuevaFamilia({ ...nuevaFamilia, padrino: e.target.value })}
                    >
                      {padrinos.map((p) => (
                        <option key={p.id} value={p.id}>
                          {p.nombre_completo}
                        </option>
                      ))}
                    </select>
                  </label>
                ) : null}
                <div className="actions">
                  <button
                    type="button"
                    className="btn"
                    disabled={guardandoFamilia}
                    onClick={async () => {
                      setErrorFamilia("");
                      if (!nuevaFamilia.nombre.trim()) {
                        setErrorFamilia("Escriba el nombre.");
                        return;
                      }
                      if (!actividad) {
                        setErrorFamilia("Elija primero la actividad.");
                        return;
                      }
                      setGuardandoFamilia(true);
                      try {
                        const act = await api<Actividad>(`/api/actividades/${actividad}/`);
                        if (esGeneral || act.tipo === "general") {
                          const personas_data = [
                            ...(act.personas || []).map((p) => ({
                              id: p.id,
                              nombre: p.nombre,
                              telefono: p.telefono || "",
                            })),
                            {
                              nombre: nuevaFamilia.nombre.trim(),
                              telefono: nuevaFamilia.telefono.trim(),
                            },
                          ];
                          const actualizada = await api<Actividad>(`/api/actividades/${actividad}/`, {
                            method: "PUT",
                            body: JSON.stringify({
                              nombre: act.nombre,
                              descripcion: act.descripcion || "",
                              fecha_inicio: act.fecha_inicio,
                              fecha_fin: act.fecha_fin,
                              estado: act.estado,
                              tipo: "general",
                              cobro_cada: act.cobro_cada || "una_vez",
                              personas_data,
                              familias: [],
                            }),
                          });
                          const creada = (actualizada.personas || []).find(
                            (p) =>
                              p.nombre === nuevaFamilia.nombre.trim() &&
                              (p.telefono || "") === nuevaFamilia.telefono.trim()
                          );
                          if (creada) {
                            setPersonaId(creada.id);
                            setPersonaNombre(creada.nombre);
                          }
                        } else {
                          const padrinoId = nuevaFamilia.padrino || padrino || padrinos[0]?.id || "";
                          if (!padrinoId) {
                            setErrorFamilia("Elija el padrino.");
                            return;
                          }
                          const creada = await api<Familia>("/api/familias/", {
                            method: "POST",
                            body: JSON.stringify({
                              nombre: nuevaFamilia.nombre.trim(),
                              telefono: nuevaFamilia.telefono.trim(),
                              padrino: padrinoId,
                            }),
                          });
                          const ids = [
                            ...(act.participantes || []).map((p) => p.familia),
                            creada.id,
                          ];
                          await api(`/api/actividades/${actividad}/`, {
                            method: "PUT",
                            body: JSON.stringify({
                              nombre: act.nombre,
                              descripcion: act.descripcion || "",
                              fecha_inicio: act.fecha_inicio,
                              fecha_fin: act.fecha_fin,
                              estado: act.estado,
                              tipo: act.tipo || "apadrinamiento",
                              cobro_cada: act.cobro_cada || "mes",
                              familias: ids,
                              personas_data: [],
                            }),
                          });
                          setFamilia(creada);
                          setPadrino(creada.padrino);
                        }
                        setFiltroEstado("faltan");
                        await loadControl(actividad, fecha);
                        setCrearFamilia(false);
                        setNuevaFamilia({ nombre: "", telefono: "", padrino: "" });
                      } catch (err) {
                        setErrorFamilia(err instanceof ApiError ? err.message : "No se pudo guardar.");
                      } finally {
                        setGuardandoFamilia(false);
                      }
                    }}
                  >
                    {guardandoFamilia ? "Guardando…" : "Guardar y usar"}
                  </button>
                  <button
                    type="button"
                    className="btn secondary"
                    onClick={() => {
                      setCrearFamilia(false);
                      setErrorFamilia("");
                    }}
                  >
                    Cancelar
                  </button>
                </div>
              </div>
            ) : (
              <button
                type="button"
                className="btn secondary"
                onClick={() => {
                  setNuevaFamilia({ nombre: "", telefono: "", padrino: padrino || padrinos[0]?.id || "" });
                  setCrearFamilia(true);
                }}
              >
                {esGeneral ? "Agregar persona" : "Agregar familia"}
              </button>
            )}
          </>
        )}
      </section>

      <section className="form-card">
        <div className="form-step">
          <span className="step-num">3</span>
          <div>
            <h2>Valor y medio de pago</h2>
            <p className="muted">
              El monto se suma a la actividad al confirmar. El comprobante solo se pide si es transferencia.
            </p>
          </div>
        </div>
        <div className="form-grid">
          <label>
            Valor recibido (COP)
            <input
              inputMode="decimal"
              placeholder="Ej. 150000"
              value={valor}
              onChange={(e) => setValor(e.target.value)}
              required
            />
          </label>
          <label>
            Fecha
            <input type="date" value={fecha} onChange={(e) => setFecha(e.target.value)} required />
          </label>
          <div className="span-2">
            <div style={{ fontWeight: 620, marginBottom: 8, color: "var(--gray-700)", fontSize: "0.86rem" }}>
              Medio de pago
            </div>
            <div className="pay">
              <button
                type="button"
                className={medio === "efectivo" ? "on" : ""}
                onClick={() => {
                  setMedio("efectivo");
                  setFiles([]);
                  setReferencia("");
                }}
              >
                Efectivo
              </button>
              <button
                type="button"
                className={medio === "transferencia" ? "on" : ""}
                onClick={() => setMedio("transferencia")}
              >
                Transferencia
              </button>
            </div>
          </div>
          {medio === "transferencia" ? (
            <>
              <label className="span-2">
                Referencia de consignación (opcional)
                <input value={referencia} onChange={(e) => setReferencia(e.target.value)} />
              </label>
              <div className="span-2">
                <div style={{ fontWeight: 620, marginBottom: 8, color: "var(--gray-700)", fontSize: "0.86rem" }}>
                  Comprobante de la transferencia
                </div>
                <p className="muted" style={{ margin: "0 0 8px" }}>
                  Adjunte el PDF o el archivo descargado del banco, de menos de 5 MB. En el celular elija Archivos o
                  Documentos; no se abre la cámara.
                </p>
                <label className="file-input">
                  <span className="muted">Toque para adjuntar el comprobante (PDF, JPG, PNG o WebP, máx. 5 MB)</span>
                  <input
                    type="file"
                    accept="application/pdf,.pdf,image/jpeg,.jpg,.jpeg,image/png,.png,image/webp,.webp"
                    multiple
                    onChange={(e) => {
                      const next = Array.from(e.target.files || []);
                      const pesado = next.find((file) => file.size > MAX_SOPORTE_BYTES);
                      if (pesado) {
                        setError(`"${pesado.name}" pesa más de 5 MB. Use un archivo más liviano.`);
                        e.target.value = "";
                        setFiles([]);
                        return;
                      }
                      setError("");
                      setFiles(next);
                    }}
                  />
                  {files.length ? (
                    <strong>
                      {files.length} archivo(s): {files.map((file) => file.name).join(", ")}
                    </strong>
                  ) : id && soportesExistentes ? (
                    <span className="muted">Ya hay {soportesExistentes} comprobante(s). Adjunte otros solo si desea reemplazarlos.</span>
                  ) : null}
                </label>
              </div>
            </>
          ) : (
            <p className="muted span-2">
              En efectivo no se pide soporte. Confirme el valor y emita el recibo.
            </p>
          )}
          <label className="span-2">
            Nota (opcional)
            <input value={concepto} onChange={(e) => setConcepto(e.target.value)} />
          </label>
        </div>
      </section>

      <section className="form-card submit-card">
        <div className="kicker">Listo para confirmar</div>
        <p className="muted" style={{ margin: 0 }}>
          {actividadActual?.nombre || "Falta actividad"} ·{" "}
          {esGeneral ? personaNombre || "Falta persona" : familia?.nombre || "Falta familia"}
          {!esGeneral ? ` → ${padrinoActual?.nombre_completo || "Falta padrino"}` : ""}
        </p>
        <strong style={{ fontSize: "1.25rem" }}>{valorOk ? cop(valorOk) : "Sin valor"}</strong>
        <button className="btn gold block" disabled={busy} type="submit">
          {id ? "Revisar y guardar cambios" : "Revisar y confirmar"}
        </button>
      </section>

      {confirmar && actividad && (esGeneral ? personaId : familia && padrino) ? (
        <div
          className="sheet-backdrop"
          role="dialog"
          aria-modal="true"
          aria-labelledby="confirm-title"
          onClick={() => !busy && setConfirmar(false)}
        >
          <div className="sheet" onClick={(event) => event.stopPropagation()}>
            <div className="sheet-handle" />
            <div className="eyebrow">Confirme antes de guardar</div>
            <h2 id="confirm-title">{id ? "¿Guardar los cambios de este pago?" : "¿Registrar este pago?"}</h2>
            <p className="muted">Revise en qué actividad queda y quién paga.</p>
            {yaPagoSeleccionado ? (
              <div className="warn-banner">
                Ya hay un pago {control?.etiqueta_periodo.toLowerCase() || "en este período"}. Confirme solo si
                realmente debe registrar <strong>otro</strong> pago.
              </div>
            ) : null}
            <div className="confirm-rows">
              <div className="confirm-row">
                <div className="kicker">Se registra en la actividad</div>
                <strong>{actividadActual?.nombre || "Actividad"}</strong>
                <div className="muted">
                  Hoy va {cop(actividadActual?.total_recaudado)} · con este pago quedará {cop(nuevoTotal)}
                </div>
              </div>
              <div className="confirm-row">
                <div className="kicker">Quién realiza el pago</div>
                <strong>{esGeneral ? personaNombre : familia?.nombre}</strong>
                <div className="muted">
                  {fecha} · {medio === "efectivo" ? "Efectivo" : "Transferencia"}
                  {yaPagoSeleccionado ? " · ya tenía pago en este tramo" : ""}
                </div>
              </div>
              {!esGeneral ? (
                <div className="confirm-row">
                  <div className="kicker">A quién se evidencia</div>
                  <strong>{padrinoActual?.nombre_completo || familia?.padrino_nombre}</strong>
                  <div className="muted">Padrino. El recibo sale a nombre de la familia.</div>
                </div>
              ) : null}
              <div className="confirm-row">
                <div className="kicker">Valor a registrar</div>
                <strong>{cop(valorOk)}</strong>
                <div className="muted">
                  {medio === "transferencia"
                    ? files.length
                      ? `${files.length} comprobante(s) adjunto(s)`
                      : "Falta el comprobante de la transferencia"
                    : "Efectivo · sin soporte"}
                  {concepto ? ` · ${concepto}` : ""}
                </div>
              </div>
            </div>
            <div className="actions">
              <button type="button" className="btn gold" disabled={busy} onClick={() => void guardar()}>
                {busy
                  ? "Guardando…"
                  : id
                    ? "Sí, guardar cambios"
                    : yaPagoSeleccionado
                      ? "Sí, registrar otro pago"
                      : "Sí, confirmar y emitir recibo"}
              </button>
              <button type="button" className="btn secondary" disabled={busy} onClick={() => setConfirmar(false)}>
                Volver a editar
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </form>
  );
}
