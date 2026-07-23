import { useEffect, useState } from "react";
import { Card, EmptyState, PageHeader, Table, Button, useToast } from "../components";
import { suppliersApi, type Supplier } from "../api";
import { SupplierDetailDrawer } from "./SupplierDetailDrawer";

export function SuppliersPage() {
  const toast = useToast();
  const [rows, setRows] = useState<Supplier[]>([]);
  const [name, setName] = useState("");
  const [country, setCountry] = useState("");
  const [error, setError] = useState("");
  const [selected, setSelected] = useState<Supplier | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);

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

  async function handleCreate(e?: React.FormEvent) {
    e?.preventDefault();
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

  function openSupplier(supplier: Supplier) {
    setSelected(supplier);
    setDrawerOpen(true);
  }

  return (
    <Card>
      <PageHeader title="Fornecedores" />
      {error && <p className="error">{error}</p>}

      <form
        className="inline-form"
        onSubmit={(e) => {
          e.preventDefault();
          void handleCreate();
        }}
      >
        <input placeholder="Nome" value={name} onChange={(e) => setName(e.target.value)} required />
        <input placeholder="País (opcional)" value={country} onChange={(e) => setCountry(e.target.value)} />
        <Button type="button" onClick={() => void handleCreate()}>
          Cadastrar
        </Button>
      </form>

      {rows.length === 0 ? (
        <EmptyState title="Nenhum fornecedor" />
      ) : (
        <>
          <p className="meta">Clique em um fornecedor para editar ou excluir.</p>
          <Table>
            <thead>
              <tr>
                <th>Nome</th>
                <th>País</th>
                <th>Contato</th>
                <th>Moeda padrão</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((s) => (
                <tr
                  key={s.id}
                  className="table-row--clickable"
                  onClick={() => openSupplier(s)}
                  title="Clique para editar"
                >
                  <td>{s.name}</td>
                  <td>{s.country ?? "—"}</td>
                  <td>{s.contact_name ?? s.contact_email ?? "—"}</td>
                  <td>{s.currency_default ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </Table>
        </>
      )}

      <SupplierDetailDrawer
        open={drawerOpen}
        supplier={selected}
        onClose={() => setDrawerOpen(false)}
        onSaved={() => {
          toast.success("Fornecedor atualizado");
          void load();
        }}
        onDeleted={() => {
          toast.success("Fornecedor excluído");
          void load();
        }}
      />
    </Card>
  );
}
