import { describe, expect, it } from "vitest";
import { formatIdentityError } from "./identityApi";

describe("formatIdentityError", () => {
  it("usa message de AppError", () => {
    expect(formatIdentityError({ error: "email_duplicate", message: "E-mail já cadastrado" }, "fallback")).toBe(
      "E-mail já cadastrado",
    );
  });

  it("traduz 422 Pydantic de e-mail", () => {
    expect(
      formatIdentityError(
        {
          detail: [
            {
              type: "value_error",
              loc: ["body", "email"],
              msg: "value is not a valid email address",
              input: "RN",
            },
          ],
        },
        "Erro ao criar usuário",
      ),
    ).toBe("E-mail inválido. Use o formato nome@dominio.");
  });

  it("cai no fallback sem corpo útil", () => {
    expect(formatIdentityError({}, "Erro ao criar usuário")).toBe("Erro ao criar usuário");
  });
});
