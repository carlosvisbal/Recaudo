import { useEffect, useMemo, useRef, useState } from "react";

export type FilterOption = {
  value: string;
  label: string;
  hint?: string;
};

type Props = {
  label: string;
  value: string;
  options: FilterOption[];
  onChange: (value: string) => void;
  placeholder?: string;
  emptyLabel?: string;
  searchPlaceholder?: string;
  disabled?: boolean;
  required?: boolean;
  className?: string;
  maxVisible?: number;
  onSearch?: (term: string) => void;
};

export function FilterSelect({
  label,
  value,
  options,
  onChange,
  placeholder = "Escriba para filtrar…",
  emptyLabel,
  searchPlaceholder,
  disabled,
  required,
  className,
  maxVisible = 12,
  onSearch,
}: Props) {
  const [open, setOpen] = useState(false);
  const [term, setTerm] = useState("");
  const wrap = useRef<HTMLDivElement>(null);
  const selected = options.find((item) => item.value === value);

  const filtered = useMemo(() => {
    const q = term.trim().toLowerCase();
    if (!q) return options;
    return options.filter(
      (item) => item.label.toLowerCase().includes(q) || (item.hint || "").toLowerCase().includes(q)
    );
  }, [options, term]);
  const visible = filtered.slice(0, maxVisible);
  const hiddenCount = Math.max(0, filtered.length - visible.length);

  useEffect(() => {
    const close = (event: MouseEvent) => {
      if (!wrap.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);

  useEffect(() => {
    if (!onSearch || !open) return;
    const handle = window.setTimeout(() => onSearch(term), 180);
    return () => window.clearTimeout(handle);
  }, [term, open, onSearch]);

  function choose(next: string) {
    onChange(next);
    setTerm("");
    setOpen(false);
  }

  return (
    <div className={`field ${className || ""}`} ref={wrap}>
      <span className="field-label">
        {label}
        {required ? " *" : ""}
      </span>
      <div className={`combo ${open ? "open" : ""} ${disabled ? "disabled" : ""}`}>
        <input
          value={open ? term : selected?.label || ""}
          placeholder={searchPlaceholder || placeholder}
          disabled={disabled}
          autoComplete="off"
          onFocus={() => {
            if (disabled) return;
            setOpen(true);
            setTerm("");
          }}
          onChange={(event) => {
            setTerm(event.target.value);
            setOpen(true);
          }}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              event.preventDefault();
              if (filtered[0]) choose(filtered[0].value);
            }
            if (event.key === "Escape") setOpen(false);
          }}
        />
        {open ? (
          <div className="combo-list" role="listbox">
            {emptyLabel ? (
              <button type="button" className={!value ? "on" : ""} onClick={() => choose("")}>
                {emptyLabel}
              </button>
            ) : null}
            {visible.map((item) => (
              <button
                type="button"
                key={item.value}
                className={item.value === value ? "on" : ""}
                onClick={() => choose(item.value)}
              >
                <strong>{item.label}</strong>
                {item.hint ? <div className="muted">{item.hint}</div> : null}
              </button>
            ))}
            {hiddenCount ? (
              <div className="combo-empty">
                {hiddenCount} más. Escriba el nombre para acotar la lista ({filtered.length} en total).
              </div>
            ) : null}
            {!filtered.length ? <div className="combo-empty">Sin coincidencias</div> : null}
          </div>
        ) : null}
      </div>
    </div>
  );
}
