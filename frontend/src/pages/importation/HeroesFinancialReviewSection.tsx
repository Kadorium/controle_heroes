export interface FinancialReviewInvoiceRow {
  invoice_number: string;
  invoice_date?: string | null;
  acconto_amount?: string | null;
  acconto_remaining?: string | null;
}

export interface FinancialReview {
  versato_amount?: string | null;
  versato_currency?: string | null;
  acconto_total?: string | null;
  last_acconto_rimasto?: string | null;
  expected_rimasto?: string | null;
  delta_rimasto?: string | null;
  delta_versato?: string | null;
  warnings?: string[];
  requires_manual_review?: boolean;
  invoice_rows?: FinancialReviewInvoiceRow[];
}

interface Props {
  financialReview: FinancialReview;
  versatoOverride: string;
  onVersatoOverrideChange: (value: string) => void;
  accontoOverrides: Record<string, string>;
  onAccontoOverrideChange: (invoiceNumber: string, value: string) => void;
  confirmFinancialReview: boolean;
  onConfirmFinancialReviewChange: (checked: boolean) => void;
  disabled?: boolean;
  showProvisionField?: boolean;
  provisionRate?: string;
  onProvisionRateChange?: (value: string) => void;
}

export function HeroesFinancialReviewSection({
  financialReview,
  versatoOverride,
  onVersatoOverrideChange,
  accontoOverrides,
  onAccontoOverrideChange,
  confirmFinancialReview,
  onConfirmFinancialReviewChange,
  disabled = false,
  showProvisionField = false,
  provisionRate = "",
  onProvisionRateChange,
}: Props) {
  if (financialReview.versato_amount == null) {
    return null;
  }

  const needsFinancialConfirm = financialReview.requires_manual_review === true;

  return (
    <div className="heroes-import-panel__finance">
      <h3 className="hub-card__subtitle">Revisão financeira</h3>
      <p className="meta">
        Versato = referência da planilha. Acconto = pagamento por fatura. Acconto rimasto = saldo
        informativo do pool (não é saldo a liquidar).
      </p>

      <label className="heroes-import-panel__field">
        <span>Versato ({financialReview.versato_currency ?? "EUR"})</span>
        <input
          type="text"
          value={versatoOverride}
          onChange={(e) => onVersatoOverrideChange(e.target.value)}
          disabled={disabled}
        />
      </label>

      {showProvisionField && onProvisionRateChange && (
        <label className="heroes-import-panel__field">
          <span>Câmbio provisionado (EUR→BRL)</span>
          <input
            type="text"
            value={provisionRate}
            onChange={(e) => onProvisionRateChange(e.target.value)}
            disabled={disabled}
            placeholder="Obrigatório antes de importar"
          />
        </label>
      )}

      <table className="heroes-import-panel__finance-table">
        <thead>
          <tr>
            <th>Fatura</th>
            <th>Data</th>
            <th>Acconto</th>
            <th>Rimasto (planilha)</th>
          </tr>
        </thead>
        <tbody>
          {(financialReview.invoice_rows ?? []).map((row) => (
            <tr key={row.invoice_number}>
              <td>{row.invoice_number}</td>
              <td>{row.invoice_date ?? "—"}</td>
              <td>
                <input
                  type="text"
                  className="heroes-import-panel__acconto-input"
                  value={accontoOverrides[row.invoice_number] ?? ""}
                  onChange={(e) => onAccontoOverrideChange(row.invoice_number, e.target.value)}
                  disabled={disabled}
                />
              </td>
              <td>{row.acconto_remaining ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="heroes-import-panel__finance-totals meta">
        <span>Σ acconti: {financialReview.acconto_total ?? "—"}</span>
        <span>Rimasto esperado: {financialReview.expected_rimasto ?? "—"}</span>
        <span>Último rimasto: {financialReview.last_acconto_rimasto ?? "—"}</span>
      </div>

      {(financialReview.warnings?.length ?? 0) > 0 && (
        <ul className="error heroes-import-panel__finance-warnings">
          {financialReview.warnings!.map((w) => (
            <li key={w}>{w}</li>
          ))}
        </ul>
      )}

      {needsFinancialConfirm && (
        <label className="heroes-import-panel__confirm">
          <input
            type="checkbox"
            checked={confirmFinancialReview}
            onChange={(e) => onConfirmFinancialReviewChange(e.target.checked)}
            disabled={disabled}
          />
          Revisei os valores financeiros e confirmo a importação apesar dos avisos.
        </label>
      )}
    </div>
  );
}

export function initAccontoOverrides(review: FinancialReview): Record<string, string> {
  const initial: Record<string, string> = {};
  for (const row of review.invoice_rows ?? []) {
    if (row.invoice_number && row.acconto_amount) {
      initial[row.invoice_number] = row.acconto_amount;
    }
  }
  return initial;
}
