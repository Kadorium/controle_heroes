import { useEffect, useRef, useState, type ReactNode } from "react";

export interface SelectOption {
  value: string;
  label: string;
}

interface EditableCellProps {
  value: string | number | null | undefined;
  display?: ReactNode;
  type?: "text" | "number" | "date" | "select";
  options?: SelectOption[];
  align?: "left" | "right";
  editable?: boolean;
  lockedReason?: string;
  placeholder?: string;
  emptyText?: string;
  title?: string;
  onSave: (newValue: string) => Promise<void>;
}

type CellStatus = "idle" | "saving" | "saved" | "error";

/**
 * Célula editável estilo planilha. Enter salva, Esc cancela, blur salva.
 * Tab move o foco naturalmente (salvando a célula atual via blur).
 */
export function EditableCell({
  value,
  display,
  type = "text",
  options = [],
  align = "left",
  editable = true,
  lockedReason,
  placeholder,
  emptyText = "—",
  title,
  onSave,
}: EditableCellProps) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");
  const [status, setStatus] = useState<CellStatus>("idle");
  const [errorMsg, setErrorMsg] = useState("");
  const inputRef = useRef<HTMLInputElement | HTMLSelectElement | null>(null);
  const committedRef = useRef(false);

  useEffect(() => {
    if (editing && inputRef.current) {
      inputRef.current.focus();
      if (type !== "select" && "select" in inputRef.current) {
        (inputRef.current as HTMLInputElement).select();
      }
    }
  }, [editing, type]);

  const current = value === null || value === undefined ? "" : String(value);

  function startEdit() {
    if (!editable) return;
    committedRef.current = false;
    setDraft(current);
    setErrorMsg("");
    setEditing(true);
  }

  async function commit(next: string) {
    if (committedRef.current) return;
    committedRef.current = true;
    setEditing(false);
    if (next === current) {
      setStatus("idle");
      return;
    }
    setStatus("saving");
    try {
      await onSave(next);
      setStatus("saved");
      setErrorMsg("");
      window.setTimeout(() => setStatus("idle"), 1400);
    } catch (e) {
      setStatus("error");
      setErrorMsg(e instanceof Error ? e.message : "Erro ao salvar");
    }
  }

  function cancel() {
    committedRef.current = true;
    setEditing(false);
    setStatus("idle");
  }

  function onKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter") {
      e.preventDefault();
      void commit(draft);
    } else if (e.key === "Escape") {
      e.preventDefault();
      cancel();
    }
  }

  const alignClass = align === "right" ? " editable-cell--num" : "";

  if (!editable) {
    return (
      <span
        className={`editable-cell editable-cell--locked${alignClass}`}
        title={lockedReason || title}
      >
        {display ?? (current ? current : emptyText)}
        {lockedReason && <span className="editable-cell__lock" aria-hidden>IT</span>}
      </span>
    );
  }

  if (editing) {
    return (
      <span className={`editable-cell editable-cell--editing${alignClass}`}>
        {type === "select" ? (
          <select
            ref={(el) => (inputRef.current = el)}
            className="editable-cell__input"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onBlur={() => void commit(draft)}
            onKeyDown={onKeyDown}
          >
            <option value="">{placeholder ?? "—"}</option>
            {options.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        ) : (
          <input
            ref={(el) => (inputRef.current = el)}
            className="editable-cell__input"
            type={type}
            value={draft}
            placeholder={placeholder}
            onChange={(e) => setDraft(e.target.value)}
            onBlur={() => void commit(draft)}
            onKeyDown={onKeyDown}
          />
        )}
      </span>
    );
  }

  return (
    <span
      className={`editable-cell editable-cell--${status}${alignClass}`}
      role="button"
      tabIndex={0}
      title={errorMsg || title || "Clique para editar (Enter salva, Esc cancela)"}
      onClick={startEdit}
      onFocus={() => undefined}
      onKeyDown={(e) => {
        if (e.key === "Enter") {
          e.preventDefault();
          startEdit();
        }
      }}
    >
      {display ?? (current ? current : <span className="editable-cell__empty">{emptyText}</span>)}
      {status === "saved" && <span className="editable-cell__flag editable-cell__flag--ok" aria-hidden>✓</span>}
      {status === "error" && <span className="editable-cell__flag editable-cell__flag--err" aria-hidden>!</span>}
    </span>
  );
}
