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

function isValidYmd(year: number, month: number, day: number): boolean {
  if (month < 1 || month > 12 || day < 1 || day > 31) return false;
  const dt = new Date(year, month - 1, day);
  return dt.getFullYear() === year && dt.getMonth() === month - 1 && dt.getDate() === day;
}

/** Aceita `YYYY-MM-DD` ou `dd/mm/aaaa`. Incompleto → null. */
export function parseDateToIso(raw: string | null | undefined): string | null {
  if (raw == null) return null;
  const t = raw.trim();
  if (!t) return null;
  const iso = /^(\d{4})-(\d{2})-(\d{2})$/.exec(t);
  if (iso) {
    const year = Number(iso[1]);
    const month = Number(iso[2]);
    const day = Number(iso[3]);
    return isValidYmd(year, month, day) ? `${iso[1]}-${iso[2]}-${iso[3]}` : null;
  }
  const br = /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/.exec(t);
  if (!br) return null;
  const day = Number(br[1]);
  const month = Number(br[2]);
  const year = Number(br[3]);
  if (!isValidYmd(year, month, day)) return null;
  return `${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
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
    if (tz === "-03:00" || tz === "-0300") return `${base} Brasília`;
    if (tz === "+00:00" || tz === "+0000") return `${base} UTC`;
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

const COMPACT_SYMBOL: Record<string, string> = {
  BRL: "R$",
  EUR: "€",
  USD: "US$",
};

/** Eixo de gráfico: pt-BR com milhar; sem casas se for inteiro. */
export function formatChartTick(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === "") return ABSENCE;
  const n = typeof value === "number" ? value : parseDecimal(value);
  if (n === null || !Number.isFinite(n)) return ABSENCE;
  const abs = Math.abs(n);
  if (abs >= 1_000_000) {
    return `${new Intl.NumberFormat("pt-BR", {
      minimumFractionDigits: 1,
      maximumFractionDigits: 1,
    }).format(n / 1_000_000)} mi`;
  }
  const isInt = Number.isInteger(n) || Math.abs(n - Math.round(n)) < 1e-9;
  return new Intl.NumberFormat("pt-BR", {
    minimumFractionDigits: isInt ? 0 : 2,
    maximumFractionDigits: isInt ? 0 : 2,
  }).format(isInt ? Math.round(n) : n);
}

/** Totais do painel: `R$ 1,43 mi`, `€ 14,97 mil`. Detalhe continua em formatMoney. */
export function formatCompactMoney(
  amount: string | number | null | undefined,
  currency?: string | null,
): string {
  if (amount === null || amount === undefined || amount === "") return ABSENCE;
  const n = parseDecimal(amount);
  if (n === null) return ABSENCE;
  const abs = Math.abs(n);
  let scaled = n;
  let suffix = "";
  if (abs >= 1_000_000) {
    scaled = n / 1_000_000;
    suffix = " mi";
  } else if (abs >= 1_000) {
    scaled = n / 1_000;
    suffix = " mil";
  }
  const formatted = new Intl.NumberFormat("pt-BR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(scaled);
  const code = currency?.trim();
  const sym = code ? COMPACT_SYMBOL[code] : "";
  if (sym) return `${sym} ${formatted}${suffix}`;
  return code ? `${code} ${formatted}${suffix}` : `${formatted}${suffix}`;
}

/** Tempo relativo de vencimento. Prefere days_overdue do servidor quando vier. */
export function formatRelativeDue(
  dueDate: string | null | undefined,
  daysOverdue?: number | null,
): string {
  if (typeof daysOverdue === "number" && daysOverdue > 0) {
    return daysOverdue === 1 ? "Vencida há 1 dia" : `Vencida há ${daysOverdue} dias`;
  }
  if (!dueDate) return ABSENCE;
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(dueDate).trim());
  if (!m) return ABSENCE;
  const due = Date.UTC(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
  const now = new Date();
  const today = Date.UTC(now.getFullYear(), now.getMonth(), now.getDate());
  const diff = Math.round((due - today) / 86_400_000);
  if (diff === 0) return "Vence hoje";
  if (diff < 0) {
    const d = -diff;
    return d === 1 ? "Vencida há 1 dia" : `Vencida há ${d} dias`;
  }
  return diff === 1 ? "Vence em 1 dia" : `Vence em ${diff} dias`;
}

export function formatUpdatedAgo(iso: string | null | undefined): string {
  if (!iso) return ABSENCE;
  const then = Date.parse(iso);
  if (!Number.isFinite(then)) return ABSENCE;
  const sec = Math.max(0, Math.round((Date.now() - then) / 1000));
  if (sec < 45) return "Atualizado agora";
  if (sec < 90) return "Atualizado há 1 minuto";
  if (sec < 3600) return `Atualizado há ${Math.round(sec / 60)} min`;
  if (sec < 5400) return "Atualizado há 1 hora";
  if (sec < 86400) return `Atualizado há ${Math.round(sec / 3600)} h`;
  const days = Math.round(sec / 86400);
  return days === 1 ? "Atualizado há 1 dia" : `Atualizado há ${days} dias`;
}
