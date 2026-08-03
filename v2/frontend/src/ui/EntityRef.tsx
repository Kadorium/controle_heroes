/** Referência operacional: nome/código primário; ID só secundário. */

type Props = {
  primary: string | null | undefined;
  secondaryId?: string | number | null;
  /** Quando primary ausente: texto explícito (default `—`). */
  missingLabel?: string;
  className?: string;
  "data-testid"?: string;
};

export function EntityRef({
  primary,
  secondaryId,
  missingLabel = "—",
  className,
  "data-testid": testId = "entity-ref",
}: Props) {
  const name = typeof primary === "string" ? primary.trim() : primary;
  const hasName = Boolean(name);
  const showId =
    secondaryId !== null &&
    secondaryId !== undefined &&
    secondaryId !== "" &&
    hasName;

  return (
    <span className={className ? `entity-ref ${className}` : "entity-ref"} data-testid={testId}>
      <span className="entity-ref-primary">{hasName ? name : missingLabel}</span>
      {showId ? <span className="entity-ref-secondary"> · id {String(secondaryId)}</span> : null}
    </span>
  );
}
