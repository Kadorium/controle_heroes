import { useEffect, useState } from "react";
import { Button } from "../components";
import { DEFAULT_IMPORT_CURRENCY } from "../constants/currency";
import { suppliersApi, type Supplier } from "../api";

interface Props {
  open: boolean;
  supplier: Supplier | null;
  onClose: () => void;
  onSaved: () => void;
  onDeleted: () => void;
}

export function SupplierDetailDrawer({ open, supplier, onClose, onSaved, onDeleted }: Props) {
  const [name, setName] = useState("");
  const [country, setCountry] = useState("");
  const [taxId, setTaxId] = useState("");
  const [contactName, setContactName] = useState("");
  const [contactEmail, setContactEmail] = useState("");
  const [currencyDefault, setCurrencyDefault] = useState(DEFAULT_IMPORT_CURRENCY);
  const [cancelReason, setCancelReason] = useState("");
  const [showCancel, setShowCancel] = useState(false);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!open || !supplier) return;
    setName(supplier.name);
    setCountry(supplier.country ?? "");
    setTaxId(supplier.tax_id ?? "");
    setContactName(supplier.contact_name ?? "");
    setContactEmail(supplier.contact_email ?? "");
    setCurrencyDefault(supplier.currency_default ?? DEFAULT_IMPORT_CURRENCY);
    setCancelReason("");
    setShowCancel(false);
    setError("");
  }, [open, supplier]);

  async function save() {
    if (!supplier) return;
    setSaving(true);
    setError("");
    try {
      await suppliersApi.update(supplier.id, {
        name: name.trim(),
        country: country.trim() || null,
        tax_id: taxId.trim() || null,
        contact_name: contactName.trim() || null,
        contact_email: contactEmail.trim() || null,
        currency_default: currencyDefault || DEFAULT_IMPORT_CURRENCY,
      });
      onSaved();
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao salvar");
    } finally {
      setSaving(false);
    }
  }

  async function remove() {
    if (!supplier || cancelReason.trim().length < 3) {
      setError("Informe o motivo da exclusão (mín. 3 caracteres)");
      return;
    }
    setDeleting(true);
    setError("");
    try {
      await suppliersApi.cancel(supplier.id, cancelReason.trim());
      onDeleted();
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao excluir");
    } finally {
      setDeleting(false);
    }
  }

  if (!open || !supplier) return null;

  return (
    <>
      <div className="drawer-back drawer-back--show" onClick={onClose} />
      <aside className="drawer drawer--wide drawer--show">
        <h3>Editar fornecedor</h3>
        <p className="drawer__sub">Clique em Salvar para persistir alterações.</p>
        {error && <p className="error">{error}</p>}

        <div className="form-stack">
          <label>
            Nome
            <input value={name} onChange={(e) => setName(e.target.value)} required />
          </label>
          <label>
            País
            <input value={country} onChange={(e) => setCountry(e.target.value)} placeholder="Ex.: CN, IT" />
          </label>
          <label>
            ID fiscal / VAT
            <input value={taxId} onChange={(e) => setTaxId(e.target.value)} placeholder="Opcional" />
          </label>
          <label>
            Contato
            <input value={contactName} onChange={(e) => setContactName(e.target.value)} placeholder="Nome do contato" />
          </label>
          <label>
            E-mail
            <input
              type="email"
              value={contactEmail}
              onChange={(e) => setContactEmail(e.target.value)}
              placeholder="contato@fornecedor.com"
            />
          </label>
          <label>
            Moeda padrão
            <select value={currencyDefault} onChange={(e) => setCurrencyDefault(e.target.value)}>
              <option value="EUR">EUR</option>
              <option value="BRL">BRL</option>
            </select>
          </label>
        </div>

        <div className="drawer__actions">
          <Button type="button" variant="secondary" onClick={onClose}>
            Fechar
          </Button>
          <Button type="button" onClick={() => void save()} disabled={saving || !name.trim()}>
            Salvar
          </Button>
        </div>

        <section className="drawer__danger">
          {!showCancel ? (
            <Button type="button" variant="ghost" onClick={() => setShowCancel(true)}>
              Excluir fornecedor
            </Button>
          ) : (
            <>
              <p className="drawer__sub">
                A exclusão anula o cadastro, mas preserva o histórico em ordens já vinculadas.
              </p>
              <label>
                Motivo da exclusão
                <textarea
                  value={cancelReason}
                  onChange={(e) => setCancelReason(e.target.value)}
                  rows={3}
                  placeholder="Ex.: cadastro de teste"
                />
              </label>
              <div className="drawer__actions">
                <Button type="button" variant="secondary" onClick={() => setShowCancel(false)}>
                  Cancelar
                </Button>
                <Button
                  type="button"
                  variant="danger"
                  onClick={() => void remove()}
                  disabled={deleting || cancelReason.trim().length < 3}
                >
                  Confirmar exclusão
                </Button>
              </div>
            </>
          )}
        </section>
      </aside>
    </>
  );
}
