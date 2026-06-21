import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { EmptyState, LoadingState } from "../../../components";
import { closureApi, type TimelineEvent } from "../../../api";
import { formatTimelineEvent, timelineHasRawJson } from "../../../utils/timelineFormat";
import { fmtDateTime } from "../../../utils/formatDate";
import type { DashboardRow } from "../../../hooks/useDashboardMetrics";
import { Widget } from "./Widget";

interface Entry extends TimelineEvent {
  po: string;
  importationId: number;
}

export function RecentTimelineWidget({ rows }: { rows: DashboardRow[] }) {
  const [entries, setEntries] = useState<Entry[]>([]);
  const [loading, setLoading] = useState(true);

  const ids = rows.map((r) => r.id).join(",");

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    Promise.all(
      rows.slice(0, 8).map((r) =>
        closureApi
          .timeline(r.id)
          .then((evts) => evts.map((e) => ({ ...e, po: r.po, importationId: r.id })))
          .catch(() => [] as Entry[])
      )
    ).then((all) => {
      if (cancelled) return;
      const merged = all
        .flat()
        .filter((e) => !timelineHasRawJson(e))
        .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
        .slice(0, 10);
      setEntries(merged);
      setLoading(false);
    });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ids]);

  return (
    <Widget title="Timeline recente" span={12}>
      {loading ? (
        <LoadingState label="Carregando eventos..." />
      ) : entries.length === 0 ? (
        <EmptyState title="Sem eventos recentes" />
      ) : (
        entries.map((e, i) => {
          const f = formatTimelineEvent(e);
          return (
            <div className="row row--timeline" key={`${e.importationId}-${i}`}>
              <div className="row__main">
                <Link to={`/importacoes/${e.importationId}/resumo`} className="row__po row__po--sm">
                  {e.po}
                </Link>
                <span className="row__sub">
                  <strong>{f.title}</strong>
                  {f.detail !== "—" ? ` · ${f.detail}` : ""}
                  {e.user_name ? ` · ${e.user_name}` : ""}
                </span>
              </div>
              <div className="row__rt">
                <span className="row__sub">{fmtDateTime(e.timestamp)}</span>
              </div>
            </div>
          );
        })
      )}
    </Widget>
  );
}
