import { useState } from "react";

type Props = {
  documentId: number;
  filename: string;
  mimeType?: string | null;
  "data-testid"?: string;
};

const PREVIEWABLE = /^(application\/pdf|image\/)/i;

function contentUrl(documentId: number, download: boolean) {
  const q = download ? "?download=1" : "";
  return `/api/documents/${documentId}/content${q}`;
}

/**
 * Ações de consulta documental (Abrir / Baixar) — um componente para Order, Invoice, Shipment.
 */
export function DocumentActions({
  documentId,
  filename,
  mimeType,
  "data-testid": testId = "document-actions",
}: Props) {
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const canPreview = Boolean(mimeType && PREVIEWABLE.test(mimeType));

  async function probeAndOpen(download: boolean) {
    setBusy(true);
    setError(null);
    try {
      const url = contentUrl(documentId, download);
      const res = await fetch(url, { credentials: "include", method: "GET" });
      if (res.status === 403) {
        setError("Sem permissão para acessar este documento.");
        return;
      }
      if (res.status === 404) {
        setError("Documento ou arquivo não encontrado.");
        return;
      }
      if (!res.ok) {
        setError("Não foi possível obter o documento.");
        return;
      }
      // Abrir blob URL evita depender só de navegação (cookie ok via fetch)
      const blob = await res.blob();
      const objectUrl = URL.createObjectURL(blob);
      if (download) {
        const a = document.createElement("a");
        a.href = objectUrl;
        a.download = filename || "documento";
        a.rel = "noopener";
        a.click();
      } else {
        window.open(objectUrl, "_blank", "noopener,noreferrer");
      }
      setTimeout(() => URL.revokeObjectURL(objectUrl), 60_000);
    } catch {
      setError("Falha de rede ao acessar o documento.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <span className="document-actions stack-row" data-testid={testId}>
      <span className="document-actions-name" data-testid={`${testId}-name`}>
        {filename}
      </span>
      {canPreview || !mimeType ? (
        <button
          type="button"
          className="ui-button ui-button--ghost"
          data-testid={`${testId}-open`}
          disabled={busy}
          onClick={() => void probeAndOpen(false)}
        >
          Abrir
        </button>
      ) : null}
      <button
        type="button"
        className="ui-button ui-button--secondary"
        data-testid={`${testId}-download`}
        disabled={busy}
        onClick={() => void probeAndOpen(true)}
      >
        Baixar
      </button>
      {error ? (
        <span className="muted error" role="alert" data-testid={`${testId}-error`}>
          {error}
        </span>
      ) : null}
    </span>
  );
}
