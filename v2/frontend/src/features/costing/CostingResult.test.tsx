import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import type { CostingVersion } from "./costingApi";
import { CostingResult } from "./CostingResult";
const version: CostingVersion = { id: 1, case_id: 1, kind: "REVISED", status: "PUBLISHED", version_number: 3, partial_coverage: false, included_total_brl: "12400", gross_total_brl: "12400", title: "", subtitle: "", pairs: [], products: [{ sku_snapshot: "SKU-A", qty: "20", freight_brl: "0", total_brl: "12400", unit_brl: "620" }], components: [], lines: [], snapshot: { coverage: { coverage: "COMPLETE" } } };
afterEach(cleanup);
it("shows persisted result, invoice quantity, documentary FX and absent freight honestly", () => {
  render(<CostingResult version={version} fxCopy="Câmbio documental. Não é câmbio bancário realizado." />);
  expect(screen.getByTestId("costing-included-total")).toHaveTextContent("12.400");
  expect(screen.getByText("Revisado")).toBeVisible();
  expect(screen.getByText(/base de quantidade faturada/)).toBeVisible();
  const cells = within(screen.getByTestId("costing-products")).getAllByRole("cell");
  expect(cells[1]).toHaveTextContent("20"); expect(cells[3]).toHaveTextContent("—");
  expect(screen.getByTestId("costing-freight-absent")).toBeVisible();
});
it("preserves explicit freight zero only with an included component and exposes partial publication", () => {
  render(<CostingResult version={{ ...version, partial_coverage: true, components: [{ id: 1, component_type: "FRETE_INTERNACIONAL", source_kind: "EXPENSE_LINE", amount_brl: "0", included: true, status: "OK", notes: null, allocation_method: "VALUE" }] }} fxCopy="Documental" />);
  expect(within(screen.getByTestId("costing-products")).getAllByRole("cell")[3]).toHaveTextContent("0,00");
  expect(screen.getByText(/Publicação parcial/)).toBeVisible();
  expect(screen.queryByTestId("costing-freight-absent")).toBeNull();
});
it("keeps absent total and coverage absent; draft partial is not called published", () => {
  const view = render(<CostingResult version={{ ...version, included_total_brl: null, snapshot: {} }} fxCopy="Referência ausente" />);
  expect(screen.getByTestId("costing-included-total")).toHaveTextContent("—");
  expect(screen.getByText("Não informada")).toBeVisible();
  view.rerender(<CostingResult version={{ ...version, status: "DRAFT", partial_coverage: true }} fxCopy="Documental" />);
  expect(screen.getByText(/Prévia parcial/)).toBeVisible();
});
