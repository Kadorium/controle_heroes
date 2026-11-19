import { useState } from "react";
import { FxDisplay, MoneyDisplay, RowLink, formatPendencies } from "../../ui";
import type { ApQueueRow } from "./apQueueColumns";

export function compactReference(value: string) {
  return value.length > 38 ? `${value.slice(0, 10)}…${value.slice(-10)}` : value;
}

/** The full reference stays in its destination and in the selectable/copyable
 * obligation details. The visible entity number disambiguates shortened refs. */
export function ApReference({ text, href, entity, id }: { text:string; href:string; entity:string; id:unknown }) {
  const compact = compactReference(text);
  return <span className="ap-reference-cell">
    <RowLink to={href} onClick={e => e.stopPropagation()} aria-label={`${entity} ${text}`} title={text}><span className="ap-reference">{compact}</span></RowLink>
    {compact !== text && <button type="button" className="ap-reference-details" aria-label={`Ver referência completa: ${entity} ${String(id)}`}>#{String(id)} · referência completa</button>}
  </span>;
}

export function ApFullText({ text }: {text:string}) {
  const [copied,setCopied] = useState(false);
  return <span className="ap-full-text"><span>{text}</span><button type="button" className="ap-copy" onClick={async () => { try { await navigator.clipboard.writeText(text);setCopied(true); } catch { setCopied(false); } }}>{copied ? "Copiado" : "Copiar"}</button></span>;
}

export function ApProjection({ row }: {row:ApQueueRow}) {
  const rate=row.fx_projected_rate as string|null|undefined, brl=row.fx_projected_brl as string|null|undefined;
  // These fields are the current Treasury plan, not the market quote or the
  // nominal BRL obligation. Retain provided values even for a BRL obligation.
  if (rate == null && brl == null) return <span className="ap-secondary">{row.source_type === "CUSTOMS_FUNDING" ? "Não aplicável ao numerário" : row.currency === "BRL" ? "Sem projeção cambial" : "Sem plano cambial"}</span>;
  return <span className="ap-cell-stack"><span>{rate == null ? "Taxa não informada" : <FxDisplay rate={rate}/>}</span><span>{brl == null ? "BRL não informado" : <MoneyDisplay amount={brl} currency="BRL"/>}</span></span>;
}

export function apPendingText(row:ApQueueRow) {
  const codes=Array.isArray(row.pendencies) ? row.pendencies.map(String) : typeof row.pendencies === "string" ? row.pendencies.split(/[,;]/).map(x=>x.trim()) : [];
  const dateShown=Number(row.days_overdue)>0 && !!row.due_date;
  return formatPendencies(codes.filter(code => code !== "OVERDUE" || !dateShown));
}
