import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import type { User } from "../auth/types";
import { Button, Notice, SectionCard } from "../../ui";
import {
  addDocumentSetMember,
  commitDoganale,
  commitPlDetail,
  createDocumentSet,
  getDocumentSet,
  previewDossier,
  reconcileDocumentSet,
  type CommitAttemptOut,
  type DocumentDetail,
  type DossierPreviewOut,
  type ReconciliationIssueOut,
} from "./ingestionApi";

type Props = {
  user: User;
  doc: DocumentDetail;
  onUpdated?: () => void;
};

const EXPECTED_ROLES = [
  { role: "PACKING_LIST_DETAIL", label: "Packing List (detalhe)" },
  { role: "PACKING_LIST_GROUPED", label: "Packing List (agrupado)" },
  { role: "FATTURA_DOGANALE", label: "Fattura Doganale" },
  { role: "PRINT_DECLARATION", label: "Print Declaration" },
];

function canCommitPl(user: User) {
  const p = user.permissions ?? [];
  return user.role === "admin" || (p.includes("ingestion:commit") && p.includes("logistics:write"));
}

function canCommitDoganale(user: User) {
  const p = user.permissions ?? [];
  return user.role === "admin" || (p.includes("ingestion:commit") && p.includes("customs:write"));
}

function canWrite(user: User) {
  return user.role === "admin" || (user.permissions ?? []).includes("ingestion:write");
}

function entityLink(op: { entity_type: string | null; entity_id: string | null }) {
  if (!op.entity_id) return null;
  if (op.entity_type === "shipment") {
    return (
      <Link to={`/shipments/${op.entity_id}`} data-testid={`dossier-shipment-${op.entity_id}`}>
        Shipment #{op.entity_id}
      </Link>
    );
  }
  if (op.entity_type === "import_process" || op.entity_type === "process") {
    return (
      <Link to={`/customs/${op.entity_id}`} data-testid={`dossier-process-${op.entity_id}`}>
        Processo #{op.entity_id}
      </Link>
    );
  }
  return <span>#{op.entity_id}</span>;
}

