/** Sanitiza destino pós-login (?next=). Apenas paths internos relativos. */

const FALLBACK = "/orders";

export function sanitizeNextPath(raw: string | null | undefined, fallback: string = FALLBACK): string {
  if (raw == null || raw === "") return fallback;

  let value = raw.trim();
  try {
    value = decodeURIComponent(value);
  } catch {
    return fallback;
  }
  value = value.trim();

  if (!value.startsWith("/")) return fallback;
  if (value.startsWith("//")) return fallback;
  if (value.includes("://")) return fallback;
  if (value.includes("\\")) return fallback;
  if (/[\s<>'"`]/.test(value)) return fallback;

  const pathOnly = value.split("?")[0]?.split("#")[0] ?? value;
  if (pathOnly === "/login" || pathOnly.startsWith("/login/")) return fallback;

  return value;
}

export function loginUrlWithNext(pathname: string, search = ""): string {
  const target = `${pathname}${search}`;
  if (!target || target === "/" || target.startsWith("/login")) {
    return "/login";
  }
  return `/login?next=${encodeURIComponent(target)}`;
}
