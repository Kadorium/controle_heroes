import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import type { User } from "../auth/types";
import {
  Button,
  EmptyState,
  ErrorState,
  LoadingState,
  Notice,
  PageHeader,
  SectionCard,
} from "../../ui";
import {
  addDocumentRow,
  correctIngestionField,
  deleteIngestionRow,
  fetchIngestionDocument,
  isVersionConflict,
  lockIngestionDocument,
  parseLocator,
  patchDocumentReviewStatus,
  deleteIngestionDocument,
  patchIngestionIssue,
  patchIngestionRow,
  patchIngestionSection,
  restoreIngestionField,
  unlockIngestionDocument,
  type DocumentDetail,
  type FieldOut,
  type IssueOut,
  type Locator,
  type RowOut,
  type SectionOut,
} from "./ingestionApi";
import { PdfViewerPanel } from "./PdfViewerPanel";
import { CommitResultPanel } from "./CommitResultPanel";
import { FatturaCommitPanel } from "./FatturaCommitPanel";
import { NumerarioCommitPanel } from "./NumerarioCommitPanel";
import { MatchingPanel } from "./MatchingPanel";
import { OrdineSummaryPanel } from "./OrdineSummaryPanel";
import { OrdineBeforeCreatePanel } from "./OrdineBeforeCreatePanel";
import { DossierPanel } from "./DossierPanel";
import { XlsxCommitPanel } from "./XlsxCommitPanel";
import { FatturaStructuredPanel } from "./FatturaStructuredPanel";

type Props = { user: User };

const ORDINE_TYPES = new Set(["ORDINE_COMPRA", "ORDINE"]);
const DOSSIER_TYPES = new Set([
  "PACKING_LIST_DETAIL",
  "PACKING_LIST_GROUPED",
  "FATTURA_DOGANALE",
  "PRINT_DECLARATION",
]);

function canWrite(user: User) {
  return user.role === "admin" || (user.permissions ?? []).includes("ingestion:write");
}

function versionConflictMessage(err: unknown): string {
  if (isVersionConflict(err)) {
    return "Conflito de versão (409): outro usuário alterou o documento. Recarregue e tente novamente.";
  }
  return err instanceof Error ? err.message : "Erro";
}

