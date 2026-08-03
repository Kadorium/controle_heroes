import { useCallback, useEffect, useState } from "react";
import type { User } from "../auth/types";
import {
  activateDoganaleVersion,
  createDoganaleVersion,
  getDoganale,
  listDivergences,
  registerDivergence,
  replaceDoganaleLines,
  supersedeDoganaleVersion,
  type DoganaleSummary,
  type DoganaleVersion,
  type Divergence,
} from "./customsApi";
import { canWriteCustoms, conflictMessage } from "./customsPermissions";
import {
  Button,
  EmptyState,
  ErrorState,
  FormField,
  LoadingState,
  Notice,
  SectionCard,
  TextInput,
} from "../../ui";

type Props = {
  user: User;
  processId: number;
};

export function DoganalePanel({ user, processId }: Props) {
  const writable = canWriteCustoms(user);
  const [summary, setSummary] = useState<DoganaleSummary | null | undefined>(undefined);
  const [divergences, setDivergences] = useState<Divergence[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [ncm, setNcm] = useState("84713012");
  const [description, setDescription] = useState("Item doganale");
  const [quantity, setQuantity] = useState("10");
  const [unitPrice, setUnitPrice] = useState("100");
  const [divMsg, setDivMsg] = useState("Divergência de quantidade vs invoice");

  const reload = useCallback(async () => {
    const [d, divs] = await Promise.all([getDoganale(processId), listDivergences(processId)]);
    setSummary(d);
    setDivergences(divs);
  }, [processId]);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      setError(null);
      try {
        await reload();
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Erro");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [reload]);

  async function run(action: () => Promise<void>) {
    setBusy(true);
    setError(null);
    try {
      await action();
      await reload();
    } catch (e) {
      setError(conflictMessage(e as Error & { status?: number; code?: string }));
    } finally {
      setBusy(false);
    }
  }

  if (error && summary === undefined) return <ErrorState message={error} />;
  if (summary === undefined) return <LoadingState message="Carregando Doganale…" />;

  const versions = summary?.versions ?? [];
  const current = versions.find((v) => v.is_current) ?? null;
  const draft = versions.find((v) => v.status === "DRAFT" && !v.is_current) ?? null;
  const editable: DoganaleVersion | null =
    draft ?? (current?.status === "DRAFT" ? current : null) ?? null;

  return (
    <div data-testid="customs-doganale-panel">
      {error ? (
        <Notice tone="danger" data-testid="doganale-error">
          {error}
        </Notice>
      ) : null}

      <SectionCard title="Doganale">
        {!summary ? (
          <EmptyState
            title="Sem Doganale"
            message="Crie a primeira versão declaratória para este processo."
          />
        ) : (
          <p>
            Atual:{" "}
            <strong data-testid="doganale-current">
              {current ? `v${current.version_number} (${current.status})` : "—"}
            </strong>
          </p>
        )}

        {writable ? (
          <div className="form-actions">
            <Button
              type="button"
              disabled={busy}
              data-testid="doganale-create-version"
              onClick={() =>
                void run(async () => {
                  await createDoganaleVersion(processId, {
                    notes: "Nova versão",
                    copy_from_current: false,
                  });
                })
              }
            >
              Criar versão
            </Button>
            {current && current.status === "ACTIVE" ? (
              <Button
                type="button"
                disabled={busy}
                data-testid="doganale-supersede"
                onClick={() =>
                  void run(async () => {
                    await supersedeDoganaleVersion(processId, current.id, {
                      expected_version: current.version,
                      notes: "Retificação",
                    });
                  })
                }
              >
                Retificar (supersede)
              </Button>
            ) : null}
          </div>
        ) : null}
      </SectionCard>

      {editable && writable ? (
        <SectionCard title={`Editar linhas — v${editable.version_number} (DRAFT)`}>
          <div className="form-actions">
            <FormField label="NCM">
              <TextInput value={ncm} onChange={(e) => setNcm(e.target.value)} data-testid="doganale-ncm" />
            </FormField>
            <FormField label="Descrição">
              <TextInput
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                data-testid="doganale-desc"
              />
            </FormField>
            <FormField label="Quantidade">
              <TextInput
                value={quantity}
                onChange={(e) => setQuantity(e.target.value)}
                data-testid="doganale-qty"
              />
            </FormField>
            <FormField label="Preço unit.">
              <TextInput
                value={unitPrice}
                onChange={(e) => setUnitPrice(e.target.value)}
                data-testid="doganale-price"
              />
            </FormField>
            <Button
              type="button"
              disabled={busy}
              data-testid="doganale-save-lines"
              onClick={() =>
                void run(async () => {
                  await replaceDoganaleLines(processId, editable.id, {
                    expected_version: editable.version,
                    lines: [
                      {
                        position: 1,
                        ncm,
                        description,
                        quantity: quantity.trim() || null,
                        unit: "UN",
                        currency: "EUR",
                        unit_price: unitPrice.trim() || null,
                      },
                    ],
                  });
                })
              }
            >
              Salvar linhas
            </Button>
            <Button
              type="button"
              disabled={busy || editable.lines.length === 0}
              data-testid="doganale-activate"
              onClick={() =>
                void run(async () => {
                  await activateDoganaleVersion(processId, editable.id, {
                    expected_version: editable.version,
                  });
                })
              }
            >
              Ativar
            </Button>
          </div>
        </SectionCard>
      ) : null}

      <SectionCard title="Histórico de versões">
        {versions.length === 0 ? (
          <EmptyState title="Nenhuma versão" message="Ainda não há versões Doganale." />
        ) : (
          <ul data-testid="doganale-history">
            {versions.map((v) => (
              <li key={v.id} data-testid={`doganale-version-${v.version_number}`}>
                v{v.version_number} · {v.status}
                {v.is_current ? " · current" : ""} · {v.lines.length} linha(s)
                {v.lines[0]?.description ? ` · ${v.lines[0].description}` : ""}
                {v.document_id ? ` · doc #${v.document_id}` : ""}
              </li>
            ))}
          </ul>
        )}
      </SectionCard>

      <SectionCard title="Divergências">
        <ul data-testid="doganale-divergences">
          {divergences.map((d) => (
            <li key={d.id}>
              [{d.severity}] {d.kind}: {d.message}
              {d.expected_value || d.actual_value
                ? ` (esp=${d.expected_value ?? "—"} / atu=${d.actual_value ?? "—"})`
                : ""}
            </li>
          ))}
        </ul>
        {writable ? (
          <div className="form-actions">
            <FormField label="Mensagem">
              <TextInput
                value={divMsg}
                onChange={(e) => setDivMsg(e.target.value)}
                data-testid="doganale-div-msg"
              />
            </FormField>
            <Button
              type="button"
              disabled={busy || !divMsg.trim()}
              data-testid="doganale-add-divergence"
              onClick={() =>
                void run(async () => {
                  await registerDivergence(processId, {
                    kind: "QTY",
                    message: divMsg,
                    severity: "WARN",
                    doganale_version_id: current?.id ?? editable?.id ?? null,
                    field_name: "quantity",
                    expected_value: "10",
                    actual_value: quantity || "9",
                  });
                })
              }
            >
              Registrar divergência
            </Button>
          </div>
        ) : null}
      </SectionCard>
    </div>
  );
}
