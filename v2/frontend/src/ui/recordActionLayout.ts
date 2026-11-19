/** Ordered prefix, measured controls, including the overflow trigger. Two CSS pixels
 * of slack absorb fractional font/layout rounding without a button-count limit. */
export function fitRecordActions(widths: number[], available: number, trigger: number, primary: boolean, gap = 8) {
  const sum = (count: number) => widths.slice(0, count).reduce((a, b) => a + b, 0) + Math.max(0, count - 1) * gap;
  if (sum(widths.length) <= available - 2) return widths.length;
  let count = primary ? 1 : 0;
  for (let next = count + 1; next < widths.length; next++) {
    if (sum(next) + gap + trigger > available - 2) break;
    count = next;
  }
  return Math.min(count, widths.length);
}
