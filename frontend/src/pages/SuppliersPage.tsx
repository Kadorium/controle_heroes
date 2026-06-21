import { useEffect, useState } from "react";
import { Card, EmptyState, PageHeader, Table, Button, useToast } from "../components";
import { suppliersApi, type Supplier } from "../api";

export function SuppliersPage() {
  const toast = useToast();
  const [rows, setRows] = useState<Supplier[]>([]);
  const [name, setName] = useState("");
  const [country, setCountry] = useState("");
  const [error, setError] = useState("");

  async function load() {
    try {
      setRows(await suppliersApi.list());
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
      await suppliersApi.create({ name, country: country || undefined });
      setName("");
      setCountry("");
      toast.success("Fornecedor cadastrado");
      await load();
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Erro";
      setError(msg);
      toast.error(msg);
    }
  }

  return (
    <Card>
      <PageHeader title="Fornecedores" />
      {error && <p className="error">{error}</p>}

      <form className="inline-form" onSubmit={handleCreate}>
        <input placeholder="Nome" value={name} onChange={(e) => setName(e.target.value)} required />
        <input placeholder="País (opcional)" value={country} onChange={(e) => setCountry(e.target.value)} />
        <Button type="submit">Cadastrar</Button>
      </form>

      {rows.length === 0 ? (
        <EmptyState title="Nenhum fornecedor" />
      ) : (
        <Table>
          <thead>
            <tr>
              <th>Nome</th>
              <th>País</th>
              <th>Moeda padrão</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((s) => (
              <tr key={s.id}>
                <td>{s.name}</td>
                <td>{s.country ?? "—"}</td>
                <td>{s.currency_default ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
    </Card>
  );
}
