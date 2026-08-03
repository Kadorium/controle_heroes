/** Formatadores de apresentação — sem cálculo financeiro de domínio. */

const ABSENCE = "—";

function parseDecimal(value: string | number): number | null {
  if (typeof value === "number") {
    return Number.isFinite(value) ? value : null;
  }
  const trimmed = value.trim();
  if (!trimmed) return null;
  // API usa ponto como decimal (ex.: "400.0000"). Não interpretar vírgula pt-BR aqui.
  const n = Number(trimmed);
  return Number.isFinite(n) ? n : null;
}

/** Dinheiro: `EUR 400,00` — código ISO, 2 casas, pt-BR. Ausência → `—`. Zero real → `EUR 0,00`. */
export function formatMoney(
  amount: string | number | null | undefined,
  currency?: string | null,
): string {
  if (amount === null || amount === undefined || amount === "") return ABSENCE;
  const n = parseDecimal(amount);
  if (n === null) return ABSENCE;
  const formatted = new Intl.NumberFormat("pt-BR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(n);
  const code = currency?.trim();
  return code ? `${code} ${formatted}` : formatted;
}

/** Taxa: precisão própria (default 4). Não arredonda para 2 casas monetárias. */
export function formatRate(
  rate: string | number | null | undefined,
  fractionDigits = 4,
): string {
  if (rate === null || rate === undefined || rate === "") return ABSENCE;
  const n = parseDecimal(rate);
  if (n === null) return ABSENCE;
  return new Intl.NumberFormat("pt-BR", {
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits,
  }).format(n);
}

/**
 * Date-only: preserva o calendário recebido (YYYY-MM-DD) sem shift UTC.
 * Aceita também ISO datetime e extrai só a parte da data.
 */
export function formatDateOnly(value: string | Date | null | undefined): string {
  if (value === null || value === undefined || value === "") return ABSENCE;
  if (typeof value === "string") {
    const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(value.trim());
    if (m) return `${m[3]}/${m[2]}/${m[1]}`;
    return ABSENCE;
  }
  const y = value.getFullYear();
  const mo = String(value.getMonth() + 1).padStart(2, "0");
  const d = String(value.getDate()).padStart(2, "0");
  return `${d}/${mo}/${y}`;
}

/**
 * Datetime legível com timezone explícito quando presente no input.
 * Não inventa timezone se a string for date-only.
 */
export function formatDateTime(value: string | Date | null | undefined): string {
  if (value === null || value === undefined || value === "") return ABSENCE;
  if (typeof value === "string") {
    const trimmed = value.trim();
    const dateOnly = /^(\d{4})-(\d{2})-(\d{2})$/.exec(trimmed);
    if (dateOnly) return formatDateOnly(trimmed);

    const iso = /^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})(?::(\d{2}))?(?:\.\d+)?(.*)$/.exec(
      trimmed,
    );
    if (!iso) return ABSENCE;
    const [, y, mo, d, hh, mm, ss, tzRaw] = iso;
    const base = `${d}/${mo}/${y} ${hh}:${mm}${ss ? `:${ss}` : ""}`;
    const tz = (tzRaw || "").trim();
    if (!tz) return base;
    if (tz === "Z") return `${base} UTC`;
    return `${base} ${tz}`;
  }
  const datePart = formatDateOnly(value);
  const hh = String(value.getHours()).padStart(2, "0");
  const mm = String(value.getMinutes()).padStart(2, "0");
  const ss = String(value.getSeconds()).padStart(2, "0");
  const offsetMin = -value.getTimezoneOffset();
  const sign = offsetMin >= 0 ? "+" : "-";
  const abs = Math.abs(offsetMin);
  const oh = String(Math.floor(abs / 60)).padStart(2, "0");
  const om = String(abs % 60).padStart(2, "0");
  return `${datePart} ${hh}:${mm}:${ss} ${sign}${oh}:${om}`;
}

export const FORMAT_ABSENCE = ABSENCE;

/** Quantidade: pt-BR, até 4 casas, sem zeros à direita desnecessários. */
export function formatQuantity(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === "") return ABSENCE;
  const n = parseDecimal(value);
  if (n === null) return ABSENCE;
  return new Intl.NumberFormat("pt-BR", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 4,
  }).format(n);
}

/** Remove zeros à direita do wire decimal (ex. 10.0000 → 10) sem localizar — para inputs editáveis. */
export function compactQuantityWire(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === "") return "";
  const s = String(value).trim();
  if (!s) return "";
  if (!/^-?\d+(\.\d+)?$/.test(s)) return s;
  if (!s.includes(".")) return s;
  return s.replace(/(\.\d*?)0+$/, "$1").replace(/\.$/, "");
}
