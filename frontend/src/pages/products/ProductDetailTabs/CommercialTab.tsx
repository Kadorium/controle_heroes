import { Button } from "../../../components";
import type { Product } from "../../../api";

interface Props {
  product: Product;
  onSave: (data: object) => Promise<void>;
}

export function CommercialTab({ product, onSave }: Props) {
  return (
    <div className="form-stack">
      <textarea defaultValue={product.commercial_notes ?? ""} id="notes" rows={6} placeholder="Notas comerciais" />
      <Button
        onClick={() =>
          void onSave({ commercial_notes: (document.getElementById("notes") as HTMLTextAreaElement).value || null })
        }
      >
        Salvar
      </Button>
    </div>
  );
}
