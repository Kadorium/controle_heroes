const PHASES = [
  { key: "despachar", label: "A despachar", hash: "#despachar" },
  { key: "embarques", label: "Embarques", hash: "#embarques" },
  { key: "transito", label: "Em trânsito", hash: "#transito" },
  { key: "aduana", label: "Aduana", hash: "#aduana" },
  { key: "entreposto", label: "Entreposto", hash: "#entreposto" },
  { key: "nacionalizacao", label: "Nacionalização", hash: "#nacionalizacao" },
  { key: "estoque", label: "Estoque Epic", hash: "#estoque" },
];

interface Props {
  counts: Record<string, number>;
}

export function LogisticsPhaseRail({ counts }: Props) {
  return (
    <nav className="anchor-nav logistics-phase-rail" aria-label="Fases logísticas">
      {PHASES.map((p) => {
        const n = counts[p.key] ?? 0;
        return (
          <a key={p.key} href={p.hash} className="logistics-phase-link">
            {p.label}
            {n > 0 && <span className="logistics-phase-badge">{n}</span>}
          </a>
        );
      })}
    </nav>
  );
}
