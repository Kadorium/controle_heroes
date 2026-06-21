import { useEffect, useState } from "react";
import { Button, Card, Table } from "../components";
import {
  customsApi,
  landedCostApi,
  stockApi,
  type CustomsDocument,
  type LandedCostVersion,
  type QuantityChain,
  type Tax,
} from "../api";

interface Props {
  importationId: number;
  items: Array<{ id: number; quantity_ordered: number | null }>;
}

export function CustomsStockPanel({ importationId, items }: Props) {
  const [docs, setDocs] = useState<CustomsDocument[]>([]);
  const [taxes, setTaxes] = useState<Tax[]>([]);
  const [chain, setChain] = useState<QuantityChain[]>([]);
  const [versions, setVersions] = useState<LandedCostVersion[]>([]);
  const [error, setError] = useState("");
  const [docType, setDocType] = useState("DI");
  const [docNumber, setDocNumber] = useState("");
  const [taxType, setTaxType] = useState("II");
  const [taxAmount, setTaxAmount] = useState("");
  const [natQty, setNatQty] = useState("");
  const [lcMethod, setLcMethod] = useState("VALUE");

  async function load() {
    try {
      const [d, t, c, v] = await Promise.all([
        customsApi.listDocuments(importationId),
        customsApi.listTaxes(importationId),
        stockApi.quantityChain(importationId),
        landedCostApi.listVersions(importationId),
      ]);
      setDocs(d);
      setTaxes(t);
      setChain(c);
      setVersions(v);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao carregar");
    }
  }

  useEffect(() => {
    if (!importationId || Number.isNaN(importationId)) {
      setDocs([]);
      setTaxes([]);
      setChain([]);
      setVersions([]);
      return;
    }
    setDocs([]);
    setTaxes([]);
    setChain([]);
    setVersions([]);
    load();
  }, [importationId]);

  useEffect(() => {
    const hash = window.location.hash;
    if (!hash) return;
    const timer = window.setTimeout(() => {
      document.querySelector(hash)?.scrollIntoView({ behavior: "smooth", block: "start" });
    }, 100);
    return () => window.clearTimeout(timer);
  }, [docs, taxes, chain, versions]);

  async function createDoc(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    try {
      const staging = await customsApi.createDocument({
        importation_id: importationId,
        document_type: docType,
        document_number: docNumber,
        document_data_json: { source: "ui", staging: true },
      });
      await customsApi.approveDocument(staging.id, {
        official_data_json: { number: docNumber, approved_via: "ui" },
      });
      setDocNumber("");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro");
    }
  }

  async function createTax(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    const official = docs.find((d) => d.status === "OFFICIAL");
    if (!official) {
      setError("Registre e aprove DI/DUIMP antes do imposto");
      return;
    }
    try {
      await customsApi.createTax({
        importation_id: importationId,
        customs_document_id: official.id,
        tax_type: taxType,
        amount: taxAmount,
        source_document_attachment_id: 1,
      });
      setTaxAmount("");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro");
    }
  }

  async function nationalize(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    const official = docs.find((d) => d.status === "OFFICIAL");
    const itemId = items[0]?.id;
    if (!official || !itemId) {
      setError("DI/DUIMP oficial e item necessários");
      return;
    }
    try {
      await stockApi.createNationalization({
        importation_id: importationId,
        customs_document_id: official.id,
        items: [{ importation_item_id: itemId, quantity_nationalized: Number(natQty) }],
      });
      setNatQty("");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro");
    }
  }

  async function createLc(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    try {
      await landedCostApi.createVersion({
        importation_id: importationId,
        version_type: versions.length ? "FINAL" : "INITIAL",
        allocation_method: lcMethod,
      });
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro");
    }
  }

  return (
    <div>
      {error && <p className="error">{error}</p>}

      <nav className="anchor-nav">
        <a href="#di-duimp">DI/DUIMP</a>
        <a href="#impostos">Impostos</a>
        <a href="#nacionalizacao">Nacionalização</a>
        <a href="#landed-cost">Landed cost</a>
      </nav>

      <Card id="di-duimp" title="DI / DUIMP" compact className="stacked-section">
        <form className="inline-form" onSubmit={createDoc}>
          <select value={docType} onChange={(e) => setDocType(e.target.value)}>
            <option value="DI">DI</option>
            <option value="DUIMP">DUIMP</option>
          </select>
          <input
            placeholder="Número"
            value={docNumber}
            onChange={(e) => setDocNumber(e.target.value)}
            required
          />
          <Button type="submit">Registrar e aprovar</Button>
        </form>
        <Table>
          <thead>
            <tr>
              <th>Tipo</th>
              <th>Número</th>
              <th>Status</th>
              <th>Bruto vs Oficial</th>
            </tr>
          </thead>
          <tbody>
            {docs.map((d) => (
              <tr key={d.id}>
                <td>{d.document_type}</td>
                <td>{d.document_number}</td>
                <td>{d.status}</td>
                <td>
                  {d.document_data_json ? "staging" : "—"} /{" "}
                  {d.official_data_json ? "official" : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      </Card>

      <Card id="impostos" title="Impostos" compact className="stacked-section">
        <form className="inline-form" onSubmit={createTax}>
          <select value={taxType} onChange={(e) => setTaxType(e.target.value)}>
            {["II", "IPI", "PIS", "COFINS", "ICMS", "OTHER"].map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
          <input
            placeholder="Valor"
            value={taxAmount}
            onChange={(e) => setTaxAmount(e.target.value)}
            required
          />
          <Button type="submit">Registrar imposto</Button>
        </form>
        <Table>
          <thead>
            <tr>
              <th>Tipo</th>
              <th>Valor</th>
              <th>Moeda</th>
            </tr>
          </thead>
          <tbody>
            {taxes.map((t) => (
              <tr key={t.id}>
                <td>{t.tax_type}</td>
                <td>{t.amount}</td>
                <td>{t.currency}</td>
              </tr>
            ))}
          </tbody>
        </Table>
      </Card>

      <Card id="nacionalizacao" title="Nacionalização" compact className="stacked-section">
        <form className="inline-form" onSubmit={nationalize}>
          <input
            placeholder="Qtd nacionalizada"
            value={natQty}
            onChange={(e) => setNatQty(e.target.value)}
            required
          />
          <Button type="submit">Nacionalizar</Button>
        </form>
        <Table>
          <thead>
            <tr>
              <th>Item</th>
              <th>Pedido</th>
              <th>Embarcado</th>
              <th>Nacionalizado</th>
              <th>Estoque</th>
            </tr>
          </thead>
          <tbody>
            {chain.map((c) => (
              <tr key={c.importation_item_id}>
                <td>{c.importation_item_id}</td>
                <td>{c.quantity_ordered ?? "—"}</td>
                <td>{c.quantity_shipped}</td>
                <td>{c.quantity_nationalized}</td>
                <td>{c.quantity_stocked}</td>
              </tr>
            ))}
          </tbody>
        </Table>
      </Card>

      <Card id="landed-cost" title="Landed cost" compact className="stacked-section">
        <form className="inline-form" onSubmit={createLc}>
          <select value={lcMethod} onChange={(e) => setLcMethod(e.target.value)}>
            <option value="VALUE">Por valor</option>
            <option value="QUANTITY">Por quantidade</option>
            <option value="EQUAL">Igual</option>
          </select>
          <Button type="submit">Calcular versão</Button>
        </form>
        <Table>
          <thead>
            <tr>
              <th>v#</th>
              <th>Tipo</th>
              <th>Total</th>
              <th>Atual</th>
              <th>Trigger</th>
            </tr>
          </thead>
          <tbody>
            {versions.map((v) => (
              <tr key={v.id}>
                <td>{v.version_number}</td>
                <td>{v.version_type}</td>
                <td>{v.total_cost ?? "—"}</td>
                <td>{v.is_current_version ? "sim" : "—"}</td>
                <td>{v.trigger_event ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </Table>
      </Card>
    </div>
  );
}
