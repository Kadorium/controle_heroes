import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { DocumentActions } from "./DocumentActions";

describe("DocumentActions", () => {
  it("mostra Abrir e Baixar e trata 403", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ status: 403, ok: false });
    vi.stubGlobal("fetch", fetchMock);

    render(
      <DocumentActions documentId={9} filename="PL.pdf" mimeType="application/pdf" data-testid="da" />,
    );
    expect(screen.getByTestId("da-name")).toHaveTextContent("PL.pdf");
    expect(screen.getByTestId("da-open")).toBeInTheDocument();
    expect(screen.getByTestId("da-download")).toBeInTheDocument();

    fireEvent.click(screen.getByTestId("da-download"));
    await waitFor(() => expect(screen.getByTestId("da-error")).toHaveTextContent(/permissão/i));
    expect(fetchMock).toHaveBeenCalledWith("/api/documents/9/content?download=1", expect.any(Object));

    vi.unstubAllGlobals();
  });
});
