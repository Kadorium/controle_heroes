import { useCallback, useEffect, useId, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import type { Product } from "../api";

interface Props {
  products: Product[];
  value: string;
  productId: number | null;
  onChange: (next: { text: string; product: Product | null }) => void;
  placeholder?: string;
  disabled?: boolean;
}

const LIST_MAX_HEIGHT = 280;
const LIST_MIN_WIDTH = 300;

function productMatchesQuery(p: Product, q: string): boolean {
  if (p.sku_code.toLowerCase().includes(q)) return true;
  if (p.description.toLowerCase().includes(q)) return true;
  const code = p.supplier_code?.trim().toLowerCase();
  if (code && code.includes(q)) return true;
  return false;
}

function productMetaLine(p: Product): string {
  const group = p.product_group?.trim() || "—";
  const subgroup = p.product_subgroup?.trim() || "—";
  return `${group} › ${subgroup}`;
}

export function ProductCombobox({
  products,
  value,
  productId,
  onChange,
  placeholder = "SKU, nome ou código fornecedor…",
  disabled = false,
}: Props) {
  const listId = useId();
  const wrapRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLUListElement>(null);
  const [open, setOpen] = useState(false);
  const [highlight, setHighlight] = useState(0);
  const [listPos, setListPos] = useState<{
    top: number;
    left: number;
    width: number;
    maxHeight: number;
    openUp: boolean;
  } | null>(null);

  const filtered = useMemo(() => {
    const q = value.trim().toLowerCase();
    const limit = q ? 50 : 15;
    if (!q) return products.slice(0, limit);
    return products.filter((p) => productMatchesQuery(p, q)).slice(0, limit);
  }, [products, value]);

  const reposition = useCallback(() => {
    const el = inputRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const spaceBelow = window.innerHeight - rect.bottom - 12;
    const spaceAbove = rect.top - 12;
    const openUp = spaceBelow < 160 && spaceAbove > spaceBelow;
    const maxHeight = Math.min(
      LIST_MAX_HEIGHT,
      Math.max(120, openUp ? spaceAbove : spaceBelow),
    );
    setListPos({
      left: rect.left,
      top: openUp ? rect.top - maxHeight - 4 : rect.bottom + 4,
      width: Math.max(rect.width, LIST_MIN_WIDTH),
      maxHeight,
      openUp,
    });
  }, []);

  useEffect(() => {
    setHighlight(0);
  }, [value, open]);

  useEffect(() => {
    function onDocClick(e: MouseEvent) {
      const t = e.target as Node;
      if (wrapRef.current?.contains(t) || listRef.current?.contains(t)) return;
      setOpen(false);
    }
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, []);

  useEffect(() => {
    if (!open) {
      setListPos(null);
      return;
    }
    reposition();
    window.addEventListener("scroll", reposition, true);
    window.addEventListener("resize", reposition);
    return () => {
      window.removeEventListener("scroll", reposition, true);
      window.removeEventListener("resize", reposition);
    };
  }, [open, reposition, filtered.length]);

  useEffect(() => {
    if (!open || !listRef.current) return;
    const active = listRef.current.querySelector(".product-combobox__option--on");
    active?.scrollIntoView({ block: "nearest" });
  }, [highlight, open]);

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

  const listPanel =
    open && filtered.length > 0 && listPos
      ? createPortal(
          <ul
            ref={listRef}
            className={`product-combobox__list product-combobox__list--floating${
              listPos.openUp ? " product-combobox__list--up" : ""
            }`}
            id={listId}
            role="listbox"
            style={{
              position: "fixed",
              top: listPos.top,
              left: listPos.left,
              width: listPos.width,
              maxHeight: listPos.maxHeight,
            }}
          >
            <li className="product-combobox__list-hint" aria-hidden>
              {value.trim()
                ? `${filtered.length} resultado(s)`
                : `Digite SKU, nome ou código fornecedor · ${products.length} cadastrados`}
            </li>
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
                <div className="product-combobox__option-main">
                  <strong>{p.sku_code}</strong>
                  <span>{p.description}</span>
                </div>
                <div className="product-combobox__option-meta">{productMetaLine(p)}</div>
              </li>
            ))}
          </ul>,
          document.body,
        )
      : null;

  return (
    <div className="product-combobox" ref={wrapRef}>
      <input
        ref={inputRef}
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
      {listPanel}
    </div>
  );
}
