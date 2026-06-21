import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { demoApi, importationsApi, type Importation } from "../api";
import { Button, EmptyState, LoadingState, PageHeader, useToast } from "../components";
import { DEMO_SCENARIOS } from "../constants/demoScenarios";

export function DemoGuidePage() {
  const toast = useToast();
  const navigate = useNavigate();
  const [importations, setImportations] = useState<Importation[]>([]);
  const [loading, setLoading] = useState(true);
  const [seeding, setSeeding] = useState(false);

  async function load() {
    setLoading(true);
    try {
      setImportations(await importationsApi.list());
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function seedDemo() {
    setSeeding(true);
    try {
      await demoApi.seed();
      toast.success("Massa demo carregada — 16 cenários disponíveis");
      await load();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Erro ao carregar demo");
    } finally {
      setSeeding(false);
    }
  }

  function resolveId(poNumber: string): number | null {
    const match = importations.find((i) => i.po_number === poNumber);
    return match?.id ?? null;
  }

  return (
    <div>
      <PageHeader
        title="Roteiro de demonstração Epic"
        subtitle="Casos de teste reais da massa demo — sem dados fictícios inventados"
        actions={
          <Button onClick={seedDemo} disabled={seeding}>
            {seeding ? "Carregando..." : "Carregar massa demo"}
          </Button>
        }
      />

      {loading ? (
        <LoadingState label="Buscando cenários..." />
      ) : (
        <div className="demo-grid">
          {DEMO_SCENARIOS.map((s) => {
            const impId = resolveId(s.poNumber);
            return (
              <article key={s.id} className="demo-card">
                <h3>{s.title}</h3>
                <p className="demo-card__po">{s.poNumber}</p>
                <p className="demo-card__desc">{s.description}</p>
                {impId ? (
                  <Button
                    variant="secondary"
                    onClick={() => navigate(s.path ? s.path(impId) : `/importacoes/${impId}/resumo`)}
                  >
                    Abrir cenário
                  </Button>
                ) : (
                  <p className="meta">
                    Cenário não encontrado —{" "}
                    <button type="button" className="link-btn" onClick={seedDemo}>
                      carregar demo
                    </button>
                  </p>
                )}
              </article>
            );
          })}
        </div>
      )}

      <p className="meta demo-footer">
        <Link to="/">← Voltar ao painel</Link>
      </p>
    </div>
  );
}
