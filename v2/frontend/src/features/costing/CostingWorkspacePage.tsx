import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";
import type { User } from "../auth/types";
import {
  canPublishCosting,
  canReadCosting,
  canResolveRecon,
  canWriteCosting,
} from "./costingPermissions";
import {
  addCostingExpense,
  getCostingCase,
  getCostingVersion,
  publishCosting,
  recalculateCosting,
  resolvePair,
  reviseCosting,
  setFreightChoice,
  uploadCostingDocument,
  type CostingCase,
  type CostingExpense,
  type CostingVersion,
  type CostingVersionSummary,
} from "./costingApi";
import {
  ALLOCATION_METHODS,
  EXPENSE_CATEGORIES,
  allocationMethodLabel,
  componentTypeLabel,
  expenseCategoryLabel,
  expenseStatusLabel,
  sourceKindLabel,
  versionKindLabel,
  versionStatusLabel,
} from "./costingLabels";
import {
  Button,
  ContextBreadcrumb,
  ErrorState,
  LoadingState,
  MoneyDisplay,
  Notice,
  PageHeader,
  SectionCard,
  StatusBadge,
  formatDateOnly,
  formatDateTime,
  formatMoney,
  formatRate,
} from "../../ui";
import { CostingResult } from "./CostingResult";

type Props = { user: User };

const SUBTITLE =
  "Inclui tributos em valor bruto. Não representa tratamento contábil ou fiscal de recuperabilidade.";

const KINDS = ["ESTIMATED", "REVISED", "REALIZED"] as const;

function fxStoryCopy(kind: string | undefined, fx: { kind?: string; documentary_rate?: string | null } | undefined) {
  const rate = fx?.documentary_rate ? ` Taxa documental ${formatRate(fx.documentary_rate, 6)}.` : "";
  if (kind === "REALIZED" && fx?.kind === "bancario") {
    return `Câmbio bancário realizado.${rate}`;
  }
  if (fx?.kind === "parcial") {
    return `Câmbio parcial: parte documental da importação, parte ainda sem pagamento bancário.${rate} Não é câmbio realizado.`;
  }
  return `Câmbio documental da importação (Numerário).${rate} Não é câmbio bancário realizado.`;
}

function publishReadyCopy(kind: string | undefined) {
  if (kind === "REVISED") {
    return "Pronto para publicar custo revisado. Não é custo final nem câmbio realizado.";
  }
  if (kind === "REALIZED") {
    return "Pronto para publicar custo com câmbio bancário realizado.";
  }
  return "Pronto para publicar estimado.";
}

