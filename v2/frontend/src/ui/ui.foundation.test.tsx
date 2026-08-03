import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import {
  Button,
  EntityRef,
  FilterChip,
  MoneyDisplay,
  OperationalTable,
  PageHeader,
  RowLink,
  StatusBadge,
} from "./index";

describe("V0 ui foundation", () => {
  it("MoneyDisplay formata e StatusBadge usa label PT", () => {
    render(
      <MemoryRouter>
        <PageHeader title="Pagamentos" />
        <StatusBadge status="REGISTERED" entity="payment" />
        <MoneyDisplay amount="400.0000" currency="EUR" />
        <MoneyDisplay amount={null} />
      </MemoryRouter>,
    );
    expect(screen.getByTestId("page-header")).toHaveTextContent("Pagamentos");
    expect(screen.getByTestId("status-badge")).toHaveTextContent("Registrado");
    expect(screen.getByTestId("status-badge")).not.toHaveTextContent("REGISTERED");
    expect(screen.getAllByTestId("money")[0]).toHaveTextContent("EUR 400,00");
    expect(screen.getByText("—")).toBeTruthy();
  });

  it("EntityRef prioriza nome e não inventa identidade por id", () => {
    const { rerender } = render(<EntityRef primary="Heroes Metalúrgica LTDA" secondaryId={20} />);
    expect(screen.getByTestId("entity-ref")).toHaveTextContent("Heroes Metalúrgica LTDA");
    expect(screen.getByTestId("entity-ref")).toHaveTextContent("id 20");
    expect(screen.getByTestId("entity-ref")).not.toHaveTextContent("#20");

    rerender(<EntityRef primary={null} missingLabel="Fornecedor não identificado" />);
    expect(screen.getByTestId("entity-ref")).toHaveTextContent("Fornecedor não identificado");
  });

  it("RowLink é Link com classe DS", () => {
    render(
      <MemoryRouter>
        <RowLink to="/payments/1">Abrir</RowLink>
      </MemoryRouter>,
    );
    const link = screen.getByTestId("row-link");
    expect(link).toHaveAttribute("href", "/payments/1");
    expect(link.className).toContain("row-link");
  });

  it("exporta Button / FilterChip / OperationalTable", () => {
    render(
      <>
        <Button>Salvar</Button>
        <FilterChip pressed>Abertos</FilterChip>
        <OperationalTable density="finance">
          <tbody>
            <tr>
              <td>1</td>
            </tr>
          </tbody>
        </OperationalTable>
      </>,
    );
    expect(screen.getByRole("button", { name: "Salvar" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Abertos" })).toHaveAttribute("aria-pressed", "true");
    expect(document.querySelector(".operational-table.density-finance")).toBeTruthy();
  });

  it("OperationalTable columns opt-in omite P2 em compact", () => {
    type R = { id: string; name: string };
    const columns = [
      {
        id: "name",
        header: "Nome",
        visibility: "always" as const,
        priority: 0 as const,
        minWidth: "8rem",
        cell: (r: R) => r.name,
      },
      {
        id: "extra",
        header: "Extra",
        visibility: "wide" as const,
        priority: 2 as const,
        minWidth: "6rem",
        cell: () => "x",
      },
    ];
    render(
      <OperationalTable
        columns={columns}
        rows={[{ id: "1", name: "Alpha" }]}
        getRowId={(r) => r.id}
        layoutMode="compact"
        data-testid="ot-cols"
      />,
    );
    expect(screen.getByText("Nome")).toBeTruthy();
    expect(screen.getByText("Alpha")).toBeTruthy();
    expect(screen.queryByText("Extra")).toBeNull();
    expect(document.querySelector(".queue-shell")).toBeTruthy();
    expect(document.querySelector("colgroup col")).toBeTruthy();
  });
});
