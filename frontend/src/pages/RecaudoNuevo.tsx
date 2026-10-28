import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { api, ApiError, cop, parsePage, type Actividad, type Familia, type Padrino, type Recaudo } from "../api";
import { FilterSelect } from "../components/FilterSelect";
import { Pager } from "../components/Pager";

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
  const [familiasPadrino, setFamiliasPadrino] = useState<Familia[]>([]);
  const [cargandoFamilias, setCargandoFamilias] = useState(false);
  const [paginaFamilia, setPaginaFamilia] = useState(1);
  const [pagesFamilia, setPagesFamilia] = useState(1);
  const [countFamilia, setCountFamilia] = useState(0);
  const [qFamilia, setQFamilia] = useState("");
  const [familia, setFamilia] = useState<Familia | null>(null);
  const [actividades, setActividades] = useState<Actividad[]>([]);
  const [filtroActividad, setFiltroActividad] = useState("");
  const [padrinos, setPadrinos] = useState<Padrino[]>([]);
  const [actividad, setActividad] = useState(params.get("actividad") || "");
  const [padrino, setPadrino] = useState(params.get("padrino") || "");
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
  const [nuevaFamilia, setNuevaFamilia] = useState({ nombre: "", telefono: "" });
  const [guardandoFamilia, setGuardandoFamilia] = useState(false);
  const [errorFamilia, setErrorFamilia] = useState("");

  const loadActividades = useCallback(async (term = "") => {
    const params = new URLSearchParams({ page: "1" });
    if (term.trim()) params.set("q", term.trim());
    const data = parsePage<Actividad>(await api(`/api/actividades/?${params}`));
    setActividades(data.results.filter((a) => a.estado !== "cerrada"));
  }, []);

  const loadPadrinos = useCallback(async (term = "") => {
    const params = new URLSearchParams({ estado: "activo", page: "1" });
    if (term.trim()) params.set("q", term.trim());
    setPadrinos(parsePage<Padrino>(await api(`/api/padrinos/?${params}`)).results);
  }, []);

  const loadFamilias = useCallback(async (padrinoId: string, term = "", pagina = 1) => {
    const params = new URLSearchParams({
      padrino: padrinoId,
      estado: "activo",
      page: String(pagina),
    });
    if (term.trim()) params.set("q", term.trim());
    const data = parsePage<Familia>(await api(`/api/familias/?${params}`));
    setFamiliasPadrino(data.results);
    setPagesFamilia(data.pages);
    setCountFamilia(data.count);
    setPaginaFamilia(data.page);
    setCargandoFamilias(false);
    setFamilia((actual) => {
      if (!actual) return null;
      if (data.results.some((item) => item.id === actual.id)) return actual;
      return actual.padrino === padrinoId ? actual : null;
    });
  }, []);

  useEffect(() => {
    void loadActividades();
    void loadPadrinos();
  }, []);

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
              },
              ...actual,
            ]
      );
      setPadrinos((actual) =>
        actual.some((p) => p.id === item.padrino)
          ? actual
          : [
              {
                id: item.padrino,
                nombre_completo: item.padrino_nombre,
                telefono: "",
                correo: "",
                estado: "activo",
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
    if (!familiaId) return;
    void api<Familia>(`/api/familias/${familiaId}/`).then((item) => {
      setFamilia(item);
      setPadrino(item.padrino);
      setPadrinos((actual) =>
        actual.some((p) => p.id === item.padrino)
          ? actual
          : [
              {
                id: item.padrino,
                nombre_completo: item.padrino_nombre,
                telefono: item.telefono || "",
                correo: "",
                estado: "activo",
              },
              ...actual,
            ]
      );
    });
    const actId = params.get("actividad");
    if (actId) {
      void api<Actividad>(`/api/actividades/${actId}/`).then((item) => {
        setActividad(item.id);
        setActividades((actual) => (actual.some((a) => a.id === item.id) ? actual : [item, ...actual]));
      });
    }
  }, [params]);

  useEffect(() => {
    if (!padrino) {
      setFamiliasPadrino([]);
      setCargandoFamilias(false);
      setCountFamilia(0);
      return;
    }
    setCargandoFamilias(true);
    setQFamilia("");
    void loadFamilias(padrino, "", 1);
  }, [padrino]);

  const valorOk = useMemo(() => parseValor(valor), [valor]);
  const actividadActual =
    actividades.find((a) => a.id === actividad) ||
    (actividad ? ({ id: actividad, nombre: "Actividad seleccionada" } as Actividad) : undefined);
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

  function validar(): boolean {
    setError("");
    if (!actividad) {
      setError("Seleccione arriba la actividad en la que registra este recaudo.");
      return false;
    }
    if (!padrino) {
      setError("Elija el padrino a quien se evidencia el pago.");
      return false;
    }
    if (!familia) {
      setError("Elija la familia que está realizando el pago.");
      return false;
    }
    if (!valorOk) {
      setError("Indique el valor recibido.");
      return false;
    }
    if (medio === "transferencia" && files.length === 0 && !soportesExistentes) {
      setError("Adjunte el comprobante de la transferencia (archivo PDF o imagen, no una foto de la cámara).");
      return false;
    }
    return true;
  }

  async function guardar() {
    if (!familia || !valorOk) return;
    setBusy(true);
    setError("");
    try {
      const body = new FormData();
      body.append("fecha", fecha);
      body.append("actividad", actividad);
      body.append("padrino", padrino);
      body.append("familia", familia.id);
      body.append("aportante_nombre", familia.nombre);
      body.append("valor", valorOk);
      body.append("medio_pago", medio);
      body.append("concepto", concepto);
      body.append("referencia_consignacion", referencia);
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
          Primero elija la actividad. Luego indique quién paga (la familia) y a quién se evidencia (el padrino). Antes
          de guardar verá una confirmación.
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
              onChange={setActividad}
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
                      onClick={() => setActividad(item.id)}
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
                  onClick={() => setActividad(item.id)}
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
          <strong>{familia?.nombre || "Elija la familia"}</strong>
          <div className="muted">{familia?.telefono ? `Celular ${familia.telefono}` : "Familia aportante"}</div>
        </div>
        <div>
          <div className="kicker">A quién se evidencia</div>
          <strong>{padrinoActual?.nombre_completo || "Elija el padrino"}</strong>
          <div className="muted">Padrino que recibe</div>
        </div>
      </div>

      {error ? <div className="error">{error}</div> : null}

      <section className="form-card">
        <div className="form-step">
          <span className="step-num">2</span>
          <div>
            <h2>¿Quién paga y a quién se evidencia?</h2>
            <p className="muted">Filtre el padrino. Solo verá las familias asignadas a él.</p>
          </div>
        </div>
        <FilterSelect
          label="Padrino a quien se evidencia (recibe el pago)"
          required
          value={padrino}
          placeholder="Escriba el nombre del padrino"
          emptyLabel="Seleccione el padrino"
          options={padrinos.map((item) => ({
            value: item.id,
            label: item.nombre_completo,
            hint:
              typeof item.familias_activas === "number"
                ? `${item.familias_activas} familia(s) asignada(s)`
                : item.telefono,
          }))}
          onSearch={(term) => void loadPadrinos(term)}
          onChange={(value) => {
            setPadrino(value);
            setFamilia(null);
            setCrearFamilia(false);
            setNuevaFamilia({ nombre: "", telefono: "" });
            setErrorFamilia("");
          }}
        />

        {!padrino ? (
          <p className="muted">Elija un padrino para listar solo las familias que tiene asignadas.</p>
        ) : cargandoFamilias ? (
          <p className="muted">Cargando familias de {padrinoActual?.nombre_completo || "este padrino"}…</p>
        ) : (
          <>
            <FilterSelect
              label="Familia que realiza el pago"
              required
              value={familia?.id || ""}
              placeholder="Escriba para filtrar las familias de este padrino"
              emptyLabel="Seleccione la familia"
              options={familiasPadrino.map((item) => ({
                value: item.id,
                label: item.nombre,
                hint: item.telefono ? `WhatsApp ${item.telefono}` : "Sin celular para el recibo",
              }))}
              onSearch={(term) => {
                setQFamilia(term);
                void loadFamilias(padrino, term, 1);
              }}
              onChange={(value) => {
                setFamilia(familiasPadrino.find((item) => item.id === value) || familia);
              }}
            />
            <div className="pick-list">
              {familiasPadrino.map((item) => (
                <button
                  type="button"
                  key={item.id}
                  className={familia?.id === item.id ? "pick-item on" : "pick-item"}
                  onClick={() => setFamilia(item)}
                >
                  <div>
                    <strong>{item.nombre}</strong>
                    <div className="muted">
                      {item.telefono ? `WhatsApp ${item.telefono}` : "Sin celular para el recibo"}
                    </div>
                  </div>
                  {familia?.id === item.id ? <span className="badge activo">Paga</span> : null}
                </button>
              ))}
            </div>
            <Pager
              page={paginaFamilia}
              pages={pagesFamilia}
              count={countFamilia}
              label="familias"
              onChange={(p) => void loadFamilias(padrino, qFamilia, p)}
            />
            {!familiasPadrino.length ? (
              <p className="muted">Este padrino no tiene familias activas. Créela aquí mismo.</p>
            ) : null}
            {crearFamilia ? (
              <div className="note" style={{ display: "grid", gap: 10 }}>
                <strong>Nueva familia de {padrinoActual?.nombre_completo}</strong>
                {errorFamilia ? <div className="error">{errorFamilia}</div> : null}
                <label>
                  Nombre de la familia
                  <input
                    value={nuevaFamilia.nombre}
                    onChange={(e) => setNuevaFamilia({ ...nuevaFamilia, nombre: e.target.value })}
                    placeholder="Apellido o identificación"
                  />
                </label>
                <label>
                  Celular para WhatsApp (opcional)
                  <input
                    inputMode="tel"
                    placeholder="3001234567"
                    value={nuevaFamilia.telefono}
                    onChange={(e) => setNuevaFamilia({ ...nuevaFamilia, telefono: e.target.value })}
                  />
                </label>
                <div className="actions">
                  <button
                    type="button"
                    className="btn"
                    disabled={guardandoFamilia}
                    onClick={async () => {
                      setErrorFamilia("");
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
                            padrino,
                          }),
                        });
                        setFamilia(creada);
                        void loadFamilias(padrino, "", 1);
                        setCrearFamilia(false);
                        setNuevaFamilia({ nombre: "", telefono: "" });
                      } catch (err) {
                        setErrorFamilia(err instanceof ApiError ? err.message : "No se pudo crear la familia.");
                      } finally {
                        setGuardandoFamilia(false);
                      }
                    }}
                  >
                    {guardandoFamilia ? "Guardando…" : "Guardar familia y usarla"}
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
              <button type="button" className="btn secondary" onClick={() => setCrearFamilia(true)}>
                Agregar familia de este padrino
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
                  Adjunte el PDF o el archivo descargado del banco. En el celular elija Archivos o Documentos; no se
                  abre la cámara.
                </p>
                <label className="file-input">
                  <span className="muted">Toque para adjuntar el comprobante (PDF, JPG, PNG o WebP)</span>
                  <input
                    type="file"
                    accept="application/pdf,.pdf,image/jpeg,.jpg,.jpeg,image/png,.png,image/webp,.webp"
                    multiple
                    onChange={(e) => setFiles(Array.from(e.target.files || []))}
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
          {actividadActual?.nombre || "Falta actividad"} · {familia?.nombre || "Falta familia"} →{" "}
          {padrinoActual?.nombre_completo || "Falta padrino"}
        </p>
        <strong style={{ fontSize: "1.25rem" }}>{valorOk ? cop(valorOk) : "Sin valor"}</strong>
        <button className="btn gold block" disabled={busy} type="submit">
          {id ? "Revisar y guardar cambios" : "Revisar y confirmar"}
        </button>
      </section>

      {confirmar && actividad && familia && padrino ? (
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
            <p className="muted">Revise en qué actividad queda, quién paga y a quién se evidencia.</p>
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
                <strong>{familia.nombre}</strong>
                <div className="muted">
                  {familia.telefono ? `Celular ${familia.telefono}` : "Sin celular guardado"} · {fecha} ·{" "}
                  {medio === "efectivo" ? "Efectivo" : "Transferencia"}
                </div>
              </div>
              <div className="confirm-row">
                <div className="kicker">A quién se evidencia</div>
                <strong>{padrinoActual?.nombre_completo || familia.padrino_nombre}</strong>
                <div className="muted">Padrino que recibe. El recibo sale a nombre de la familia.</div>
              </div>
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
                {busy ? "Guardando…" : id ? "Sí, guardar cambios" : "Sí, confirmar y emitir recibo"}
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
