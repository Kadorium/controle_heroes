import { Button, useToast } from "../../../components";
import type { Product } from "../../../api";

interface Props {
  product: Product;
  onSave: (data: object) => Promise<void>;
}

export function FiscalCustomsTab({ product, onSave }: Props) {
  const toast = useToast();

  return (
    <div className="form-grid">
      <label>
        NCM
        <input defaultValue={product.ncm ?? ""} id="ncm" />
      </label>
      <label>
        Descrição fiscal
        <textarea defaultValue={product.fiscal_description ?? ""} id="fd" rows={3} />
      </label>
      <label>
        País origem
        <input defaultValue={product.country_of_origin ?? ""} id="co" />
      </label>
      <label>
        Unidade
        <input defaultValue={product.unit_of_measure ?? ""} id="um" />
      </label>
      <label className="checkbox-row">
        <input type="checkbox" defaultChecked={product.fiscal_review_required} id="fr" />
        Revisão fiscal
      </label>
      <Button
        onClick={() => {
          const ncmVal = (document.getElementById("ncm") as HTMLInputElement).value;
          const body: Record<string, unknown> = {
            ncm: ncmVal || null,
            fiscal_description: (document.getElementById("fd") as HTMLTextAreaElement).value || null,
            country_of_origin: (document.getElementById("co") as HTMLInputElement).value || null,
            unit_of_measure: (document.getElementById("um") as HTMLInputElement).value || null,
            fiscal_review_required: (document.getElementById("fr") as HTMLInputElement).checked,
          };
          if (product.used_in_importations && ncmVal !== (product.ncm ?? "")) {
            const r = prompt("Motivo da alteração de NCM (obrigatório):");
            if (!r || r.length < 3) {
              toast.error("Motivo obrigatório");
              return;
            }
            body.ncm_change_reason = r;
          }
          void onSave(body);
        }}
      >
        Salvar fiscal
      </Button>
    </div>
  );
}
