import { useEffect, useState } from "react";
import { Card, EmptyState, PageHeader, Table, Button, useToast } from "../components";
import { productsApi, type Product } from "../api";

export function ProductsPage() {
  const toast = useToast();
  const [rows, setRows] = useState<Product[]>([]);
  const [sku, setSku] = useState("");
  const [desc, setDesc] = useState("");
  const [error, setError] = useState("");

  async function load() {
    try {
      setRows(await productsApi.list());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro");
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    try {
      await productsApi.create({ sku_code: sku, description: desc });
      setSku("");
      setDesc("");
      toast.success("Produto cadastrado");
      await load();
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Erro";
      setError(msg);
      toast.error(msg);
    }
  }

  return (
    <Card>
      {/* i18n — "Produto" no lugar de "SKU" em rótulos de UI */}
      <PageHeader title="Produtos" />
      {error && <p className="error">{error}</p>}

      <form className="inline-form" onSubmit={handleCreate}>
        <input placeholder="Código do produto" value={sku} onChange={(e) => setSku(e.target.value)} required />
        <input placeholder="Descrição" value={desc} onChange={(e) => setDesc(e.target.value)} required />
        <Button type="submit">Cadastrar produto</Button>
      </form>

      {rows.length === 0 ? (
        <EmptyState title="Nenhum produto cadastrado" />
      ) : (
        <Table>
          <thead>
            <tr>
              <th>Código</th>
              <th>Descrição</th>
              <th>NCM</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((p) => (
              <tr key={p.id}>
                <td>{p.sku_code}</td>
                <td>{p.description}</td>
                <td>{p.ncm ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
    </Card>
  );
}