export function CostingWorkspacePage({ user }: Props) {
  const { caseId } = useParams();
  const id = Number(caseId);
  const [caseRow, setCaseRow] = useState<CostingCase | null>(null);
  const [version, setVersion] = useState<CostingVersion | null>(null);
  const [kind, setKind] = useState<string>("ESTIMATED");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [reason, setReason] = useState("");
  const [freightReason, setFreightReason] = useState("");
  const [previewStale, setPreviewStale] = useState(false);
  const [showExpenseForm, setShowExpenseForm] = useState(false);
  const [compareLeft, setCompareLeft] = useState<number | null>(null);
  const [compareRight, setCompareRight] = useState<number | null>(null);

  const [expCategory, setExpCategory] = useState("OUTRAS");
  const [expDescription, setExpDescription] = useState("");
  const [expAmount, setExpAmount] = useState("");
  const [expDate, setExpDate] = useState("");
  const [expPayee, setExpPayee] = useState("");
  const [expMethod, setExpMethod] = useState("VALUE");
  const [expFile, setExpFile] = useState<File | null>(null);

  async function reload(preferVersionId?: number) {
    const c = await getCostingCase(id);
    setCaseRow(c);
    const versions = [...(c.versions ?? [])].sort((a, b) => b.version_number - a.version_number);
    const targetId = preferVersionId ?? versions[0]?.id;
    if (targetId) {
      const v = await getCostingVersion(targetId);
      setVersion(v);
      setKind(v.kind);
    } else {
      setVersion(null);
    }
  }

  useEffect(() => {
    if (!id) return;
    reload().catch((e: Error) => setError(e.message));
  }, [id]);

  const expenses = useMemo(() => version?.expenses ?? [], [version]);
  const publishedVersions = useMemo(
    () =>
      (caseRow?.versions ?? []).filter((v) => v.status === "PUBLISHED" || v.status === "SUPERSEDED"),
    [caseRow],
  );
  const hasDraft = (caseRow?.versions ?? []).some((v) => v.status === "DRAFT");
  const canAddExpense = canWriteCosting(user) && version?.status === "DRAFT";

  if (!canReadCosting(user)) {
    return <ErrorState message="É preciso costing:read." />;
  }
  if (error && !caseRow) return <ErrorState message={error} />;
  if (!caseRow) return <LoadingState />;

  const coverage = version?.snapshot?.coverage;
  const fxStory = version?.snapshot?.fx;
  const invoiceFacts = version?.snapshot?.invoices ?? [];
  const blocked = (version?.pairs ?? []).some((p) => p.blocks_publish && p.status === "OPEN");
  const freightConflict = Boolean(coverage?.freight_conflict);

  async function onRecalc() {
    setBusy(true);
    setError(null);
    try {
      const v = await recalculateCosting(id, kind);
      setVersion(v);
      setPreviewStale(false);
      await reload(v.id);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function onPublish(allowPartial: boolean) {
    if (!version) return;
    setBusy(true);
    setError(null);
    try {
      const v = await publishCosting(version.id, { reason, allow_partial: allowPartial });
      setVersion(v);
      setPreviewStale(false);
      await reload(v.id);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function onRevise() {
    if (!version || version.status !== "PUBLISHED") return;
    setBusy(true);
    setError(null);
    try {
      const v = await reviseCosting(version.id, kind || "REVISED");
      setPreviewStale(false);
      await reload(v.id);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function onAddExpense(e: FormEvent) {
    e.preventDefault();
    if (!canAddExpense) return;
    const amount = expAmount.trim();
    if (!amount || Number(amount) <= 0) {
      setError("Informe um valor positivo para a despesa.");
      return;
    }
    if (!expDescription.trim()) {
      setError("Informe a descrição da despesa.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      let documentId: number | null = null;
      if (expFile) {
        const doc = await uploadCostingDocument(id, expFile);
        documentId = doc.id;
      }
      await addCostingExpense(id, {
        category: expCategory,
        description: expDescription.trim(),
        amount,
        currency: "BRL",
        expense_date: expDate || null,
        payee_snapshot: expPayee.trim() || null,
        document_id: documentId,
        allocation_method: expMethod,
      });
      setPreviewStale(true);
      setShowExpenseForm(false);
      setExpDescription("");
      setExpAmount("");
      setExpDate("");
      setExpPayee("");
      setExpFile(null);
      await reload(version?.id);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  function selectVersion(v: CostingVersionSummary) {
    void getCostingVersion(v.id)
      .then((full) => {
        setVersion(full);
        setKind(full.kind);
        setPreviewStale(false);
      })
      .catch((err: Error) => setError(err.message));
  }

  const compareHref =
    compareLeft && compareRight && compareLeft !== compareRight
      ? `/costing/${id}/compare?left=${compareLeft}&right=${compareRight}`
      : null;

  return (
    <div className="costing-refined" data-testid="costing-workspace">
      <ContextBreadcrumb
        items={[
          { label: "Custos", to: "/costing" },
          { label: caseRow.process_code },
        ]}
      />
      <PageHeader title="Custo desembarcado por produto" subtitle={SUBTITLE} />
      <p data-testid="costing-process-meta">
        Processo {caseRow.process_code}
        {caseRow.process_reference ? ` · ${caseRow.process_reference}` : ""} ·{" "}
        <StatusBadge status={caseRow.process_status} entity="customs" />
        {version ? (
          <>
            {" "}
            · {versionKindLabel(version.kind)} · {versionStatusLabel(version.status)}
            {version.partial_coverage ? " · cobertura incompleta" : ""}
          </>
        ) : null}
      </p>
      {error ? (
        <Notice tone="danger" data-testid="costing-error">
          {error}
        </Notice>
      ) : null}
      {previewStale ? (
        <Notice tone="warning" data-testid="costing-preview-stale">
          A prévia está desatualizada após alteração de despesa. Recalcule antes de publicar.
        </Notice>
      ) : null}
      {coverage?.coverage === "INCOMPLETE" ? (
        <Notice tone="warning" data-testid="costing-coverage-banner">
          Cobertura incompleta. O Numerário não cabe só neste processo.
          {(coverage.reasons ?? []).length ? ` ${(coverage.reasons ?? []).join(" ")}` : ""} Não
          publique custo desembarcado completo com o total do DUIMP nestes produtos.
        </Notice>
      ) : null}

      {version ? <CostingResult version={version} fxCopy={fxStoryCopy(version.kind, fxStory)} /> : <Notice tone="info">Nenhuma versão calculada neste caso.</Notice>}

      {canWriteCosting(user) ? (
        <div className="toolbar" style={{ display: "flex", gap: 8, flexWrap: "wrap", margin: "12px 0" }}>
          <label>
            Tipo{" "}
            <select value={kind} onChange={(e) => setKind(e.target.value)} data-testid="costing-kind">
              {KINDS.map((k) => (
                <option key={k} value={k}>
                  {versionKindLabel(k)}
                </option>
              ))}
            </select>
          </label>
          <Button type="button" onClick={() => void onRecalc()} disabled={busy} data-testid="costing-recalc">
            Recalcular prévia
          </Button>
          {canWriteCosting(user) && version?.status === "PUBLISHED" ? (
            <Button type="button" variant="ghost" disabled={busy} onClick={() => void onRevise()} data-testid="costing-revise">
              Nova revisão
            </Button>
          ) : null}
          {canPublishCosting(user) && version?.status === "DRAFT" ? (
            <>
              <input
                placeholder="Motivo da publicação"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                data-testid="costing-publish-reason"
              />
              <Button
                type="button"
                disabled={busy || previewStale || (blocked && !version.partial_coverage)}
                onClick={() => void onPublish(false)}
                data-testid="costing-publish"
              >
                {version.kind === "REVISED" ? "Publicar custo revisado" : "Publicar"}
              </Button>
              {version.partial_coverage ? (
                <Button
                  type="button"
                  variant="ghost"
                  disabled={busy || previewStale || !reason.trim()}
                  onClick={() => void onPublish(true)}
                  data-testid="costing-publish-partial"
                >
                  Publicar estimado incompleto
                </Button>
              ) : null}
            </>
          ) : null}
        </div>
      ) : null}

      {canPublishCosting(user) && version?.status === "DRAFT" && !blocked && coverage?.coverage === "COMPLETE" ? (
        <Notice tone="info" data-testid="costing-publish-copy">
          {publishReadyCopy(version.kind)}
        </Notice>
      ) : null}

      <SectionCard title="Fontes e cobertura">
        <p data-testid="costing-coverage-status">
          {coverage?.coverage === "INCOMPLETE" ? "INCOMPLETE" : coverage?.coverage || "—"}
        </p>
        <ul data-testid="costing-coverage-story">
          <li data-testid="costing-coverage-invoices">
            Mercadoria: {coverage?.invoice_count ?? invoiceFacts.length} de{" "}
            {coverage?.mentioned_count || coverage?.mentioned_invoice_refs?.length || invoiceFacts.length} faturas
            {coverage?.process_invoice_numbers?.length
              ? ` (${(coverage.process_invoice_numbers ?? []).join(", ")})`
              : ""}
          </li>
          <li data-testid="costing-coverage-fob">
            FOB: {coverage?.fob_amount ?? "—"} {coverage?.fob_currency ?? ""} vs mercadoria{" "}
            {coverage?.merchandise_foreign ?? "—"} {coverage?.merchandise_currency ?? ""}
          </li>
          <li data-testid="costing-coverage-freight">
            Frete CIF (base aduaneira, não entra no custo): {coverage?.freight_basis?.amount ?? "—"}{" "}
            {coverage?.freight_basis?.currency ?? ""} · internacional: {coverage?.international_freight_count ?? 0} ·
            doméstico: {coverage?.domestic_freight_count ?? 0}
          </li>
          <li data-testid="costing-coverage-tax">
            Tributos e despesas do Numerário: {coverage?.funding_included ? "incluídos" : "ausentes"}
          </li>
        </ul>
        {invoiceFacts.length ? (
          <table className="data-table" data-testid="costing-invoice-sources">
            <thead>
              <tr>
                <th>Fatura</th>
                <th>Líquido</th>
                <th>Origem FX</th>
              </tr>
            </thead>
            <tbody>
              {invoiceFacts.map((inv) => (
                <tr key={inv.invoice_number}>
                  <td>{inv.invoice_id ? <Link to={`/invoices/${inv.invoice_id}`}>{inv.invoice_number}</Link> : inv.invoice_number}</td>
                  <td>{formatMoney(inv.net_amount, inv.currency)}</td>
                  <td>{inv.fx?.initial_rate ? `documental ${inv.fx.initial_rate}` : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : null}
        <p>
          Escolha de frete internacional: {caseRow.freight_choice || "desnecessária quando a base CIF e o frete do agente são fatos distintos"}
        </p>
        {canWriteCosting(user) && version?.status === "DRAFT" && freightConflict ? (
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <input
              placeholder="Motivo da escolha de frete"
              value={freightReason}
              onChange={(e) => setFreightReason(e.target.value)}
              data-testid="costing-freight-reason"
            />
            {(["EXPENSE_LINE", "EXCLUDE"] as const).map((ch) => (
              <Button
                key={ch}
                type="button"
                variant="ghost"
                disabled={!freightReason.trim() || busy}
                data-testid={`costing-freight-${ch}`}
                onClick={() => {
                  void setFreightChoice(id, ch, freightReason)
                    .then(() => reload(version?.id))
                    .catch((err: Error) => setError(err.message));
                }}
              >
                {ch}
              </Button>
            ))}
          </div>
        ) : null}
      </SectionCard>

      <SectionCard title="Componentes">
        <table className="data-table" data-testid="costing-components">
          <thead>
            <tr>
              <th>Tipo</th>
              <th>Origem</th>
              <th>BRL</th>
              <th>No total</th>
              <th>Estado</th>
            </tr>
          </thead>
          <tbody>
            {(version?.components ?? []).map((comp) => (
              <tr key={comp.id}>
                <td>{componentTypeLabel(comp.component_type)}</td>
                <td>{sourceKindLabel(comp.source_kind)}</td>
                <td>{formatMoney(comp.amount_brl)}</td>
                <td>{comp.included ? "incluído" : "excluído"}</td>
                <td>{comp.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </SectionCard>

      <SectionCard
        title="Despesas adicionais"
        actions={
          canAddExpense ? (
            <Button
              type="button"
              variant="ghost"
              disabled={busy}
              onClick={() => setShowExpenseForm((v) => !v)}
              data-testid="costing-expense-add"
            >
              Adicionar despesa
            </Button>
          ) : null
        }
      >
        <p className="cell-secondary" data-testid="costing-expense-help">
          Despesas do caso de custo — não geram conta a pagar e não substituem linhas do Numerário.
          {!canAddExpense && canWriteCosting(user)
            ? hasDraft
              ? " Abra o rascunho para incluir despesa."
              : " Crie uma nova revisão para incluir despesa."
            : null}
        </p>
        {showExpenseForm && canAddExpense ? (
          <form className="stack" style={{ gap: 8, marginBottom: 16 }} onSubmit={(ev) => void onAddExpense(ev)} data-testid="costing-expense-form">
            <label>
              Categoria
              <select value={expCategory} onChange={(e) => setExpCategory(e.target.value)} data-testid="expense-category">
                {EXPENSE_CATEGORIES.map((c) => (
                  <option key={c.value} value={c.value}>
                    {c.label}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Descrição
              <input value={expDescription} onChange={(e) => setExpDescription(e.target.value)} required data-testid="expense-description" />
            </label>
            <label>
              Valor (BRL)
              <input value={expAmount} onChange={(e) => setExpAmount(e.target.value)} inputMode="decimal" required data-testid="expense-amount" />
            </label>
            <label>
              Data
              <input type="date" value={expDate} onChange={(e) => setExpDate(e.target.value)} data-testid="expense-date" />
            </label>
            <label>
              Favorecido (opcional)
              <input value={expPayee} onChange={(e) => setExpPayee(e.target.value)} data-testid="expense-payee" />
            </label>
            <label>
              Método de rateio
              <select value={expMethod} onChange={(e) => setExpMethod(e.target.value)} data-testid="expense-allocation">
                {ALLOCATION_METHODS.map((m) => (
                  <option key={m.value} value={m.value}>
                    {m.label}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Documento de ensaio
              <input
                type="file"
                accept=".pdf,application/pdf,image/*"
                onChange={(e) => setExpFile(e.target.files?.[0] ?? null)}
                data-testid="expense-document"
              />
            </label>
            <div className="stack-row" style={{ gap: 8 }}>
              <Button type="submit" disabled={busy} data-testid="expense-save">
                Salvar despesa
              </Button>
              <Button type="button" variant="ghost" disabled={busy} onClick={() => setShowExpenseForm(false)}>
                Cancelar
              </Button>
            </div>
          </form>
        ) : null}
        <table className="data-table" data-testid="costing-expenses">
          <thead>
            <tr>
              <th>Categoria</th>
              <th>Descrição</th>
              <th>Favorecido</th>
              <th>Valor</th>
              <th>Data</th>
              <th>Documento</th>
              <th>Rateio</th>
              <th>Situação</th>
              <th>Origem</th>
            </tr>
          </thead>
          <tbody>
            {expenses.length === 0 ? (
              <tr>
                <td colSpan={9}>Nenhuma despesa adicional neste caso.</td>
              </tr>
            ) : (
              expenses.map((ex: CostingExpense) => (
                <tr key={ex.id} data-testid={`costing-expense-row-${ex.id}`}>
                  <td>{expenseCategoryLabel(ex.category)}</td>
                  <td>{ex.description}</td>
                  <td>{ex.payee_snapshot || "—"}</td>
                  <td>
                    <MoneyDisplay amount={ex.amount} currency={ex.currency} />
                  </td>
                  <td>{ex.expense_date ? formatDateOnly(ex.expense_date) : "—"}</td>
                  <td>{ex.document_id ? <a href={`/api/documents/${ex.document_id}/content`} target="_blank" rel="noopener noreferrer">Documento #{ex.document_id}</a> : "—"}</td>
                  <td>{allocationMethodLabel(ex.allocation_method)}</td>
                  <td>{expenseStatusLabel(ex.status)}</td>
                  <td>Despesa adicional</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </SectionCard>

      <SectionCard title="Reconciliação">
        <Notice tone="info" data-testid="costing-tolerance-notice">
          As divergências usam uma tolerância provisória. A política final de conciliação ainda não está
          definida. Nada some da tela.
        </Notice>
        {(version?.pairs ?? []).length === 0 ? (
          <p className="muted" data-testid="costing-pairs-empty">
            Sem divergências.
          </p>
        ) : (
          <ul data-testid="costing-pairs">
            {(version?.pairs ?? []).map((p) => (
              <li key={p.id}>
                <strong>{p.pair_type}</strong> · {p.left_label} {p.left_value ?? "—"} vs {p.right_label}{" "}
                {p.right_value ?? "—"} · {p.severity}
                {p.blocks_publish ? " · bloqueia publicação" : ""}
                {canResolveRecon(user) && p.status === "OPEN" ? (
                  <Button
                    type="button"
                    variant="ghost"
                    onClick={() => {
                      const why = window.prompt("Motivo da resolução");
                      if (!why) return;
                      void resolvePair(p.id, why)
                        .then(() => reload(version?.id))
                        .catch((err: Error) => setError(err.message));
                    }}
                  >
                    Resolver
                  </Button>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </SectionCard>

      <SectionCard title="Versões">
        <table className="data-table" data-testid="costing-versions">
          <thead>
            <tr>
              <th>Comparar</th>
              <th>Versão</th>
              <th>Tipo</th>
              <th>Situação</th>
              <th>Total</th>
              <th>Data</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {(caseRow.versions ?? [])
              .slice()
              .sort((a, b) => b.version_number - a.version_number)
              .map((v) => {
                const selectable = v.status === "PUBLISHED" || v.status === "SUPERSEDED";
                return (
                  <tr key={v.id} data-testid={`costing-version-row-${v.id}`}>
                    <td>
                      {selectable ? (
                        <div className="stack-row" style={{ gap: 4 }}>
                          <Button
                            type="button"
                            variant={compareLeft === v.id ? "primary" : "ghost"}
                            data-testid={`costing-compare-left-${v.id}`}
                            onClick={() => {
                              setCompareLeft(v.id);
                              if (compareRight === v.id) setCompareRight(null);
                            }}
                          >
                            Esq.
                          </Button>
                          <Button
                            type="button"
                            variant={compareRight === v.id ? "primary" : "ghost"}
                            data-testid={`costing-compare-right-${v.id}`}
                            onClick={() => {
                              setCompareRight(v.id);
                              if (compareLeft === v.id) setCompareLeft(null);
                            }}
                          >
                            Dir.
                          </Button>
                        </div>
                      ) : (
                        "—"
                      )}
                    </td>
                    <td>v{v.version_number}</td>
                    <td>{v.kind}</td>
                    <td>{versionStatusLabel(v.status)}</td>
                    <td>{formatMoney(v.included_total_brl ?? null, "BRL")}</td>
                    <td>
                      {v.published_at
                        ? formatDateTime(v.published_at)
                        : v.created_at
                          ? formatDateTime(v.created_at)
                          : "—"}
                    </td>
                    <td>
                      <Button type="button" variant="ghost" onClick={() => selectVersion(v)} data-testid={`costing-open-version-${v.id}`}>
                        Abrir
                      </Button>
                    </td>
                  </tr>
                );
              })}
          </tbody>
        </table>
        {publishedVersions.length >= 2 ? (
          <div className="stack-row" style={{ gap: 8, marginTop: 12 }}>
            {compareHref ? (
              <Link className="ui-button" to={compareHref} data-testid="costing-compare-open">
                Comparar versões
              </Link>
            ) : (
              <Button type="button" disabled data-testid="costing-compare-open">
                Comparar versões
              </Button>
            )}
            <span className="cell-secondary">Selecione exatamente duas versões publicadas ou substituídas.</span>
          </div>
        ) : null}
        <p>
          <Link to={`/customs/${caseRow.import_process_id}`}>Abrir processo aduaneiro</Link>
        </p>
      </SectionCard>
    </div>
  );
}
