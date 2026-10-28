import { Link } from "react-router-dom";
import { useState } from "react";
import { ConfirmDialog } from "./ConfirmDialog";

type Props = {
  editTo?: string;
  onDelete?: () => Promise<void> | void;
  confirmText: string;
};

export function RowActions({ editTo, onDelete, confirmText }: Props) {
  const [ask, setAsk] = useState(false);
  const [busy, setBusy] = useState(false);

  return (
    <div
      className="row-actions"
      onClick={(event) => {
        event.preventDefault();
        event.stopPropagation();
      }}
    >
      {editTo ? (
        <Link className="btn secondary sm" to={editTo}>
          Editar
        </Link>
      ) : null}
      {onDelete ? (
        <button
          type="button"
          className="btn danger sm"
          disabled={busy}
          onClick={(event) => {
            event.preventDefault();
            event.stopPropagation();
            setAsk(true);
          }}
        >
          Eliminar
        </button>
      ) : null}
      <ConfirmDialog
        open={ask}
        title="Confirmar eliminación"
        message={confirmText}
        confirmLabel="Sí, eliminar"
        danger
        busy={busy}
        onCancel={() => {
          if (!busy) setAsk(false);
        }}
        onConfirm={async () => {
          if (!onDelete) return;
          setBusy(true);
          try {
            await onDelete();
            setAsk(false);
          } finally {
            setBusy(false);
          }
        }}
      />
    </div>
  );
}
