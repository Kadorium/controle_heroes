import { useState } from "react";
import { render, fireEvent, screen, cleanup } from "@testing-library/react";
import { describe, it, expect, afterEach } from "vitest";
import { MoneyInput } from "./MoneyInput";
import { RateInput } from "./RateInput";
afterEach(cleanup);

describe("financial entry preserves browser selection", () => {
  for (const [kind, Component, initial, display, entered] of [
    ["money", MoneyInput, "1234.56", "1.234,56", "300,55"],
    ["rate", RateInput, "6.0000", "6,0000", "6,1250"],
  ] as const) {
    it(`${kind}: focus does not rewrite the formatted text; replacement and blur preserve value`, () => {
      function Form() {
        const [value, setValue] = useState<string>(initial);
        return <><Component aria-label={kind} value={value} onValueChange={setValue} /><output data-testid="wire">{value}</output></>;
      }
      render(<Form />);
      const input = screen.getByLabelText(kind) as HTMLInputElement;
      expect(input.value).toBe(display);
      for (let i = 0; i < 3; i++) {
        const before = input.value;
        fireEvent.focus(input);
        expect(input.value).toBe(before);
        expect(input.selectionStart).toBe(0);
        expect(input.selectionEnd).toBe(before.length);
        fireEvent.change(input, { target: { value: entered } });
        fireEvent.blur(input);
        expect(screen.getByTestId("wire").textContent).toBe(entered.replace(",", "."));
        expect(input.value).toBe(entered);
      }
    });
  }
});
