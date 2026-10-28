import { useState, type ReactNode } from "react";
import { createPortal } from "react-dom";

type ConfirmDialogProps = {
  open: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  danger?: boolean;
  busy?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
};

export function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel = "Sí, confirmar",
  cancelLabel = "Cancelar",
  danger = false,
  busy = false,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  if (!open || typeof document === "undefined") return null;
  return createPortal(
    <div
      className="sheet-backdrop confirm-backdrop"
      role="dialog"
      aria-modal="true"
      aria-labelledby="confirm-dialog-title"
      onClick={() => {
        if (!busy) onCancel();
      }}
    >
      <div className="sheet confirm-sheet" onClick={(event) => event.stopPropagation()}>
        <div className="sheet-handle" />
        <h2 id="confirm-dialog-title">{title}</h2>
        <p className="muted">{message}</p>
        <div className="actions">
          <button
            type="button"
            className={danger ? "btn danger" : "btn gold"}
            disabled={busy}
            onClick={onConfirm}
          >
            {busy ? "Procesando…" : confirmLabel}
          </button>
          <button type="button" className="btn secondary" disabled={busy} onClick={onCancel}>
            {cancelLabel}
          </button>
        </div>
      </div>
    </div>,
    document.body,
  );
}

type AskOptions = {
  title: string;
  message: string;
  confirmLabel?: string;
  danger?: boolean;
  action: () => Promise<void> | void;
};

export function useConfirm(): { ask: (opts: AskOptions) => void; dialog: ReactNode } {
  const [opts, setOpts] = useState<AskOptions | null>(null);
  const [busy, setBusy] = useState(false);

  return {
    ask: (next) => setOpts(next),
    dialog: (
      <ConfirmDialog
        open={Boolean(opts)}
        title={opts?.title || ""}
        message={opts?.message || ""}
        confirmLabel={opts?.confirmLabel}
        danger={opts?.danger}
        busy={busy}
        onCancel={() => {
          if (!busy) setOpts(null);
        }}
        onConfirm={async () => {
          if (!opts) return;
          setBusy(true);
          try {
            await opts.action();
            setOpts(null);
          } finally {
            setBusy(false);
          }
        }}
      />
    ),
  };
}
