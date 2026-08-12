import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen, within } from "@testing-library/react";
import { ConfirmationModal } from "./ConfirmationModal";

afterEach(() => cleanup());

describe("ConfirmationModal initialFocusSelector", () => {
  it("foca o Motivo quando initialFocusSelector é passado", () => {
    render(
      <ConfirmationModal
        open
        title="Cancelar adiantamento"
        confirmLabel="Cancelar adiantamento"
        initialFocusSelector="#adv-cancel-reason"
        onConfirm={() => undefined}
        onCancel={() => undefined}
      >
        <label htmlFor="adv-cancel-reason">Motivo (obrigatório)</label>
        <input id="adv-cancel-reason" data-testid="adv-cancel-reason" />
      </ConfirmationModal>,
    );
    expect(screen.getByTestId("adv-cancel-reason")).toHaveFocus();
  });

  it("sem selector, mantém foco no primeiro focusable (Fechar)", () => {
    render(
      <ConfirmationModal open title="Confirmar" onConfirm={() => undefined} onCancel={() => undefined}>
        <p>sem campo</p>
      </ConfirmationModal>,
    );
    const dialog = screen.getByRole("dialog", { name: "Confirmar" });
    expect(within(dialog).getByLabelText("Fechar")).toHaveFocus();
  });
});
