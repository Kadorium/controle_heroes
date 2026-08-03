type Props = {
  offset: number;
  limit: number;
  total?: number | null;
  loadedCount?: number;
  className?: string;
};

/** Resumo de paginação em linguagem de produto (substitui `offset 0 · limite 50`). */
export function PaginationSummary({
  offset,
  limit,
  total,
  loadedCount,
  className,
}: Props) {
  const from = loadedCount === 0 ? 0 : offset + 1;
  const to = offset + (loadedCount ?? 0);
  let text: string;
  if (typeof total === "number" && total >= 0) {
    text =
      total === 0
        ? "Nenhum registro"
        : `Exibindo ${from}–${to} de ${total}`;
  } else if ((loadedCount ?? 0) === 0 && offset === 0) {
    text = "Nenhum registro";
  } else {
    text = `Exibindo ${from}–${to}`;
    if (limit > 0) text += ` · até ${limit} por página`;
  }

  return (
    <p className={["pagination-summary", "muted", className].filter(Boolean).join(" ")} data-testid="pagination-summary">
      {text}
    </p>
  );
}
