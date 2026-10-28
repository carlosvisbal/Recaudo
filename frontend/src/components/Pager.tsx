export function Pager({
  page,
  pages,
  count,
  onChange,
  label = "registros",
}: {
  page: number;
  pages: number;
  count: number;
  onChange: (page: number) => void;
  label?: string;
}) {
  if (count === 0) return null;
  return (
    <div className="pager">
      <span className="muted">
        {count} {label} · página {page} de {Math.max(pages, 1)}
      </span>
      {pages > 1 ? (
        <div className="pager-actions">
          <button type="button" className="btn secondary" disabled={page <= 1} onClick={() => onChange(page - 1)}>
            Anterior
          </button>
          <button
            type="button"
            className="btn secondary"
            disabled={page >= pages}
            onClick={() => onChange(page + 1)}
          >
            Siguiente
          </button>
        </div>
      ) : null}
    </div>
  );
}

export function slicePage<T>(items: T[], page: number, size = 20): { pageItems: T[]; pages: number } {
  const pages = Math.max(1, Math.ceil(items.length / size));
  const current = Math.min(Math.max(page, 1), pages);
  const start = (current - 1) * size;
  return { pageItems: items.slice(start, start + size), pages };
}