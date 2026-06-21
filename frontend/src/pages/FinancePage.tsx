import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Badge, Button, EmptyState, LoadingState, PageHeader, Table } from "../components";
import {
  financeApi,
  importationsApi,
  invoicesApi,
  suppliersApi,
  type Importation,
  type Invoice,
  type Payment,
  type Supplier,
} from "../api";
import { emptyDash, fieldLabel, payStatusLabel } from "../i18n/glossario";
import { fmtDate, isPlannedPayment } from "../utils/formatDate";

type PayFilter = "all" | "overdue" | "due7" | "planned" | "settled" | "no_receipt";

interface PayRow {
  payment: Payment;
  invoice: Invoice;
  importation: Importation;
  supplierName: string;
}

export function FinancePage() {
  const navigate = useNavigate();
  const [rows, setRows] = useState<PayRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<PayFilter>("all");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [imps, invs, pays, sups] = await Promise.all([
          importationsApi.list(),
          invoicesApi.list(),
          financeApi.listPayments(),
          suppliersApi.list(),
        ]);
        const impMap = Object.fromEntries(imps.map((i) => [i.id, i]));
        const supMap = Object.fromEntries(sups.map((s) => [s.id, s.name]));
        const invMap = Object.fromEntries(invs.map((i) => [i.id, i]));
        const built: PayRow[] = pays
          .filter((p) => p.is_active)
          .map((p) => {
            const inv = invMap[p.invoice_id];
            const imp = inv ? impMap[inv.importation_id] : undefined;
            return {
              payment: p,
              invoice: inv!,
              importation: imp!,
              supplierName: imp ? supMap[imp.supplier_id] ?? "—" : "—",
            };
          })
          .filter((r) => r.invoice && r.importation);
        if (!cancelled) setRows(built);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const filtered = useMemo(() => {
    const today = new Date().toISOString().slice(0, 10);
    const in7 = new Date();
    in7.setDate(in7.getDate() + 7);
    const in7s = in7.toISOString().slice(0, 10);
    return rows.filter((r) => {
      const p = r.payment;
      const planned = isPlannedPayment(p);
      const settled = !planned && (p.payment_date != null || !!p.receipt_reference);
      switch (filter) {
        case "overdue":
          return p.due_date && p.due_date < today && planned;
        case "due7":
          return p.due_date && p.due_date >= today && p.due_date <= in7s && planned;
        case "planned":
          return planned;
        case "settled":
          return settled;
        case "no_receipt":
          return settled && !p.receipt_reference;
        default:
          return true;
      }
    });
  }, [rows, filter]);

  if (loading) {
    return (
      <div>
        <PageHeader title="Fila de contas a pagar" subtitle="Vencimentos, pagamentos planejados e liquidados — visão global." />
        <LoadingState label="Carregando contas a pagar..." />
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        title="Fila de contas a pagar"
        subtitle="Vencimentos, pagamentos planejados e liquidados — visão global."
      />
      <div className="finance-banners">
        <p className="finance-info-banner">Planejado não reduz saldo · Liquidado reduz</p>
        <p className="finance-info-banner">Crédito ≠ desconto</p>
        <p className="finance-info-banner">Vencimento ≠ data real de pagamento</p>
      </div>
      <div className="order-queue__filters">
        {(
          [
            ["all", "Todas"],
            ["overdue", "Vencidas"],
            ["due7", "Vencendo 7d"],
            ["planned", "Planejadas"],
            ["settled", "Liquidadas"],
            ["no_receipt", "Pagas sem comprovante"],
          ] as const
        ).map(([id, label]) => (
          <button
            key={id}
            type="button"
            className={`order-queue__filter${filter === id ? " order-queue__filter--on" : ""}`}
            onClick={() => setFilter(id)}
          >
            {label}
          </button>
        ))}
      </div>
      {filtered.length === 0 ? (
        <EmptyState title="Nenhum pagamento encontrado" />
      ) : (
        <div className="order-queue__scroll">
          <Table>
            <thead>
              <tr>
                <th>Vencimento</th>
                <th>{fieldLabel("Invoice")}</th>
                <th>{fieldLabel("Importation")}</th>
                <th>Fornecedor</th>
                <th className="num">Valor EUR</th>
                <th className="num">Câmbio</th>
                <th className="num">Valor BRL</th>
                <th>Status</th>
                <th>Aprovação</th>
                <th>Comprovante</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((r) => {
                const p = r.payment;
                const planned = isPlannedPayment(p);
                const status = planned
                  ? payStatusLabel("PLANNED")
                  : payStatusLabel(p.payment_date ? "SETTLED" : "PENDING");
                return (
                  <tr key={p.id}>
                    <td>{p.due_date ? fmtDate(p.due_date) : emptyDash(null)}</td>
                    <td>{r.invoice.invoice_number}</td>
                    <td>
                      <button
                        type="button"
                        className="link-btn"
                        onClick={() => navigate(`/importacoes/${r.importation.id}/resumo`)}
                      >
                        {r.importation.po_number}
                      </button>
                    </td>
                    <td>{r.supplierName}</td>
                    <td className="num">{p.amount_foreign ?? emptyDash(null)}</td>
                    <td className="num">{p.exchange_rate ?? emptyDash(null)}</td>
                    <td className="num">{p.amount_local ?? emptyDash(null)}</td>
                    <td>
                      <Badge status={planned ? "PENDING" : "FULL_PAID"}>{status}</Badge>
                    </td>
                    <td>{emptyDash(null)}</td>
                    <td>{p.receipt_reference ? "Sim" : "Não"}</td>
                    <td>
                      <Button variant="ghost" className="ui-btn--sm" onClick={() => navigate(`/importacoes/${r.importation.id}/financeiro`)}>
                        Abrir
                      </Button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </Table>
        </div>
      )}
    </div>
  );
}
