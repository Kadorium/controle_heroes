import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import {
  AuditDocumentsBlock,
  Button,
  EmptyState,
  ErrorState,
  FileUpload,
  FormField,
  MoneyInput,
  Notice,
  PaginationSummary,
  parseMoneyInput,
  RateInput,
  RowAction,
  SectionCard,
  SelectField,
  SummaryGrid,
  TextInput,
  roleLabel,
} from "./index";

describe("VF ui foundation", () => {
  it("parseMoneyInput aceita pt-BR e ponto", () => {
    expect(parseMoneyInput("1.234,56")).toBe("1234.56");
    expect(parseMoneyInput("400.00")).toBe("400.00");
    expect(parseMoneyInput("")).toBe("");
  });

  it("MoneyInput formata no blur e emite ponto", () => {
    const onValueChange = vi.fn();
    render(<MoneyInput value="400.0000" onValueChange={onValueChange} currency="EUR" />);
    const input = screen.getByRole("textbox");
    expect(input).toHaveValue("400,00");
    fireEvent.focus(input);
    fireEvent.change(input, { target: { value: "250,50" } });
    fireEvent.blur(input);
    expect(onValueChange).toHaveBeenCalledWith("250.50");
  });

  it("RateInput preserva casas além de 2", () => {
    const onValueChange = vi.fn();
    const { container } = render(
      <RateInput value="6.123456" onValueChange={onValueChange} fractionDigits={6} />,
    );
    expect(container.querySelector(".rate-input")).toHaveValue("6,123456");
  });

  it("SelectField / TextInput / FormField / FileUpload renderizam sem default browser-looking file", () => {
    const onFile = vi.fn();
    render(
      <FormField label="Moeda" htmlFor="cur">
        <SelectField
          id="cur"
          options={[
            { value: "EUR", label: "EUR" },
            { value: "BRL", label: "BRL" },
          ]}
          defaultValue="EUR"
        />
        <TextInput aria-label="ref" />
        <FileUpload data-testid="doc" onFileChange={onFile} />
      </FormField>,
    );
    expect(screen.getByRole("combobox")).toHaveClass("ds-select");
    expect(screen.getByTestId("doc")).toHaveClass("file-upload-input");
    expect(screen.getByTestId("doc-name")).toHaveTextContent("Nenhum arquivo selecionado");
    expect(screen.getByRole("button", { name: "Anexar arquivo" })).toBeTruthy();
  });

  it("SectionCard / SummaryGrid / Notice / PaginationSummary", () => {
    render(
      <>
        <SectionCard title="Resumo" actions={<Button variant="ghost">Ação</Button>}>
          <SummaryGrid items={[{ label: "Saldo", value: "EUR 10,00" }]} />
        </SectionCard>
        <Notice tone="warning" title="Atenção">
          Pendência
        </Notice>
        <PaginationSummary offset={0} limit={50} total={120} loadedCount={50} />
      </>,
    );
    expect(screen.getByTestId("section-card")).toHaveTextContent("Resumo");
    expect(screen.getByTestId("summary-grid")).toHaveTextContent("EUR 10,00");
    expect(screen.getByTestId("notice")).toHaveTextContent("Pendência");
    expect(screen.getByTestId("pagination-summary")).toHaveTextContent("Exibindo 1–50 de 120");
  });

  it("EmptyState com ação e ErrorState com retry", () => {
    const retry = vi.fn();
    render(
      <>
        <EmptyState message="Sem itens" title="Vazio" orientation="Ajuste os filtros" action={<Button>Criar</Button>} />
        <ErrorState message="Falha" onRetry={retry} />
      </>,
    );
    expect(screen.getByTestId("empty-state")).toHaveTextContent("Ajuste os filtros");
    fireEvent.click(screen.getByRole("button", { name: "Tentar novamente" }));
    expect(retry).toHaveBeenCalled();
  });

  it("Button danger e RowAction link", () => {
    render(
      <MemoryRouter>
        <Button variant="danger">Excluir</Button>
        <RowAction to="/orders/1">Abrir</RowAction>
      </MemoryRouter>,
    );
    expect(screen.getByRole("button", { name: "Excluir" }).className).toContain("ui-button--danger");
    expect(screen.getByTestId("row-action")).toHaveAttribute("href", "/orders/1");
  });

  it("AuditDocumentsBlock e roleLabel", () => {
    render(
      <AuditDocumentsBlock
        documents={[{ name: "nf.pdf", uploadedAt: "2026-07-01T10:00:00Z" }]}
        audit={[{ action: "issue", at: "2026-07-01T11:00:00Z", actor: "Ana" }]}
      />,
    );
    expect(screen.getByTestId("audit-documents-block")).toHaveTextContent("nf.pdf");
    expect(screen.getByTestId("audit-documents-block")).toHaveTextContent("Emissão");
    expect(roleLabel("admin")).toBe("Administrador");
  });
});
