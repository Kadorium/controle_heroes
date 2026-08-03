import type { ReactNode } from "react";
import { SectionCard } from "./SectionCard";
import { FORMAT_ABSENCE, formatDateTime } from "./format";
import { auditActionLabel } from "./domainLabels";

export type AuditEntry = {
  id?: string | number;
  action?: string | null;
  at?: string | null;
  actor?: string | null;
  detail?: ReactNode;
};

export type DocumentEntry = {
  id?: string | number;
  name?: string | null;
  uploadedAt?: string | null;
  href?: string | null;
};

type Props = {
  documents?: DocumentEntry[];
  audit?: AuditEntry[];
  documentsTitle?: string;
  auditTitle?: string;
  emptyDocuments?: string;
  emptyAudit?: string;
  className?: string;
};

/** Bloco composto Documentos + Auditoria (§27.7). */
export function AuditDocumentsBlock({
  documents = [],
  audit = [],
  documentsTitle = "Documentos",
  auditTitle = "Auditoria",
  emptyDocuments = "Nenhum documento anexado",
  emptyAudit = "Sem eventos de auditoria",
  className,
}: Props) {
  return (
    <div className={["audit-documents-block", "stack", className].filter(Boolean).join(" ")} data-testid="audit-documents-block">
      <SectionCard title={documentsTitle} data-testid="documents-block">
        {documents.length === 0 ? (
          <p className="muted">{emptyDocuments}</p>
        ) : (
          <table className="mini-table">
            <thead>
              <tr>
                <th>Arquivo</th>
                <th>Enviado em</th>
              </tr>
            </thead>
            <tbody>
              {documents.map((doc, i) => (
                <tr key={doc.id ?? i}>
                  <td>
                    {doc.href ? (
                      <a href={doc.href} target="_blank" rel="noreferrer">
                        {doc.name?.trim() || "Documento"}
                      </a>
                    ) : (
                      doc.name?.trim() || "Documento"
                    )}
                  </td>
                  <td>{formatDateTime(doc.uploadedAt)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </SectionCard>
      <SectionCard title={auditTitle} data-testid="audit-block">
        {audit.length === 0 ? (
          <p className="muted">{emptyAudit}</p>
        ) : (
          <table className="mini-table">
            <thead>
              <tr>
                <th>Ação</th>
                <th>Quando</th>
                <th>Quem</th>
              </tr>
            </thead>
            <tbody>
              {audit.map((entry, i) => (
                <tr key={entry.id ?? i}>
                  <td>
                    {auditActionLabel(entry.action)}
                    {entry.detail ? <div className="muted">{entry.detail}</div> : null}
                  </td>
                  <td>{formatDateTime(entry.at)}</td>
                  <td>{entry.actor?.trim() || FORMAT_ABSENCE}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </SectionCard>
    </div>
  );
}
