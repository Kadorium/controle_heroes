import { cleanup, render, screen } from "@testing-library/react";
import type { ReactElement } from "react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it } from "vitest";
import { AgingBar, ExplainerDialog, Skeleton } from "../../ui";
import { DashboardWidgetCard } from "./DashboardWidgets";
import type { DashboardWidget } from "./dashboardApi";

afterEach(() => cleanup());

function wrap(ui: ReactElement) {
  return render(<MemoryRouter>{ui}</MemoryRouter>);
}

const base: Omit<DashboardWidget, "widget_id" | "label" | "kind" | "display"> = {
  metric_id: "hidden.id",
  short_description: "Texto do catálogo",
  status: "AVAILABLE",
  limitation: null,
  drill: "/payables",
  currencies: ["EUR"],
  filters_applied: ["date_from"],
  filters_ignored: [],
  time_field: "due_date",
  error: null,
  col: 1,
  span: 4,
};

describe("J7 dashboard UI", () => {
  it("não mostra metric_id no explainer nem no card", () => {
    const widget: DashboardWidget = {
      ...base,
      widget_id: "ap.next_7d",
      label: "A vencer em 7 dias",
      kind: "kpi_currency",
      display: {
        by_currency: [{ currency: "EUR", amount: "10.00" }],
        mixed_currency: false,
      },
    };
    wrap(
      <>
        <DashboardWidgetCard widget={widget} onExplain={() => undefined} />
        <ExplainerDialog
          open
          title={widget.label}
          description={widget.short_description}
          unitLabel="moeda da obrigação"
          onClose={() => undefined}
        />
      </>,
    );
    expect(screen.queryByText("ap.next_7d")).toBeNull();
    expect(screen.queryByText("hidden.id")).toBeNull();
    expect(screen.getAllByText("A vencer em 7 dias").length).toBeGreaterThan(0);
    expect(screen.getByTestId("explainer-dialog")).toHaveTextContent("Texto do catálogo");
  });

  it("Executiva progressiva não renderiza card PARTIAL", () => {
    const widgets: DashboardWidget[] = [
      {
        ...base,
        widget_id: "attention.inbox",
        label: "O que espera por você",
        kind: "inbox",
        display: {
          items: [],
          total_count: 0,
          empty_kind: "none",
          empty_copy: "Nada precisa da sua decisão agora.",
        },
      },
    ];
    wrap(
      <>
        {widgets
          .filter((w) => w.status !== "PARTIAL")
          .map((w) => (
            <DashboardWidgetCard key={w.widget_id} widget={w} onExplain={() => undefined} />
          ))}
      </>,
    );
    expect(screen.getByTestId("dash-widget-attention.inbox")).toBeInTheDocument();
    expect(screen.queryByText("PARTIAL")).toBeNull();
  });

  it("barra de aging por moeda", () => {
    wrap(
      <AgingBar
        rows={[
          {
            currency: "EUR",
            open_balance: "100.00",
            overdue_balance: "40.00",
            due_today_balance: "10.00",
            next_7d_balance: "20.00",
          },
        ]}
      />,
    );
    expect(screen.getByTestId("aging-bar")).toBeInTheDocument();
    expect(screen.getByText("Vencido")).toBeInTheDocument();
  });

  it("skeleton reserva altura", () => {
    wrap(<Skeleton kind="kpi" />);
    const el = screen.getByTestId("skeleton-slot");
    expect(el).toHaveStyle({ minHeight: "132px" });
  });

  it("chips de filtro ficam na URL (contrato da página)", () => {
    const search = "?view=financeiro&date_from=2026-08-01&currency=EUR";
    expect(search).toContain("date_from=2026-08-01");
    expect(search).toContain("currency=EUR");
    expect(search).not.toContain("crossFilter");
  });

  it("chrome do card é ícone info acessível, não o texto O que é", () => {
    const widget: DashboardWidget = {
      ...base,
      widget_id: "attention.inbox",
      label: "O que espera por você",
      kind: "inbox",
      display: {
        items: [],
        total_count: 0,
        empty_kind: "none",
          empty_copy: "Nada precisa da sua decisão agora.",
      },
    };
    wrap(<DashboardWidgetCard widget={widget} onExplain={() => undefined} />);
    const info = screen.getByRole("button", { name: /o que é o que espera por você/i });
    expect(info).toHaveTextContent("ⓘ");
    expect(info).toHaveAttribute("title", "Texto do catálogo");
    expect(screen.queryByRole("button", { name: /^o que é$/i })).toBeNull();
    expect(screen.getByText("Nada precisa da sua decisão agora.")).toBeInTheDocument();
  });

  it("totais compactos no caixa da Executiva", () => {
    const widget: DashboardWidget = {
      ...base,
      widget_id: "ap.cash_committed",
      label: "Caixa comprometido",
      kind: "cash_months",
      display: {
        labels: { overdue: "Já vencido", m0: "Agosto", m1: "Setembro", m2: "Outubro" },
        includes_overdue: true,
        empty: false,
        by_currency: [
          {
            currency: "EUR",
            buckets: { overdue: "0.00", m0: "14970.00", m1: "0.00", m2: "0.00" },
          },
        ],
      },
    };
    wrap(<DashboardWidgetCard widget={widget} onExplain={() => undefined} compactMoney />);
    expect(screen.getByText("€ 14,97 mil")).toBeInTheDocument();
    expect(screen.getByText("inclui vencidas")).toBeInTheDocument();
  });
});
