import type { TimelineEvent } from "../api";

function looksLikeJson(value: string | undefined | null): boolean {
  if (!value) return false;
  const t = value.trim();
  return (t.startsWith("{") && t.endsWith("}")) || (t.startsWith("[") && t.endsWith("]"));
}

export function formatTimelineEvent(e: TimelineEvent): {
  title: string;
  detail: string;
  reason: string | null;
} {
  const title = e.summary ?? e.action ?? e.type;
  const parts: string[] = [];

  if (e.type === "status_transition" && e.from_status && e.to_status) {
    parts.push(`${e.from_status} → ${e.to_status}`);
  } else if (e.field_changed && e.new_value && !looksLikeJson(e.new_value)) {
    parts.push(`${e.field_changed}: ${e.new_value}`);
  } else if (e.entity_label) {
    parts.push(e.entity_label);
  }

  if (e.comment) parts.push(e.comment);

  const reason = e.justification?.trim() || null;
  return {
    title,
    detail: parts.length ? parts.join(" · ") : "—",
    reason,
  };
}

export function timelineHasRawJson(e: TimelineEvent): boolean {
  return looksLikeJson(e.old_value) || looksLikeJson(e.new_value);
}
