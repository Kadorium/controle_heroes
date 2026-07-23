import { PageHeader, Card } from "../components";
import { glossarySections } from "../i18n/glossario";

export function GlossaryPage() {
  const sections = glossarySections();

  return (
    <Card>
      <PageHeader
        title="Glossário operacional"
        subtitle="Termos técnicos do sistema e seus rótulos em português para a operação Epic."
      />
      <div className="glossary">
        {sections.map((sec) => (
          <section key={sec.title} className="glossary__section">
            <h2 className="glossary__title">{sec.title}</h2>
            <table className="glossary__table">
              <thead>
                <tr>
                  <th>Código técnico</th>
                  <th>Rótulo operacional (PT)</th>
                </tr>
              </thead>
              <tbody>
                {sec.entries.map((e) => (
                  <tr key={e.code}>
                    <td>
                      <code>{e.code}</code>
                    </td>
                    <td>{e.label}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        ))}
      </div>
    </Card>
  );
}
