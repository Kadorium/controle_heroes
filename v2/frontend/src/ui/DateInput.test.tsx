import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { DateInput } from "./DateInput";

afterEach(() => {
  cleanup();
});

describe("DateInput", () => {
  it("mostra dd/mm/aaaa a partir do ISO", () => {
    render(<DateInput value="2026-03-30" onChange={() => undefined} />);
    expect(screen.getByPlaceholderText("dd/mm/aaaa")).toHaveValue("30/03/2026");
  });

  it("aceita digitação ISO (ensaios) e emite YYYY-MM-DD", () => {
    let value = "";
    const { rerender } = render(
      <DateInput value={value} onChange={(e) => {
        value = e.target.value;
      }} />,
    );
    const input = screen.getByPlaceholderText("dd/mm/aaaa");
    fireEvent.focus(input);
    fireEvent.change(input, { target: { value: "2026-03-30" } });
    rerender(<DateInput value={value} onChange={(e) => {
      value = e.target.value;
    }} />);
    fireEvent.blur(input);
    expect(value).toBe("2026-03-30");
  });
});
