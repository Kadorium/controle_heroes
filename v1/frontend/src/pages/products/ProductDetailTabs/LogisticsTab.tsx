import { Button } from "../../../components";
import type { Product } from "../../../api";

interface Props {
  product: Product;
  onSave: (data: object) => Promise<void>;
}

export function LogisticsTab({ product, onSave }: Props) {
  return (
    <div className="form-grid">
      <label>
        Peso (kg)
        <input defaultValue={product.weight_kg ?? ""} id="w" />
      </label>
      <label>
        Volume (m³)
        <input defaultValue={product.volume_m3 ?? ""} id="v" />
      </label>
      <Button
        onClick={() =>
          void onSave({
            weight_kg: (document.getElementById("w") as HTMLInputElement).value || null,
            volume_m3: (document.getElementById("v") as HTMLInputElement).value || null,
          })
        }
      >
        Salvar logística
      </Button>
    </div>
  );
}
