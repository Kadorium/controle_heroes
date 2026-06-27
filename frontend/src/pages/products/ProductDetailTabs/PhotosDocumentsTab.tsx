import { useEffect, useState } from "react";
import { Button, EmptyState, useToast } from "../../../components";
import { documentsApi, type DocumentAttachment } from "../../../api";

interface Props {
  productId: number;
  onUploaded: () => void;
}

export function PhotosDocumentsTab({ productId, onUploaded }: Props) {
  const toast = useToast();
  const [docs, setDocs] = useState<DocumentAttachment[]>([]);
  const [uploading, setUploading] = useState(false);

  async function load() {
    const list = await documentsApi.list("product", String(productId));
    setDocs(list);
  }

  useEffect(() => {
    void load().catch(() => setDocs([]));
  }, [productId]);

  async function handleUpload(file: File) {
    setUploading(true);
    try {
      await documentsApi.upload(file, "product", String(productId), "product_photo", "product_photo");
      toast.success("Foto enviada");
      await load();
      onUploaded();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Erro no upload");
    } finally {
      setUploading(false);
    }
  }

  return (
    <div>
      <input
        type="file"
        accept="image/*"
        disabled={uploading}
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) void handleUpload(f);
        }}
      />
      {docs.length === 0 ? (
        <EmptyState title="Nenhuma foto" description="Envie imagens do produto" />
      ) : (
        <div className="product-photo-grid">
          {docs.map((d) => (
            <a key={d.id} href={`/api/documents/${d.id}/download`} target="_blank" rel="noreferrer">
              <img src={`/api/documents/${d.id}/download`} alt={d.original_filename ?? "foto"} />
            </a>
          ))}
        </div>
      )}
      <Button variant="secondary" onClick={() => void load()} disabled={uploading}>
        Atualizar galeria
      </Button>
    </div>
  );
}
