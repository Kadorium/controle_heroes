export type FlowStep = { key: string; label: string; value: string | number; href?: string };

export function FlowSteps({ steps }: { steps: FlowStep[] }) {
  return (
    <ol className="dash-flow" data-testid="dash-goods-flow">
      {steps.map((s) => (
        <li key={s.key}>
          <span className="dash-flow-value">{s.value}</span>
          <span className="dash-flow-label">{s.label}</span>
        </li>
      ))}
    </ol>
  );
}
