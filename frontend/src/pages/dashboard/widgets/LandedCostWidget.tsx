import { EmptyState } from "../../../components";
import type { DashboardRow } from "../../../hooks/useDashboardMetrics";
import { Widget } from "./Widget";

export function LandedCostWidget({ rows }: { rows: DashboardRow[] }) {
  const items = rows.filter((r) => r.lcEstimated != null && r.lcActual != null).slice(0, 6);

  const max = Math.max(
    1,
    ...items.flatMap((r) => [r.lcEstimated ?? 0, r.lcActual ?? 0])
  );

  return (
    <Widget title="Landed cost · estimado vs realizado" span={5}>
      {items.length === 0 ? (
        <EmptyState
          title="Sem landed cost calculado"
          description="Nenhuma importação com versão de LC na seleção."
        />
      ) : (
        <>
          <div className="bars">
            {items.map((r) => {
              const estH = ((r.lcEstimated ?? 0) / max) * 100;
              const realH = ((r.lcActual ?? 0) / max) * 100;
              return (
                <div className="bar" key={r.id} title={`${r.po}: est ${r.lcEstimated} / real ${r.lcActual}`}>
                  <div className="bar__pair">
                    <span className="bar__col bar__col--est" style={{ height: `${estH}%` }} />
                    <span className="bar__col bar__col--real" style={{ height: `${realH}%` }} />
                  </div>
                  <div className="bar__lab">{r.po.replace(/^DEMO-/, "D-").slice(0, 6)}</div>
                </div>
              );
            })}
          </div>
          <div className="legend">
            <span>
              <i className="legend__est" /> Estimado
            </span>
            <span>
              <i className="legend__real" /> Realizado
            </span>
          </div>
        </>
      )}
    </Widget>
  );
}