export function IngestionWorkspacePage({ user }: Props) {
  const { documentId } = useParams();
  const id = Number(documentId);
  const [doc, setDoc] = useState<DocumentDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [forbidden, setForbidden] = useState(false);
  const [activeIssueIdx, setActiveIssueIdx] = useState(0);
  const [activeLocator, setActiveLocator] = useState<Locator | null>(null);
  const [editFieldId, setEditFieldId] = useState<number | null>(null);
  const [editValue, setEditValue] = useState("");
  const [editRowId, setEditRowId] = useState<number | null>(null);
  const [editRowJson, setEditRowJson] = useState("");
  const [issueReason, setIssueReason] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async (opts?: { soft?: boolean }) => {
    if (!Number.isFinite(id)) {
      setError("ID inválido");
      return;
    }
    setError(null);
    setForbidden(false);
    if (!opts?.soft) setDoc(null);
    try {
      const data = await fetchIngestionDocument(id);
      setDoc(data);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Erro";
      if (/403|forbidden|permiss/i.test(msg)) setForbidden(true);
      setError(msg);
    }
  }, [id]);

  useEffect(() => {
    void load();
  }, [load]);

  const openIssues: IssueOut[] = useMemo(
    () => (doc?.issues ?? []).filter((i) => i.status === "OPEN"),
    [doc],
  );

  /** Ordine: só ERROR bloqueia commit — INFO/WARNING de compromisso não são ação. */
  const openBlockingErrors: IssueOut[] = useMemo(
    () => openIssues.filter((i) => i.severity === "ERROR"),
    [openIssues],
  );

  const conflictTargets = useMemo(() => {
    const items: { kind: "issue" | "field"; id: number; label: string; locator: Locator | null }[] = [];
    for (const issue of openIssues) {
      items.push({
        kind: "issue",
        id: issue.id,
        label: `${issue.code}: ${issue.message}`,
        locator: parseLocator(issue.locator_json),
      });
    }
    for (const f of doc?.fields ?? []) {
      if (f.review_status === "PENDING" || f.review_status === "REJECTED") {
        items.push({
          kind: "field",
          id: f.id,
          label: `Campo ${f.field_key}`,
          locator: parseLocator(f.locator_json),
        });
      }
    }
    return items;
  }, [doc, openIssues]);

  function goConflict(delta: number) {
    if (conflictTargets.length === 0) return;
    const next = (activeIssueIdx + delta + conflictTargets.length) % conflictTargets.length;
    setActiveIssueIdx(next);
    setActiveLocator(conflictTargets[next].locator);
  }

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
      if (e.key === "n" || e.key === "ArrowDown") {
        e.preventDefault();
        goConflict(1);
      }
      if (e.key === "p" || e.key === "ArrowUp") {
        e.preventDefault();
        goConflict(-1);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [conflictTargets, activeIssueIdx]);

  async function withBusy<T>(fn: () => Promise<T>) {
    setBusy(true);
    try {
      return await fn();
    } catch (e) {
      setError(versionConflictMessage(e));
      throw e;
    } finally {
      setBusy(false);
    }
  }

  async function saveField(field: FieldOut) {
    if (!canWrite(user)) return;
    await withBusy(async () => {
      await correctIngestionField(field.id, {
        corrected_value: editValue,
        expected_version: field.version,
        reason: "workspace",
      });
      setEditFieldId(null);
      await load();
    });
  }

  async function acceptField(field: FieldOut) {
    if (!canWrite(user)) return;
    await withBusy(async () => {
      await correctIngestionField(field.id, {
        corrected_value: field.effective_value ?? field.raw_value,
        expected_version: field.version,
        reason: "accept",
      });
      await load();
    });
  }

  async function restoreField(field: FieldOut) {
    if (!canWrite(user)) return;
    await withBusy(async () => {
      await restoreIngestionField(field.id, { expected_version: field.version });
      await load();
    });
  }

  async function resolveIssue(issue: IssueOut, status: "RESOLVED" | "DISMISSED") {
    if (!canWrite(user)) return;
    if (status === "DISMISSED" && issue.severity === "ERROR" && !issueReason.trim()) {
      setError("Para ignorar um erro, informe o motivo no campo acima.");
      return;
    }
    await withBusy(async () => {
      setError(null);
      await patchIngestionIssue(issue.id, {
        status,
        justification: issueReason.trim() || undefined,
      });
      setIssueReason("");
      await load();
    });
  }

  async function reviewSection(section: SectionOut, review_status: "APPROVED" | "REJECTED") {
    if (!canWrite(user) || !doc) return;
    await withBusy(async () => {
      await patchIngestionSection(section.id, {
        review_status,
        expected_version: section.version,
        reason: issueReason || undefined,
      });
      await load();
    });
  }

  async function discardImport() {
    if (!canWrite(user) || !doc) return;
    if (doc.created_order_id) {
      setError(
        `Esta importação já criou o pedido ${doc.created_order_code ?? `#${doc.created_order_id}`}. ` +
          "Não pode ser rejeitada nem excluída.",
      );
      return;
    }
    const hard = window.confirm(
      "Excluir esta importação em definitivo?\n\n" +
        "Só é permitido se ainda não criou pedido.\n" +
        "OK = excluir e sumir da fila · Cancelar = só marcar como rejeitada.",
    );
    await withBusy(async () => {
      if (hard) {
        try {
          await deleteIngestionDocument(doc.id);
          window.location.assign("/ingestion");
          return;
        } catch (e) {
          const msg = e instanceof Error ? e.message : "Não foi possível excluir";
          setError(msg);
          return;
        }
      }
      const reason = window.prompt("Motivo para rejeitar a importação (obrigatório):");
      if (!reason?.trim()) return;
      await patchDocumentReviewStatus(doc.id, {
        review_status: "REJECTED",
        expected_version: doc.version,
      });
      await load();
    });
  }

  async function saveRow(row: RowOut) {
    if (!canWrite(user)) return;
    await withBusy(async () => {
      await patchIngestionRow(row.id, {
        cells_json: editRowJson,
        expected_version: row.version,
        reason: "workspace",
      });
      setEditRowId(null);
      await load();
    });
  }

  async function addRow() {
    if (!canWrite(user) || !doc) return;
    await withBusy(async () => {
      const nextIndex = (doc.rows ?? []).reduce((m, r) => Math.max(m, r.row_index), -1) + 1;
      await addDocumentRow(doc.id, {
        cells_json: JSON.stringify({ note: { raw: "", normalized: "" } }),
        expected_version: doc.version,
        row_index: nextIndex,
      });
      await load();
    });
  }

  async function removeRow(row: RowOut) {
    if (!canWrite(user) || !doc) return;
    await withBusy(async () => {
      await deleteIngestionRow(row.id, row.version);
      await load();
    });
  }

  async function toggleLock() {
    if (!canWrite(user) || !doc) return;
    if (!doc.locked_by_actor_id) {
      const reason = window.prompt("Motivo operacional para pôr em espera (obrigatório):");
      if (!reason?.trim()) return;
    }
    await withBusy(async () => {
      if (doc.locked_by_actor_id) await unlockIngestionDocument(doc.id);
      else await lockIngestionDocument(doc.id);
      await load();
    });
  }

  const showOrdineCommit = doc ? ORDINE_TYPES.has(doc.doc_type) : false;
  const showDossier = doc
    ? DOSSIER_TYPES.has(doc.doc_type) || doc.document_set_id != null
    : false;

  if (forbidden) {
    return (
      <section className="panel dense" data-testid="ingestion-workspace-page">
        <ErrorState message="Sem permissão para revisar ingestão (forbidden)." />
      </section>
    );
  }

  if (error && !doc) {
    return (
      <section className="panel dense" data-testid="ingestion-workspace-page">
        <PageHeader title="Workspace de ingestão" />
        <ErrorState message={error} onRetry={() => void load()} />
      </section>
    );
  }

  if (!doc) {
    return (
      <section className="panel dense" data-testid="ingestion-workspace-page">
        <LoadingState message="Carregando workspace…" />
      </section>
    );
  }

  const reviewLabel = doc.created_order_id
    ? `Pedido criado${doc.created_order_code ? ` (${doc.created_order_code})` : ""}`
    : doc.review_status === "IN_REVIEW" || doc.review_status === "DRAFT"
      ? "Conferindo — pedido ainda não criado"
      : doc.review_status === "READY"
        ? "Pronto para criar pedido"
        : doc.review_status === "REJECTED"
          ? "Importação descartada"
          : doc.review_status;

  // Narrowed after early returns — capture for panels below.
  const currentDoc = doc;

  const technicalPanels = (
      <>
          <SectionCard title={showOrdineCommit ? "Pendências técnicas" : "Issues"} data-testid="ingestion-issues-panel">
            <div className="ingestion-conflict-nav">
              <Button type="button" variant="ghost" onClick={() => goConflict(-1)} data-testid="conflict-prev">
                Anterior
              </Button>
              <Button type="button" variant="ghost" onClick={() => goConflict(1)} data-testid="conflict-next">
                Próximo
              </Button>
              <span className="muted">
                {conflictTargets.length ? `${activeIssueIdx + 1}/${conflictTargets.length}` : "0"}
              </span>
            </div>
            {openIssues.length === 0 ? (
              <EmptyState message="Nenhuma pendência técnica aberta" />
            ) : (
              <>
                <input
                  className="ds-input ingestion-issue-reason"
                  placeholder="Motivo (obrigatório para ignorar erro)"
                  value={issueReason}
                  onChange={(e) => setIssueReason(e.target.value)}
                  data-testid="issue-resolve-reason"
                />
                <ul className="ingestion-issue-list">
                  {openIssues.map((issue, idx) => (
                    <li key={issue.id}>
                      <button
                        type="button"
                        className={
                          conflictTargets[activeIssueIdx]?.kind === "issue" &&
                          conflictTargets[activeIssueIdx]?.id === issue.id
                            ? "is-active"
                            : undefined
                        }
                        data-testid={`issue-${issue.id}`}
                        onClick={() => {
                          setActiveIssueIdx(
                            conflictTargets.findIndex((t) => t.kind === "issue" && t.id === issue.id) || idx,
                          );
                          setActiveLocator(parseLocator(issue.locator_json));
                        }}
                      >
                        {showOrdineCommit ? (
                          <>
                            <strong>{issue.severity}</strong> {issue.message}
                          </>
                        ) : (
                          <>
                            <strong>{issue.severity}</strong> {issue.code}: {issue.message}
                          </>
                        )}
                      </button>
                      {canWrite(user) ? (
                        <span className="ingestion-issue-actions">
                          <Button
                            type="button"
                            variant="ghost"
                            disabled={busy}
                            data-testid={`issue-resolve-${issue.id}`}
                            onClick={() => void resolveIssue(issue, "RESOLVED")}
                          >
                            Corrigir
                          </Button>
                          <Button
                            type="button"
                            variant="ghost"
                            disabled={busy}
                            data-testid={`issue-dismiss-${issue.id}`}
                            onClick={() => void resolveIssue(issue, "DISMISSED")}
                          >
                            Ignorar
                          </Button>
                        </span>
                      ) : null}
                    </li>
                  ))}
                </ul>
              </>
            )}
          </SectionCard>

          {(currentDoc.sections ?? []).length > 0 ? (
            <SectionCard title="Seções" data-testid="ingestion-sections-panel">
              <ul>
                {(currentDoc.sections ?? []).map((s) => (
                  <li key={s.id} data-testid={`section-${s.id}`}>
                    <strong>{s.section_key}</strong> — {s.review_status}
                    {canWrite(user) ? (
                      <>
                        <Button type="button" variant="ghost" disabled={busy} onClick={() => void reviewSection(s, "APPROVED")}>
                          Aprovar
                        </Button>
                        <Button type="button" variant="ghost" disabled={busy} onClick={() => void reviewSection(s, "REJECTED")}>
                          Rejeitar
                        </Button>
                      </>
                    ) : null}
                  </li>
                ))}
              </ul>
            </SectionCard>
          ) : null}

          <FatturaStructuredPanel doc={currentDoc} />

          <SectionCard title="Campos" data-testid="ingestion-fields-panel">
            {(currentDoc.fields ?? []).length === 0 ? (
              <EmptyState message="Nenhum campo no IR" />
            ) : (
              <table className="dense-table" data-testid="ingestion-fields-table">
                <thead>
                  <tr>
                    <th>Chave</th>
                    <th>Raw</th>
                    <th>Efetivo</th>
                    <th>Status</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {(currentDoc.fields ?? []).map((f) => (
                    <tr key={f.id}>
                      <td>
                        <button
                          type="button"
                          className="linkish"
                          onClick={() => setActiveLocator(parseLocator(f.locator_json))}
                          data-testid={`field-focus-${f.id}`}
                        >
                          {f.field_key}
                        </button>
                      </td>
                      <td>
                        <code>{f.raw_value === null ? "∅" : JSON.stringify(f.raw_value)}</code>
                      </td>
                      <td>
                        {editFieldId === f.id ? (
                          <input
                            value={editValue}
                            onChange={(e) => setEditValue(e.target.value)}
                            data-testid={`field-edit-${f.id}`}
                          />
                        ) : (
                          <code>
                            {f.effective_value === null || f.effective_value === undefined
                              ? "∅"
                              : JSON.stringify(f.effective_value)}
                          </code>
                        )}
                      </td>
                      <td>{f.review_status}</td>
                      <td>
                        {canWrite(user) ? (
                          editFieldId === f.id ? (
                            <>
                              <Button type="button" disabled={busy} onClick={() => void saveField(f)} data-testid={`field-save-${f.id}`}>
                                Salvar
                              </Button>
                              <Button type="button" variant="ghost" onClick={() => setEditFieldId(null)}>
                                Cancelar
                              </Button>
                            </>
                          ) : (
                            <>
                              <Button
                                type="button"
                                variant="ghost"
                                onClick={() => {
                                  setEditFieldId(f.id);
                                  setEditValue(f.effective_value ?? "");
                                }}
                                data-testid={`field-edit-btn-${f.id}`}
                              >
                                Editar
                              </Button>
                              <Button type="button" variant="ghost" disabled={busy} onClick={() => void acceptField(f)}>
                                Aceitar
                              </Button>
                              {f.review_status === "REJECTED" ? (
                                <span className="muted">Rejeitado — corrija ou restaure</span>
                              ) : null}
                              {f.corrected_value != null || f.review_status === "CORRECTED" ? (
                                <Button type="button" variant="ghost" disabled={busy} onClick={() => void restoreField(f)}>
                                  Restaurar
                                </Button>
                              ) : null}
                            </>
                          )
                        ) : null}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </SectionCard>

          <SectionCard
            title="Linhas"
            data-testid="ingestion-rows-panel"
            actions={
              canWrite(user) ? (
                <Button type="button" variant="ghost" disabled={busy} onClick={() => void addRow()} data-testid="row-add">
                  Adicionar linha
                </Button>
              ) : null
            }
          >
            {(currentDoc.rows ?? []).length === 0 ? (
              <EmptyState message="Nenhuma linha" />
            ) : (
              <ul>
                {(currentDoc.rows ?? []).map((r) => (
                  <li key={r.id} data-testid={`row-${r.id}`}>
                    #{r.row_index} · {r.review_status}
                    {editRowId === r.id ? (
                      <>
                        <textarea
                          className="ingestion-row-editor"
                          value={editRowJson}
                          onChange={(e) => setEditRowJson(e.target.value)}
                          data-testid={`row-edit-${r.id}`}
                        />
                        <Button type="button" disabled={busy} onClick={() => void saveRow(r)}>
                          Salvar
                        </Button>
                        <Button type="button" variant="ghost" onClick={() => setEditRowId(null)}>
                          Cancelar
                        </Button>
                      </>
                    ) : (
                      <>
                        <pre className="code-block">{r.cells_json}</pre>
                        {canWrite(user) ? (
                          <>
                            <Button
                              type="button"
                              variant="ghost"
                              onClick={() => {
                                setEditRowId(r.id);
                                setEditRowJson(r.cells_json);
                              }}
                            >
                              Editar
                            </Button>
                            <Button type="button" variant="ghost" disabled={busy} onClick={() => void removeRow(r)}>
                              Remover
                            </Button>
                          </>
                        ) : null}
                      </>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </SectionCard>
      </>
  );

  return (
    <section className="panel dense ingestion-workspace" data-testid="ingestion-workspace-page">
      <PageHeader
        title={showOrdineCommit ? "Pedido de compra (Ordine)" : `${doc.doc_type}`}
        subtitle={
          showOrdineCommit
            ? `Importação #${doc.id} · ${reviewLabel}`
            : `Revisão IR · status ${doc.review_status} · adapter ${doc.adapter_id}`
        }
        actions={
          <>
            {!showOrdineCommit ? (
              <span className="ingestion-secondary-id" data-testid="workspace-doc-id">
                IR #{doc.id}
              </span>
            ) : (
              <span className="ingestion-secondary-id sr-only" data-testid="workspace-doc-id">
                Importação #{doc.id}
              </span>
            )}
            <Link className="ui-button" to="/ingestion" data-testid="ingestion-back-queue">
              Voltar à fila
            </Link>
          </>
        }
      />

      {error ? (
        <Notice tone="danger" data-testid="workspace-error">
          {error}
        </Notice>
      ) : null}

      {canWrite(user) ? (
        <div className="ingestion-workspace-toolbar" data-testid="workspace-review-toolbar">
          <Button
            type="button"
            variant="ghost"
            disabled={busy}
            onClick={() => void discardImport()}
            data-testid="doc-review-discard"
          >
            Descartar / excluir
          </Button>
          <Button
            type="button"
            variant="ghost"
            disabled={busy}
            onClick={() => void toggleLock()}
            data-testid="doc-review-block"
          >
            {doc.locked_by_actor_id ? "Liberar espera" : "Pôr em espera"}
          </Button>
        </div>
      ) : null}

      <div className="ingestion-workspace-grid">
        <PdfViewerPanel occurrenceId={doc.occurrence_id} activeLocator={activeLocator} compactChrome={showOrdineCommit} />

        <div className="ingestion-workspace-side">
          {showOrdineCommit ? (
            <>
              <OrdineSummaryPanel user={user} doc={doc} onUpdated={() => void load({ soft: true })} />
              <OrdineBeforeCreatePanel user={user} doc={doc} onUpdated={() => void load()} />
              <CommitResultPanel
                documentId={doc.id}
                user={user}
                refreshToken={doc.version}
                onCommitted={() => void load({ soft: true })}
                onCodeChanged={() => void load({ soft: true })}
              />
            </>
          ) : (
            <MatchingPanel user={user} doc={doc} onUpdated={() => void load()} />
          )}

          {showOrdineCommit ? (
            openBlockingErrors.length > 0 ? (
              <SectionCard title="Erros que impedem criar o pedido" data-testid="ingestion-ordine-blocking-errors">
                <p className="muted">
                  Para seguir, corrija no PDF ou ignore com um motivo (fica registrado).
                </p>
                <input
                  className="ds-input ingestion-issue-reason"
                  placeholder="Motivo (obrigatório para ignorar)"
                  value={issueReason}
                  onChange={(e) => setIssueReason(e.target.value)}
                  data-testid="issue-resolve-reason"
                />
                <ul className="ingestion-issue-list">
                  {openBlockingErrors.map((issue) => (
                    <li key={issue.id}>
                      <button
                        type="button"
                        data-testid={`issue-${issue.id}`}
                        onClick={() => setActiveLocator(parseLocator(issue.locator_json))}
                      >
                        <strong>{issue.message}</strong>
                      </button>
                      {canWrite(user) ? (
                        <span className="ingestion-issue-actions">
                          <Button
                            type="button"
                            variant="ghost"
                            disabled={busy}
                            data-testid={`issue-dismiss-${issue.id}`}
                            onClick={() => void resolveIssue(issue, "DISMISSED")}
                          >
                            Ignorar
                          </Button>
                        </span>
                      ) : null}
                    </li>
                  ))}
                </ul>
              </SectionCard>
            ) : null
          ) : (
            technicalPanels
          )}

          {!showOrdineCommit && doc.doc_type === "ORDINE_COMPRA_XLSX" ? (
            <XlsxCommitPanel documentId={doc.id} doc={doc} user={user} />
          ) : null}
          {doc.doc_type === "FATTURA_VENDITA" ? (
            <FatturaCommitPanel documentId={doc.id} user={user} />
          ) : null}
          {doc.doc_type === "SOLICITACAO_NUMERARIO" ? (
            <NumerarioCommitPanel documentId={doc.id} user={user} />
          ) : null}
          {showDossier ? <DossierPanel user={user} doc={doc} onUpdated={() => void load()} /> : null}
        </div>
      </div>
    </section>
  );
}

