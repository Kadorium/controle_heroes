import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import type { User } from "../auth/types";
import { createProduct } from "./catalogApi";
import { buildReturnTo } from "../../navigation/returnState";
import {
  Button,
  ContextBreadcrumb,
  ErrorState,
  FormField,
  Notice,
  PageHeader,
  SectionCard,
  TextInput,
} from "../../ui";

type Props = { user: User };

function canWrite(user: User) {
  return user.role === "admin" || (user.permissions ?? []).includes("catalog:write");
}

export function ProductCreatePage({ user }: Props) {
  const nav = useNavigate();
  const listReturn = buildReturnTo("/catalog/products");
  const [sku, setSku] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (!canWrite(user)) return <ErrorState message="Sem permissão para criar produtos." />;

  async function onSubmit() {
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      const p = await createProduct({ sku: sku.trim(), description: description.trim() });
      nav(`/catalog/products/${p.id}`, { replace: true });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao criar produto");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="panel dense" data-testid="product-create-page">
      <ContextBreadcrumb
        items={[
          { label: "Produtos", to: listReturn },
          { label: "Novo" },
        ]}
      />
      <PageHeader
        title="Novo produto"
        subtitle="SKU e descrição bastam para começar. O restante pode ser preenchido na ficha."
        actions={
          <Link className="ui-button ui-button--secondary" to={listReturn}>
            Voltar
          </Link>
        }
      />
      {error ? (
        <Notice tone="danger" className="error">
          {error}
        </Notice>
      ) : null}
      <SectionCard title="Essenciais">
        <div className="form-grid">
          <FormField label="SKU" htmlFor="product-sku" required>
            <TextInput
              id="product-sku"
              data-testid="product-sku"
              value={sku}
              onChange={(e) => setSku(e.target.value)}
            />
          </FormField>
          <FormField label="Descrição" htmlFor="product-desc" required className="span-2">
            <TextInput
              id="product-desc"
              data-testid="product-description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </FormField>
        </div>
        <div className="actions">
          <Button
            type="button"
            busy={busy}
            data-testid="product-create-submit"
            onClick={() => void onSubmit()}
            disabled={!sku.trim() || !description.trim()}
          >
            Criar
          </Button>
        </div>
      </SectionCard>
    </section>
  );
}
