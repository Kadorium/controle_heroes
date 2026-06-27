import { EmptyState, Table } from "../../../components";
import type { ProductAuditRow } from "../../../api";
import { emptyDash } from "../../../i18n/glossario";

interface Props {
  audit: ProductAuditRow[];
}

export function HistoryAuditTab({ audit }: Props) {
  if (audit.length === 0) {
    return <EmptyState title="Sem registros de auditoria" />;
  }

  return (
    <Table className="table-dense">
      <thead>
        <tr>
          <th>Data</th>
          <th>Ação</th>
          <th>Campo</th>
          <th>De</th>
          <th>Para</th>
          <th>Motivo</th>
        </tr>
      </thead>
      <tbody>
        {audit.map((a) => (
          <tr key={a.id}>
            <td>{new Date(a.timestamp).toLocaleString("pt-BR")}</td>
            <td>{a.action}</td>
            <td>{a.field_changed ?? emptyDash(null)}</td>
            <td>{a.old_value ?? emptyDash(null)}</td>
            <td>{a.new_value ?? emptyDash(null)}</td>
            <td>{a.justification ?? emptyDash(null)}</td>
          </tr>
        ))}
      </tbody>
    </Table>
  );
}
