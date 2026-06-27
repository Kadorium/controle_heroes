import { useState } from "react";
import { Button, Card, Table } from "../../../../components";
import type { CustomsDocument, Tax } from "../../../../api";
import { formatMoney } from "../../../../i18n/glossario";

interface Props {
  docs: CustomsDocument[];
  taxes: Tax[];
  onCreateDoc: (docType: string, docNumber: string) => Promise<void>;
  onCreateTax: (taxType: string, amount: string) => Promise<void>;
}

export function CustomsSection({ docs, taxes, onCreateDoc, onCreateTax }: Props) {
  const [docType, setDocType] = useState("DI");
  const [docNumber, setDocNumber] = useState("");
  const [taxType, setTaxType] = useState("II");
  const [taxAmount, setTaxAmount] = useState("");

  return (
    <>
      <Card id="aduana" title="DI / DUIMP" compact className="stacked-section logistics-phase">
        <form
          className="inline-form"
          onSubmit={async (e) => {
            e.preventDefault();
            await onCreateDoc(docType, docNumber);
            setDocNumber("");
          }}
        >
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
            </tr>
          </thead>
          <tbody>
            {docs.map((d) => (
              <tr key={d.id}>
                <td>{d.document_type}</td>
                <td>{d.document_number}</td>
                <td>{d.status}</td>
              </tr>
            ))}
          </tbody>
        </Table>
      </Card>

      <Card id="impostos" title="Impostos" compact className="stacked-section logistics-phase">
        <form
          className="inline-form"
          onSubmit={async (e) => {
            e.preventDefault();
            await onCreateTax(taxType, taxAmount);
            setTaxAmount("");
          }}
        >
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
                <td className="num">{formatMoney(t.amount, t.currency)}</td>
                <td>{t.currency}</td>
              </tr>
            ))}
          </tbody>
        </Table>
      </Card>
    </>
  );
}
