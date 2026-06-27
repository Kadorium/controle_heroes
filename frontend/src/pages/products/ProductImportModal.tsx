import { useState } from "react";
import { Button } from "../../components";
import { productsApi, type ProductImportPreviewRow } from "../../api";

interface Props {
  open: boolean;
  onClose: () => void;
  onDone: () => void;
}

export function ProductImportModal({ open, onClose, onDone }: Props) {
  const [step, setStep] = useState<"upload" | "preview">("upload");
  const [preview, setPreview] = useState<ProductImportPreviewRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [confirmed, setConfirmed] = useState(false);

  if (!open) return null;

  async function handleFile(file: File) {
    setLoading(true);
    setError("");
    try {
      const res = await productsApi.importPreview(file);
      setPreview(res.rows);
      setStep("preview");
      setConfirmed(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro no preview");
    } finally {
      setLoading(false);
    }
  }

  async function commit() {
    setLoading(true);
    setError("");
    try {
      const validRows = preview.filter((r) => r.valid);
      await productsApi.importCommit(validRows);
      onDone();
      onClose();
      setStep("upload");
      setPreview([]);
      setConfirmed(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao importar");
    } finally {
      setLoading(false);
    }
  }

  const validCount = preview.filter((r) => r.valid).length;

  return (
    <div className="modal-back" onClick={onClose}>
      <div className="modal-card modal-card--wide" onClick={(e) => e.stopPropagation()}>
        <h3>Importar produtos</h3>
        {error && <p className="error">{error}</p>}
        {step === "upload" ? (
          <>
            <p className="meta">CSV ou XLSX com colunas: sku_code, description, product_group, lifecycle_status</p>
            <input
              type="file"
              accept=".csv,.xlsx"
              disabled={loading}
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) void handleFile(f);
              }}
            />
          </>
        ) : (
          <>
            <p>
              {validCount} válida(s) · {preview.length - validCount} inválida(s)
            </p>
            <div className="table-scroll table-scroll--short">
              <table className="table-dense">
                <thead>
                  <tr>
                    <th>Linha</th>
                    <th>SKU</th>
                    <th>Status</th>
                    <th>Erros</th>
                  </tr>
                </thead>
                <tbody>
                  {preview.map((r) => (
                    <tr key={r.row_number}>
                      <td>{r.row_number}</td>
                      <td>{r.sku_code ?? "—"}</td>
                      <td>{r.valid ? "OK" : "Inválida"}</td>
                      <td>{r.errors.join("; ") || "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <label className="checkbox-row">
              <input type="checkbox" checked={confirmed} onChange={(e) => setConfirmed(e.target.checked)} />
              Confirmo importação das linhas válidas
            </label>
          </>
        )}
        <div className="modal-actions">
          <Button variant="secondary" onClick={onClose} disabled={loading}>
            Fechar
          </Button>
          {step === "preview" && (
            <Button onClick={() => void commit()} disabled={loading || validCount === 0 || !confirmed}>
              Importar válidas
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
