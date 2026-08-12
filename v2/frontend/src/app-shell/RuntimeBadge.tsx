import { useEffect, useState } from "react";

type HealthInfo = {
  runtime_lane?: string;
  app_env?: string;
  logical_database?: string;
  app?: string;
  alembic_head?: string | null;
  alembic_expected?: string;
  schema_ok?: boolean;
};

const BUILD_ID =
  (import.meta.env.VITE_BUILD_ID as string | undefined) ||
  (import.meta.env.MODE === "production" ? "dist" : `vite-${import.meta.env.MODE}`);

function laneFromHealth(h: HealthInfo | null): "Teste" | "Operação" | null {
  if (h?.runtime_lane === "Teste" || h?.runtime_lane === "Operação") return h.runtime_lane;
  if (h?.logical_database?.endsWith("_test")) return "Teste";
  if (h?.logical_database) return "Operação";
  if (import.meta.env.MODE === "test") return "Teste";
  return null;
}

/**
 * Runtime badge — Ambiente: Operação|Teste; técnico só em tooltip.
 */
export function RuntimeBadge() {
  const [health, setHealth] = useState<HealthInfo | null>(null);
  const [fetchFailed, setFetchFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const res = await fetch("/api/health", { credentials: "include" });
        if (!res.ok) {
          if (!cancelled) setFetchFailed(true);
          return;
        }
        const data = (await res.json()) as HealthInfo;
        if (!cancelled) {
          setHealth(data);
          setFetchFailed(false);
        }
      } catch {
        if (!cancelled) setFetchFailed(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const lane = laneFromHealth(health);
  const apiHost = typeof window !== "undefined" ? window.location.host : "";
  const db = health?.logical_database?.trim() || null;
  const alembic = health?.alembic_head?.trim() || null;
  const alembicExpected = health?.alembic_expected?.trim() || null;
  const tooltip = [
    apiHost ? `API ${apiHost}` : null,
    db ? `DB ${db}` : null,
    alembic
      ? `alembic ${alembic}${alembicExpected && alembic !== alembicExpected ? ` (esperado ${alembicExpected})` : ""}`
      : null,
    health?.schema_ok === false ? "SCHEMA DRIFT" : null,
    `build ${BUILD_ID}`,
    health?.app_env ? `env ${health.app_env}` : null,
  ]
    .filter(Boolean)
    .join(" · ");

  const label = lane ? `Ambiente: ${lane}` : fetchFailed ? "Ambiente: indisponível" : "Ambiente: …";

  return (
    <div
      className="shell-runtime-badge"
      data-testid="runtime-badge"
      data-runtime-lane={lane ?? "unknown"}
      data-logical-database={db ?? ""}
      title={tooltip || "Carregando ambiente…"}
    >
      <span
        className={
          lane === "Teste"
            ? "runtime-lane runtime-lane--test"
            : lane === "Operação"
              ? "runtime-lane runtime-lane--ops"
              : "runtime-lane"
        }
      >
        {label}
      </span>
    </div>
  );
}
