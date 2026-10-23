import { SectionCard, formatDateTime, formatMoney, formatQuantity } from "../../ui";
import type { CostingVersion } from "./costingApi";
import { versionKindLabel, versionStatusLabel } from "./costingLabels";
import "./costingResult.css";

/** Presentation of the persisted version only; no recomputation or quantity substitution. */
export function CostingResult({ version, fxCopy }: { version: CostingVersion; fxCopy: string }) {
  const coverage = version.snapshot?.coverage?.coverage;
  const hasFreight = version.components.some(c => c.included && c.component_type === "FRETE_INTERNACIONAL");
  return <section className="cost-result" aria-label="Resultado da versão" data-testid="costing-result">
    <div className="cost-result-summary">
      <div><span className="cost-result-label">Total incluído · BRL</span><strong data-testid="costing-included-total">{formatMoney(version.included_total_brl, "BRL")}</strong><small>Bruto visível: {formatMoney(version.gross_total_brl, "BRL")}</small></div>
      <div><span className="cost-result-label">Versão {version.version_number}</span><strong>{versionKindLabel(version.kind)}</strong><small>{versionStatusLabel(version.status)}{version.published_at ? ` · ${formatDateTime(version.published_at)}` : ""}</small></div>
      <div><span className="cost-result-label">Cobertura documental</span><strong>{version.partial_coverage || coverage === "INCOMPLETE" ? "Incompleta" : coverage === "COMPLETE" ? "Completa" : "Não informada"}</strong><small>{version.partial_coverage ? `${version.status === "DRAFT" ? "Prévia" : "Publicação"} parcial — não representa custo completo.` : "Conforme as fontes desta versão."}</small></div>
    </div>
    <div className="cost-result-qualifiers">
      <p data-testid="costing-fx-story">{fxCopy}</p>
      <p>Tributos brutos · base de quantidade faturada por SKU, não quantidade recebida.</p>
      {!hasFreight && <p data-testid="costing-freight-absent">Frete internacional sem componente incluído nesta versão. Ausência não significa frete a custo zero.</p>}
    </div>
    <SectionCard title="Resultado por produto">
      <div className="cost-result-table-wrap">
        <table className="data-table" data-testid="costing-products">
          <thead><tr><th>SKU</th><th>Qtd. faturada</th><th>Mercadoria</th><th>Frete int.</th><th>Tributos brutos</th><th>Despesas</th><th>Total BRL</th><th>Unitário BRL</th></tr></thead>
          <tbody>{version.products.map(p => <tr key={p.sku_snapshot}>
            <td>{p.sku_snapshot}</td><td>{formatQuantity(p.qty)}</td><td>{formatMoney(p.merchandise_brl)}</td>
            <td title={!hasFreight ? "Sem componente de frete internacional incluído" : undefined}>{hasFreight ? formatMoney(p.freight_brl) : "—"}</td>
            <td>{formatMoney(p.tax_brl)}</td><td>{formatMoney(p.expense_brl)}</td><td><strong>{formatMoney(p.total_brl)}</strong></td><td><strong>{formatMoney(p.unit_brl)}</strong></td>
          </tr>)}</tbody>
        </table>
      </div>
      {version.products.length === 0 && <p>Nenhum produto nesta versão.</p>}
    </SectionCard>
  </section>;
}
