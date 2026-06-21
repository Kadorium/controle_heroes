import { Link } from "react-router-dom";
import { Badge, EmptyState } from "../../../components";
import type { DashboardRow } from "../../../hooks/useDashboardMetrics";
import { fullMoney } from "../format";
import { PlaneIcon, ShipIcon } from "../icons";
import { Widget } from "./Widget";

const PIPELINE_STAGES = [2, 3, 4, 5, 6];

function Pipeline({ stageIndex }: { stageIndex: number }) {
  return (
    <div className="pipe">
      {PIPELINE_STAGES.map((s) => {
        const cls = s < stageIndex ? "done" : s === stageIndex ? "now" : "";
        return <div key={s} className={`seg2 ${cls}`.trim()} />;
      })}
    </div>
  );
}

function formatEta(iso: string | null): string {
  if (!iso) return "ETA —";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return `ETA ${d.toLocaleDateString("pt-BR")}`;
}

export function InTransitWidget({
  rows,
  totalCount,
}: {
  rows: DashboardRow[];
  totalCount?: number;
}) {
  const items = rows.filter((r) => r.inTransit);
  const count = totalCount ?? items.length;

  return (
    <Widget title="Em trânsito" count={count} span={7}>
      {items.length === 0 ? (
        <EmptyState title="Nada em trânsito" description="Nenhum embarque na seleção atual." />
      ) : (
        items.map((r) => (
          <div className="row" key={r.id}>
            <div className={`modal-ico ${r.modal === "AIR" ? "m-air" : "m-ocean"}`}>
              {r.modal === "AIR" ? <PlaneIcon className="ico" /> : <ShipIcon className="ico" />}
            </div>
            <div className="row__main">
              <Link to={`/importacoes/${r.id}/resumo`} className="row__po">
                {r.po}
              </Link>
              <div className="row__sub">
                {r.supplierName} · {r.modal ?? "modal —"} · {formatEta(r.eta)}
              </div>
              <Pipeline stageIndex={r.stageIndex} />
            </div>
            <div className="row__rt">
              <Badge status={r.status}>{r.status}</Badge>
              <div className="row__val">
                {r.openValue != null && r.openValue > 0 ? fullMoney(r.openValue, r.currency) : "—"}
              </div>
            </div>
          </div>
        ))
      )}
    </Widget>
  );
}
