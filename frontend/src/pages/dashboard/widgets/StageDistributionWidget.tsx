import type { DashboardRow } from "../../../hooks/useDashboardMetrics";
import { STAGE_LABELS } from "../../../hooks/useDashboardMetrics";
import { Widget } from "./Widget";

const OPEN_STAGES = STAGE_LABELS.slice(0, 6);
const STAGE_TONE = ["info", "info", "info", "warn", "warn", "purple"] as const;

export function StageDistributionWidget({
  rows,
  globalStageCounts,
}: {
  rows: DashboardRow[];
  globalStageCounts?: number[];
}) {
  const counts =
    globalStageCounts && globalStageCounts.length >= 6
      ? globalStageCounts.slice(0, 6)
      : OPEN_STAGES.map((_, idx) => rows.filter((r) => r.stageIndex === idx).length);

  const max = Math.max(1, ...counts);

  return (
    <Widget title="Importações por etapa" span={8}>
      <div className="stage-row">
        {OPEN_STAGES.map((label) => (
          <span key={label}>{label}</span>
        ))}
      </div>
      <div className="funnel">
        {counts.map((c, idx) => (
          <div
            key={OPEN_STAGES[idx]}
            className={`funnel__bar funnel__bar--${STAGE_TONE[idx]}`}
            style={{ height: `${Math.max(18, (c / max) * 100)}%` }}
          >
            {c}
          </div>
        ))}
      </div>
      {globalStageCounts && (
        <p className="meta widget-note">Funil global (todas as importações, inclui fechadas na etapa Fechado).</p>
      )}
    </Widget>
  );
}