export function DossierPanel({ user, doc, onUpdated }: Props) {
  const [setId, setSetId] = useState<number | null>(doc.document_set_id);
  const [members, setMembers] = useState<{ document_id: number; role: string | null }[]>([]);
  const [preview, setPreview] = useState<DossierPreviewOut | null>(null);
  const [reconcileIssues, setReconcileIssues] = useState<ReconciliationIssueOut[]>([]);
  const [plAttempt, setPlAttempt] = useState<CommitAttemptOut | null>(null);
  const [dogAttempt, setDogAttempt] = useState<CommitAttemptOut | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (doc.document_set_id) setSetId(doc.document_set_id);
  }, [doc.document_set_id]);

  useEffect(() => {
    if (!setId) return;
    void getDocumentSet(setId).then((s) => {
      setMembers(s.members.map((m) => ({ document_id: m.document_id, role: m.role })));
    });
  }, [setId]);

  async function ensureSet() {
    if (setId) return setId;
    setBusy(true);
    setError(null);
    try {
      const s = await createDocumentSet({
        batch_id: doc.batch_id,
        label: `Dossier IR #${doc.id}`,
        projection_key: `batch-${doc.batch_id}`,
      });
      setSetId(s.id);
      await addDocumentSetMember(s.id, { document_id: doc.id, role: doc.doc_type });
      setMembers([{ document_id: doc.id, role: doc.doc_type }]);
      onUpdated?.();
      return s.id;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Falha ao criar conjunto");
      return null;
    } finally {
      setBusy(false);
    }
  }

  async function handleReconcile() {
    const id = setId ?? (await ensureSet());
    if (!id) return;
    setBusy(true);
    setError(null);
    try {
      const issues = await reconcileDocumentSet(id);
      setReconcileIssues(issues);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Falha na reconciliação");
    } finally {
      setBusy(false);
    }
  }

  async function handlePreview() {
    const id = setId ?? (await ensureSet());
    if (!id) return;
    setBusy(true);
    setError(null);
    try {
      const p = await previewDossier(id);
      setPreview(p);
      setReconcileIssues(p.reconciliation_issues);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Falha no preview");
    } finally {
      setBusy(false);
    }
  }

  async function handleCommitPl() {
    if (!canCommitPl(user)) return;
    setBusy(true);
    setError(null);
    try {
      const result = await commitPlDetail(doc.id, `pl-detail-${doc.id}-${Date.now()}`);
      setPlAttempt(result);
      onUpdated?.();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Falha commit PL");
    } finally {
      setBusy(false);
    }
  }

  async function handleCommitDoganale() {
    if (!canCommitDoganale(user)) return;
    setBusy(true);
    setError(null);
    try {
      const result = await commitDoganale(doc.id, `doganale-${doc.id}-${Date.now()}`);
      setDogAttempt(result);
      onUpdated?.();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Falha commit doganale");
    } finally {
      setBusy(false);
    }
  }

  const presentRoles = new Set(members.map((m) => m.role).filter(Boolean) as string[]);
  const isPlDoc = doc.doc_type === "PACKING_LIST_DETAIL" || doc.doc_type === "PACKING_LIST_GROUPED";
  const isDoganaleDoc = doc.doc_type === "FATTURA_DOGANALE";

  return (
    <SectionCard title="Dossier — conjunto documental" data-testid="ingestion-dossier-panel">
      {error ? <Notice tone="danger">{error}</Notice> : null}
      <p className="muted">
        Conjunto #{setId ?? "—"} · documento atual: {doc.doc_type}
        <span className="ingestion-secondary-id"> (IR #{doc.id})</span>
      </p>

      {canWrite(user) ? (
        <div className="ingestion-dossier-actions">
          <Button type="button" disabled={busy} onClick={() => void ensureSet()} data-testid="dossier-create-set">
            {setId ? "Conjunto ativo" : "Criar conjunto"}
          </Button>
          <Button type="button" variant="ghost" disabled={busy} onClick={() => void handleReconcile()} data-testid="dossier-reconcile">
            Reconciliar
          </Button>
          <Button type="button" variant="ghost" disabled={busy} onClick={() => void handlePreview()} data-testid="dossier-preview">
            Preview dossier
          </Button>
        </div>
      ) : null}

      <div className="ingestion-dossier-expected" data-testid="dossier-expected-present">
        <h3 className="ingestion-subtitle">Esperado vs presente</h3>
        <ul>
          {EXPECTED_ROLES.map(({ role, label }) => (
            <li key={role} data-testid={`dossier-role-${role}`}>
              {presentRoles.has(role) || preview?.documents_found.includes(role) ? "✓" : "○"}{" "}
              {label}
            </li>
          ))}
        </ul>
        {members.length > 0 ? (
          <ul>
            {members.map((m) => (
              <li key={m.document_id}>
                <Link to={`/ingestion/${m.document_id}`}>IR #{m.document_id}</Link>
                {m.role ? ` · ${m.role}` : ""}
              </li>
            ))}
          </ul>
        ) : null}
      </div>

      {(reconcileIssues.length > 0 || preview?.reconciliation_issues.length) ? (
        <div className="ingestion-dossier-issues" data-testid="dossier-reconcile-issues">
          <h3 className="ingestion-subtitle">Divergências</h3>
          <ul>
            {(preview?.reconciliation_issues ?? reconcileIssues).map((ri, idx) => (
              <li key={`${ri.code}-${idx}`}>
                <strong className={`severity-${ri.severity.toLowerCase()}`}>{ri.severity}</strong>{" "}
                {ri.code}: {ri.message}
                {ri.doc_types?.length ? ` (${ri.doc_types.join(", ")})` : ""}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {preview ? (
        <div className="ingestion-dossier-preview" data-testid="dossier-preview-result">
          <p>
            Pode commit: {preview.can_commit ? "sim" : "não"} · docs:{" "}
            {preview.documents_found.join(", ") || "—"}
          </p>
          <ul>
            {preview.planned_operations.map((op) => (
              <li key={op.op_key}>
                <code>{op.op_key}</code>: {op.description}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className="ingestion-dossier-commits">
        {isPlDoc ? (
          <div data-testid="dossier-commit-pl">
            <h3 className="ingestion-subtitle">Commit Packing List</h3>
            {canCommitPl(user) ? (
              <Button type="button" disabled={busy} onClick={() => void handleCommitPl()}>
                Commit PL → Shipment PLANNED
              </Button>
            ) : (
              <p className="muted">Requer ingestion:commit + logistics:write</p>
            )}
            {plAttempt ? (
              <ul>
                {(plAttempt.operations ?? []).map((op) => (
                  <li key={op.id}>
                    {op.op_key}: {op.status} {entityLink(op)}
                  </li>
                ))}
              </ul>
            ) : null}
          </div>
        ) : null}

        {isDoganaleDoc ? (
          <div data-testid="dossier-commit-doganale">
            <h3 className="ingestion-subtitle">Commit Fattura Doganale</h3>
            {canCommitDoganale(user) ? (
              <Button type="button" disabled={busy} onClick={() => void handleCommitDoganale()}>
                Commit Doganale → ImportProcess DRAFT
              </Button>
            ) : (
              <p className="muted">Requer ingestion:commit + customs:write</p>
            )}
            {dogAttempt ? (
              <ul>
                {(dogAttempt.operations ?? []).map((op) => (
                  <li key={op.id}>
                    {op.op_key}: {op.status} {entityLink(op)}
                  </li>
                ))}
              </ul>
            ) : null}
          </div>
        ) : null}
      </div>
    </SectionCard>
  );
}
