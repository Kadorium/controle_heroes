import { useEffect, useState } from "react";
import { Navigate, useParams } from "react-router-dom";
import { ErrorState, LoadingState } from "../../ui";

/** Resolve FundingRequest → ImportProcess (Opção B / J5-C1). */
export function FundingRedirectPage() {
  const { fundingRequestId } = useParams();
  const id = Number(fundingRequestId);
  const [processId, setProcessId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!Number.isFinite(id) || id <= 0) {
      setError("Numerário inválido");
      return;
    }
    let cancelled = false;
    void (async () => {
      try {
        const res = await fetch(`/api/customs/funding-requests/${id}`, {
          credentials: "include",
        });
        if (!res.ok) {
          const t = await res.text();
          throw new Error(t || "Numerário não encontrado");
        }
        const data = (await res.json()) as { process_id: number };
        if (!cancelled) setProcessId(data.process_id);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Erro");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [id]);

  if (error) return <ErrorState message={error} />;
  if (processId == null) return <LoadingState message="Abrindo Numerário…" />;
  return <Navigate to={`/customs/${processId}`} replace />;
}
