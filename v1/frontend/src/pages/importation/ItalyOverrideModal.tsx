import { useEffect, useState } from "react";
import { Button, Card } from "../../components";
import { documentsApi, importationsApi } from "../../api";

export interface ItalyOverrideTarget {
  entityType: "invoice" | "invoice_item";
  entityId: number;
  fieldName: string;
  fieldLabel: string;
  currentValue: string;
}

interface Props {
  importationId: number;
  target: ItalyOverrideTarget | null;
  onClose: () => void;
  onSaved: () => void;
}

export function ItalyOverrideModal({ importationId, target, onClose, onSaved }: Props) {
  const [newValue, setNewValue] = useState("");
  const [reason, setReason] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (target) {
      setNewValue(target.currentValue);
      setReason("");
      setFile(null);
      setError("");
    }
  }, [target]);

  if (!target) return null;

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!file) {
      setError("Anexo obrigatório para override de campo Itália");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const att = await documentsApi.upload(
        file,
        "importation_order",
        String(importationId),
        "ITALY_OVERRIDE"
      );
      await importationsApi.italyOverride(importationId, {
        entity_type: target!.entityType,
        entity_id: target!.entityId,
        field_name: target!.fieldName,
        new_value: newValue,
        reason,
        attachment_id: att.id,
      });
      onSaved();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao salvar override");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="modal-overlay" role="dialog" aria-modal="true" aria-labelledby="italy-override-title">
      <Card className="italy-override-modal">
        <h2 id="italy-override-title">Override Brasil — campo Itália</h2>
        <form onSubmit={submit}>
          <p className="muted">
            Correção de <strong>{target.fieldLabel}</strong> (origem Itália). Exige motivo e comprovante.
          </p>
          <div>
            <label>Valor atual</label>
            <input className="input" value={target.currentValue} readOnly />
          </div>
          <div>
            <label htmlFor="italy-new">Novo valor</label>
            <input
              id="italy-new"
              className="input"
              value={newValue}
              onChange={(e) => setNewValue(e.target.value)}
              required
            />
          </div>
          <div>
            <label htmlFor="italy-reason">Motivo</label>
            <textarea
              id="italy-reason"
              className="input"
              rows={3}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              required
              minLength={3}
            />
          </div>
          <div>
            <label htmlFor="italy-file">Anexo comprobatório</label>
            <input
              id="italy-file"
              type="file"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              required
            />
          </div>
          {error && <p className="error">{error}</p>}
          <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginTop: 12 }}>
            <Button type="button" variant="secondary" onClick={onClose}>
              Cancelar
            </Button>
            <Button type="submit" disabled={busy}>
              {busy ? "Salvando…" : "Confirmar override"}
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
}
