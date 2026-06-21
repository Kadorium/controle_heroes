import { useState } from "react";
import { importsApi } from "../api";

export function HeroesUploadPage() {
  const [error, setError] = useState("");
  const [msg, setMsg] = useState("");

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setError("");
    setMsg("");
    try {
      const result = await importsApi.uploadHeroes(file);
      setMsg(`Importado: ${result.row_count ?? 0} linhas para staging. Revise a fila.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro");
    }
  }

  return (
    <div className="card">
      <h1>Upload Heroes</h1>
      <p className="meta">
        CSV com colunas: PO, SKU, Description, Qty, UnitPrice, Supplier. Mapeamento configurável via API.
      </p>
      {error && <p className="error">{error}</p>}
      {msg && <p className="meta">{msg}</p>}
      <input type="file" accept=".csv" onChange={handleUpload} />
    </div>
  );
}
