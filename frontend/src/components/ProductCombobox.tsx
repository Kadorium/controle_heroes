import { useEffect, useId, useMemo, useRef, useState } from "react";
import type { Product } from "../api";

interface Props {
  products: Product[];
  value: string;
  productId: number | null;
  onChange: (next: { text: string; product: Product | null }) => void;
  placeholder?: string;
  disabled?: boolean;
}

export function ProductCombobox({
  products,
  value,
  productId,
  onChange,
  placeholder = "SKU ou descrição…",
  disabled = false,
}: Props) {
  const listId = useId();
  const wrapRef = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState(false);
  const [highlight, setHighlight] = useState(0);

  const filtered = useMemo(() => {
    const q = value.trim().toLowerCase();
    if (!q) return products.slice(0, 12);
    return products
      .filter(
        (p) =>
          p.sku_code.toLowerCase().includes(q) ||
          p.description.toLowerCase().includes(q),
      )
      .slice(0, 12);
  }, [products, value]);

  useEffect(() => {
    setHighlight(0);
  }, [value, open]);

  useEffect(() => {
    function onDocClick(e: MouseEvent) {
      if (!wrapRef.current?.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, []);

  function selectProduct(p: Product) {
    onChange({ text: p.sku_code, product: p });
    setOpen(false);
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (!open && (e.key === "ArrowDown" || e.key === "Enter")) {
      setOpen(true);
      return;
    }
    if (!open) return;
    if (e.key === "Escape") {
      setOpen(false);
      return;
    }
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setHighlight((h) => Math.min(h + 1, Math.max(0, filtered.length - 1)));
    }
    if (e.key === "ArrowUp") {
      e.preventDefault();
      setHighlight((h) => Math.max(h - 1, 0));
    }
    if (e.key === "Enter" && filtered[highlight]) {
      e.preventDefault();
      selectProduct(filtered[highlight]);
    }
  }

  const activeId = filtered[highlight] ? `${listId}-opt-${filtered[highlight].id}` : undefined;

  return (
    <div className="product-combobox" ref={wrapRef}>
      <input
        type="text"
        className="product-combobox__input"
        value={value}
        disabled={disabled}
        placeholder={placeholder}
        role="combobox"
        aria-expanded={open}
        aria-controls={listId}
        aria-activedescendant={activeId}
        autoComplete="off"
        onFocus={() => setOpen(true)}
        onChange={(e) => onChange({ text: e.target.value, product: null })}
        onKeyDown={onKeyDown}
      />
      {productId && (
        <span className="product-combobox__badge" title="SKU cadastrado">
          ✓
        </span>
      )}
      {open && filtered.length > 0 && (
        <ul className="product-combobox__list" id={listId} role="listbox">
          {filtered.map((p, i) => (
            <li
              key={p.id}
              id={`${listId}-opt-${p.id}`}
              role="option"
              aria-selected={i === highlight}
              className={`product-combobox__option${i === highlight ? " product-combobox__option--on" : ""}`}
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => selectProduct(p)}
              onMouseEnter={() => setHighlight(i)}
            >
              <strong>{p.sku_code}</strong>
              <span>{p.description}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
