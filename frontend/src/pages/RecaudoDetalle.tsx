import { useEffect, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { api, ApiError, type Compartir, type Recaudo } from "../api";
import { useConfirm } from "../components/ConfirmDialog";

export function RecaudoDetalle() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [item, setItem] = useState<Recaudo | null>(null);
  const [share, setShare] = useState<Compartir | null>(null);
  const [telefono, setTelefono] = useState("");
  const [motivo, setMotivo] = useState("");
  const [mensaje, setMensaje] = useState("");
  const [error, setError] = useState("");
  const { ask, dialog } = useConfirm();

  const load = async () => {
    if (!id) return;
    const recaudo = await api<Recaudo>(`/api/recaudos/${id}/`);
    setItem(recaudo);
    const compartir = await api<Compartir>(`/api/recaudos/${id}/compartir/`);
    setShare(compartir);
    setTelefono(recaudo.familia_telefono || "");
  };

  useEffect(() => {
    void load();
  }, [id]);

  if (!item) return <p>Cargando recibo…</p>;
  const recaudo = item;
  const pdfUrl = `/api/recaudos/${recaudo.id}/recibo/`;
  const pdfDownload = `${pdfUrl}?descargar=1`;
  const seguirSumando = `/recaudos/nuevo?actividad=${recaudo.actividad}&padrino=${recaudo.padrino}${
    recaudo.familia ? `&familia=${recaudo.familia}` : ""
  }`;

  async function pdfFile() {
    const response = await fetch(pdfDownload, { credentials: "include" });
    const blob = await response.blob();
    return new File([blob], `recibo-${recaudo.numero_formateado}.pdf`, { type: "application/pdf" });
  }

  async function enviarWhatsAppFamilia() {
    setError("");
    setMensaje("");
    let actual = share;
    if (recaudo.familia && !actual?.tiene_telefono_familia) {
      if (telefono.replace(/\D/g, "").length < 10) {
        setError("Escriba el celular de la familia (10 dígitos) para abrir su WhatsApp.");
        return;
      }
      actual = await api<Compartir>(`/api/recaudos/${recaudo.id}/telefono-familia/`, {
        method: "POST",
        body: JSON.stringify({ telefono }),
      });
      setShare(actual);
    }
    const file = await pdfFile();
    if (navigator.share && navigator.canShare?.({ files: [file] })) {
      await navigator.share({
        title: `Recibo ${recaudo.numero_formateado}`,
        text: actual?.mensaje,
        files: [file],
      });
      setMensaje(
        "Se abrió Compartir. Elija WhatsApp para mandar el PDF a la familia. El mensaje no se envía solo."
      );
      return;
    }
    window.open(actual?.whatsapp_url_destino || actual?.whatsapp_url, "_blank", "noopener");
    setMensaje(
      "Se abrió el chat de WhatsApp de la familia con el texto del recibo. Adjunte el PDF descargado con el clip."
    );
  }

  async function llevarAOtroLado() {
    setError("");
    const file = await pdfFile();
    if (navigator.share && navigator.canShare?.({ files: [file] })) {
      await navigator.share({
        title: `Recibo ${recaudo.numero_formateado}`,
        text: share?.mensaje,
        files: [file],
      });
      setMensaje("Elija WhatsApp, Drive, correo o archivos. El envío lo confirma usted en esa aplicación.");
      return;
    }
    window.location.href = pdfDownload;
    setMensaje("Se descargó el PDF. Desde ahí puede enviarlo o guardarlo donde decida.");
  }

  return (
    <div className="form">
      {params.get("nuevo") ? (
        <div className="note">
          Pago confirmado. Quedó en <strong>{item.actividad_nombre}</strong>, lo realizó{" "}
          <strong>{item.familia_nombre || item.aportante_nombre}</strong> y se evidenció a{" "}
          <strong>{item.padrino_nombre}</strong>. Envíe el recibo a la familia.
        </div>
      ) : null}
      {item.estado === "anulado" ? (
        <div className="error">Recibo anulado. El número {item.numero_formateado} no se reutiliza.</div>
      ) : null}
      <div className="eyebrow">Recibo de caja</div>
      <h1>N.º {item.numero_formateado}</h1>
      <div className="context-banner">
        <div>
          <div className="kicker">Registrado en</div>
          <strong>{item.actividad_nombre}</strong>
          <div className="muted">
            {item.fecha} · {item.medio_pago_display}
          </div>
        </div>
        <div>
          <div className="kicker">Quién realizó el pago</div>
          <strong>{item.familia_nombre || item.aportante_nombre}</strong>
          <div className="muted">Familia aportante</div>
        </div>
        <div>
          <div className="kicker">A quién se evidenció</div>
          <strong>{item.padrino_nombre}</strong>
          <div className="muted">Padrino que recibe</div>
        </div>
      </div>
      <div className="card">
        <div className="kpi">{item.valor_formato}</div>
        <div className="muted">{item.valor_en_letras}</div>
      </div>

      {error ? <div className="error">{error}</div> : null}
      {mensaje ? <div className="note">{mensaje}</div> : null}

      {item.estado === "confirmado" ? (
        <div className="card">
          <strong>Enviar recibo a la familia por WhatsApp</strong>
          <p className="muted">{share?.aviso_whatsapp}</p>
          {share?.tiene_telefono_familia ? (
            <p>
              Celular guardado: <strong>{share.telefono_destino}</strong>
            </p>
          ) : recaudo.familia ? (
            <label>
              Celular de {share?.familia_nombre || "la familia"}
              <input
                inputMode="tel"
                placeholder="3001234567"
                value={telefono}
                onChange={(e) => setTelefono(e.target.value)}
              />
            </label>
          ) : (
            <p className="muted">Este pago no tiene familia. Use “Llevar a otro lado” o descargue el PDF.</p>
          )}
          <button className="btn whatsapp block" type="button" onClick={() => void enviarWhatsAppFamilia()}>
            Enviar recibo por WhatsApp
          </button>
        </div>
      ) : null}

      <h2>Llevar el recibo o el soporte a otro lado</h2>
      <p className="muted">Descargue o use Compartir para escoger WhatsApp, Drive, correo o el teléfono.</p>
      <div className="share-grid">
        <button className="btn gold" type="button" onClick={() => void llevarAOtroLado()}>
          Compartir / exportar
        </button>
        <a className="btn" href={pdfDownload}>
          Descargar PDF
        </a>
        <button
          className="btn secondary"
          type="button"
          onClick={() => window.open(pdfUrl, "_blank", "noopener")}
        >
          Imprimir
        </button>
        <Link className="btn secondary" to={seguirSumando}>
          Registrar otro pago
        </Link>
        {item.estado === "confirmado" ? (
          <Link className="btn secondary" to={`/recaudos/${item.id}/editar`}>
            Editar pago
          </Link>
        ) : null}
        <button
          className="btn danger"
          type="button"
          onClick={() =>
            ask({
              title: "Eliminar pago",
              message: `¿Eliminar el recibo ${item.numero_formateado}? Se borra el PDF y los soportes. El número no se reutiliza.`,
              confirmLabel: "Sí, eliminar",
              danger: true,
              action: async () => {
                setError("");
                try {
                  await api(`/api/recaudos/${item.id}/`, { method: "DELETE" });
                  navigate("/pagos");
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
      </div>

      <h2>Soportes del pago</h2>
      {item.soportes?.length ? (
        <div className="list">
          {item.soportes.map((s) => (
            <a
              className="list-item"
              key={s.id}
              href={`/api/recaudos/${item.id}/soportes/${s.id}/`}
              target="_blank"
              rel="noreferrer"
            >
              {s.nombre_original}
            </a>
          ))}
        </div>
      ) : (
        <p className="muted">
          {item.medio_pago === "efectivo"
            ? "Pago en efectivo: no lleva comprobante adjunto."
            : "Este pago no tiene comprobante adjunto."}
        </p>
      )}

      {item.estado === "confirmado" ? (
        <div>
          <h2>Anular pago</h2>
          <p className="muted">No se borra ni se reutiliza el número. Sale de la sumatoria.</p>
          <label>
            Motivo
            <textarea value={motivo} onChange={(e) => setMotivo(e.target.value)} />
          </label>
          <button
            type="button"
            className="btn danger"
            onClick={() =>
              ask({
                title: "Anular pago",
                message: `¿Anular el recibo ${item.numero_formateado}? Sale de la sumatoria y el número no se reutiliza.`,
                confirmLabel: "Sí, anular",
                danger: true,
                action: async () => {
                  setError("");
                  try {
                    await api(`/api/recaudos/${item.id}/anular/`, {
                      method: "POST",
                      body: JSON.stringify({ motivo }),
                    });
                    await load();
                  } catch (err) {
                    setError(err instanceof ApiError ? err.message : "No se pudo anular.");
                    throw err;
                  }
                },
              })
            }
          >
            Anular
          </button>
        </div>
      ) : null}
      {dialog}
    </div>
  );
}
