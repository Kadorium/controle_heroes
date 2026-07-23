import { useEffect, useRef, useState } from "react";
import { Card, EmptyState, PageHeader, Table, useToast } from "../components";
import { documentsApi, importationsApi, type DocumentAttachment } from "../api";

export function DocumentsPage() {
  const toast = useToast();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [docs, setDocs] = useState<DocumentAttachment[]>([]);
  const [importations, setImportations] = useState<Array<{ id: number; po_number: string }>>([]);
  const [selectedImp, setSelectedImp] = useState("");
  const [error, setError] = useState("");
  const [dragActive, setDragActive] = useState(false);

  useEffect(() => {
    Promise.all([documentsApi.list(), importationsApi.list()])
      .then(([d, imps]) => {
        setDocs(d);
        setImportations(imps);
      })
      .catch((e) => setError(e.message));
  }, []);

  async function uploadFile(file: File) {
    if (!selectedImp) {
      toast.error("Selecione uma importação primeiro");
      return;
    }
    setError("");
    try {
      await documentsApi.upload(file, "importation_order", selectedImp, "PROFORMA");
      toast.success("Documento enviado");
      setDocs(await documentsApi.list("importation_order", selectedImp));
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Erro no upload";
      setError(msg);
      toast.error(msg);
    }
  }

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    await uploadFile(file);
    e.target.value = "";
  }

  function onDragOver(e: React.DragEvent) {
    e.preventDefault();
    setDragActive(true);
  }

  function onDragLeave() {
    setDragActive(false);
  }

  async function onDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragActive(false);
    const file = e.dataTransfer.files?.[0];
    if (file) await uploadFile(file);
  }

  return (
    <Card>
      <PageHeader title="Documentos" />
      {error && <p className="error">{error}</p>}

      <div className="inline-form">
        <select value={selectedImp} onChange={(e) => setSelectedImp(e.target.value)}>
          <option value="">Importação</option>
          {importations.map((i) => (
            <option key={i.id} value={i.id}>
              {i.po_number}
            </option>
          ))}
        </select>
      </div>

      <div
        className={`drop-zone${dragActive ? " drop-zone--active" : ""}`}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
        onClick={() => fileInputRef.current?.click()}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => e.key === "Enter" && fileInputRef.current?.click()}
      >
        <p>Arraste um arquivo aqui ou clique para selecionar</p>
        <p className="meta">Requer importação selecionada acima</p>
        <input
          ref={fileInputRef}
          type="file"
          hidden
          onChange={handleUpload}
          disabled={!selectedImp}
        />
      </div>

      {docs.length === 0 ? (
        <EmptyState title="Nenhum documento" description="Envie o primeiro anexo acima." />
      ) : (
        <Table>
          <thead>
            <tr>
              <th>Arquivo</th>
              <th>Entidade</th>
              <th>Tipo</th>
              <th>Versão</th>
              <th>Hash</th>
            </tr>
          </thead>
          <tbody>
            {docs.map((d) => (
              <tr key={d.id}>
                <td>{d.original_filename}</td>
                <td>
                  {d.entity_type} #{d.entity_id}
                </td>
                <td>{d.document_type ?? "—"}</td>
                <td>v{d.version}</td>
                <td className="meta">{d.file_hash.slice(0, 12)}…</td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
    </Card>
  );
}
