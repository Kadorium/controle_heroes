/** Local, reload-safe origin; never accept an external URL or an arbitrary redirect. */
export function contextReturn(value: string | null | undefined): string | null {
  if (!value || /[\\\r\n]/.test(value)) return null;
  return /^\/(?:orders\/\d+(?:\/commercial)?|customs\/\d+|inventory\/receiving)(?:[?#].*)?$/.test(value) ? value : null;
}
export function withContextReturn(path: string, origin: string): string {
  const [base, hash] = path.split("#");
  const [pathname, search] = base.split("?");
  const params = new URLSearchParams(search);
  const allowed = contextReturn(origin);
  if (allowed) params.set("return_to", allowed);
  return pathname + (params.size ? `?${params}` : "") + (hash ? `#${hash}` : "");
}
