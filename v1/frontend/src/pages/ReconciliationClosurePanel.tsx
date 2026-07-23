import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Button,
  Card,
  Table,
  useToast,
} from "../components";
import {
  closureApi,
  reconciliationApi,
  usersApi,
  type ClosureRecord,
  type ReasonCode,
  type Reconciliation,
  type TimelineEvent,
} from "../api";
import {
  CHECKLIST_ROUTE_MAP,
  type ChecklistItem,
} from "./importation/types";
import { formatAmount } from "../i18n/glossario";

interface Props {
  importationId: number;
}

export function ReconciliationClosurePanel({ importationId }: Props) {
  const toast = useToast();
  const [recs, setRecs] = useState<Reconciliation[]>([]);
  const [checklist, setChecklist] = useState<ChecklistItem[]>([]);
  const [history, setHistory] = useState<ClosureRecord[]>([]);
  const [timeline, setTimeline] = useState<TimelineEvent[]>([]);
  const [error, setError] = useState("");
  const [showReopenModal, setShowReopenModal] = useState(false);
  const [reasonCodes, setReasonCodes] = useState<ReasonCode[]>([]);
  const [reopenCode, setReopenCode] = useState("");
  const [reopenJustification, setReopenJustification] = useState("");
  const [reopenLoading, setReopenLoading] = useState(false);

  async function load() {
    try {
      const [r, c, h, t] = await Promise.all([
        reconciliationApi.list(importationId),
        closureApi.checklist(importationId),
        closureApi.history(importationId),
        closureApi.timeline(importationId),
      ]);
      setRecs(r);
      setChecklist(c);
      setHistory(h);
      setTimeline(t);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro");
    }
  }

  useEffect(() => {
    load();
  }, [importationId]);

  useEffect(() => {
    const hash = window.location.hash;
    if (!hash) return;
    const timer = window.setTimeout(() => {
      document.querySelector(hash)?.scrollIntoView({ behavior: "smooth", block: "start" });
    }, 100);
    return () => window.clearTimeout(timer);
  }, [checklist, recs]);

  useEffect(() => {
    if (showReopenModal && reasonCodes.length === 0) {
      usersApi.listReasonCodes().then((codes) => {
        const reopen = codes.filter((c) => c.category === "reabertura");
        setReasonCodes(reopen);
        if (reopen.length) setReopenCode(reopen[0].code);
      });
    }
  }, [showReopenModal, reasonCodes.length]);

  async function runReconciliation() {
    setError("");
    try {
      setRecs(await reconciliationApi.run(importationId));
      setChecklist(await closureApi.checklist(importationId));
      toast.success("Conciliações executadas");
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Erro";
      setError(msg);
      toast.error(msg);
    }
  }

  const blockingItems = checklist.filter((c) => !c.passed);
  const hasBlocking = blockingItems.length > 0;
  const closeTooltip = hasBlocking
    ? `Pendências: ${blockingItems.map((c) => c.label).join("; ")}`
    : "Fechar importação";

  async function closeClean() {
    setError("");
    try {
      await reconciliationApi.run(importationId);
      await closureApi.close(importationId, {});
      toast.success("Importação fechada");
      await load();
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Erro";
      setError(msg);
      toast.error(msg);
    }
  }

  async function submitReopen() {
    setReopenLoading(true);
    setError("");
    try {
      await closureApi.reopen(importationId, {
        reason_code: reopenCode,
        justification: reopenJustification,
      });
      toast.success("Importação reaberta");
      setShowReopenModal(false);
      setReopenJustification("");
      await load();
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Erro";
      setError(msg);
      toast.error(msg);
    } finally {
      setReopenLoading(false);
    }
  }

  function checklistIcon(item: ChecklistItem) {
    if (item.passed) {
      if (item.blocking_count && item.blocking_count > 0) {
        return <span className="checklist-item__icon--warn">⚠</span>;
      }
      return <span className="checklist-item__icon--ok">✓</span>;
    }
    return <span className="checklist-item__icon--fail">✗</span>;
  }

  return (
    <div>
      {error && <p className="error">{error}</p>}

      <nav className="anchor-nav">
        <a href="#conciliacao">Conciliação</a>
        <a href="#fechamento">Fechamento</a>
        <a href="#timeline">Timeline</a>
      </nav>

      <Card id="conciliacao" title="Conciliação" compact className="stacked-section">
        <Button onClick={runReconciliation}>Executar conciliações</Button>
        <Table>
          <thead>
            <tr>
              <th>Tipo</th>
              <th>Descrição</th>
              <th>Status</th>
              <th>Variância</th>
            </tr>
          </thead>
          <tbody>
            {recs.map((r) => (
              <tr key={r.id}>
                <td>{r.pair_type}</td>
                <td>{r.label}</td>
                <td>{r.status}</td>
                <td className="num">{formatAmount(r.variance_value)}</td>
              </tr>
            ))}
          </tbody>
        </Table>
      </Card>

      <Card id="fechamento" title="Fechamento" compact className="stacked-section">
        <h4>Checklist</h4>
        <div>
          {checklist.map((c) => {
            const routeFn = CHECKLIST_ROUTE_MAP[c.id];
            const href = routeFn ? routeFn(importationId) : null;
            const label = (
              <>
                {c.label}
                {c.blocking_count != null && c.blocking_count > 0 && (
                  <span className="meta"> ({c.blocking_count} bloqueante(s))</span>
                )}
              </>
            );
            return (
              <div key={c.id} className="checklist-item">
                {checklistIcon(c)}
                {href ? (
                  <Link
                    to={href}
                    className={`checklist-item__link${c.passed ? " checklist-item__link--muted" : ""}`}
                  >
                    {label}
                  </Link>
                ) : (
                  <span>{label}</span>
                )}
              </div>
            );
          })}
        </div>
        <div className="actions">
          <Button onClick={closeClean} disabled={hasBlocking} title={closeTooltip}>
            Fechar importação
          </Button>
          <Button variant="secondary" onClick={() => setShowReopenModal(true)}>
            Reabrir
          </Button>
        </div>

        <h4>Histórico de fechamentos</h4>
        <Table>
          <thead>
            <tr>
              <th>v#</th>
              <th>Tipo</th>
              <th>Status</th>
              <th>Data</th>
            </tr>
          </thead>
          <tbody>
            {history.map((h) => (
              <tr key={h.id}>
                <td>{h.closure_version}</td>
                <td>{h.closure_type}</td>
                <td>{h.status}</td>
                <td>{new Date(h.closed_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </Table>
      </Card>

      <Card id="timeline" title="Timeline" compact className="stacked-section">
        <ul>
          {timeline.map((e, i) => (
            <li key={i}>
              {e.timestamp} — {e.type}: {e.action ?? e.to_status ?? ""}
              {e.comment ? ` (${e.comment})` : ""}
            </li>
          ))}
        </ul>
      </Card>

      {showReopenModal && (
        <div className="modal-backdrop" onClick={() => setShowReopenModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>Reabrir importação</h3>
            <label htmlFor="reopen-code">Motivo (reason_code)</label>
            <select
              id="reopen-code"
              value={reopenCode}
              onChange={(e) => setReopenCode(e.target.value)}
            >
              {reasonCodes.map((rc) => (
                <option key={rc.code} value={rc.code}>
                  {rc.label}
                </option>
              ))}
            </select>
            <label htmlFor="reopen-just">Justificativa</label>
            <textarea
              id="reopen-just"
              rows={3}
              value={reopenJustification}
              onChange={(e) => setReopenJustification(e.target.value)}
              placeholder="Descreva o motivo da reabertura"
            />
            <div className="modal__actions">
              <Button variant="ghost" onClick={() => setShowReopenModal(false)}>
                Cancelar
              </Button>
              <Button
                loading={reopenLoading}
                onClick={submitReopen}
                disabled={!reopenCode || reopenJustification.trim().length < 3}
              >
                Confirmar reabertura
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
