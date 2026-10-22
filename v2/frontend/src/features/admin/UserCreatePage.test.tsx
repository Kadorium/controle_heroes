import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { UserCreatePage } from "./UserCreatePage";

const createUser = vi.fn();

vi.mock("./identityApi", () => ({
  listRoles: vi.fn(async () => [
    { id: 1, name: "admin", description: null },
    { id: 2, name: "comprador", description: null },
  ]),
  createUser: (...args: unknown[]) => createUser(...args),
}));

const admin = {
  id: 1,
  email: "admin@epic.com.br",
  name: "Admin",
  role: "admin" as const,
  permissions: ["users:read", "users:write"],
};

describe("UserCreatePage", () => {
  afterEach(() => {
    cleanup();
  });

  beforeEach(() => {
    createUser.mockReset();
  });

  it("bloqueia e-mail inválido antes do POST", async () => {
    render(
      <MemoryRouter>
        <UserCreatePage user={admin} />
      </MemoryRouter>,
    );
    await screen.findByTestId("user-create-page");
    fireEvent.change(screen.getByTestId("user-name"), { target: { value: "Ricardo" } });
    fireEvent.change(screen.getByTestId("user-email"), { target: { value: "RN" } });
    fireEvent.change(screen.getByTestId("user-password"), { target: { value: "admin123" } });
    fireEvent.change(screen.getByTestId("user-password-confirm"), { target: { value: "admin123" } });
    fireEvent.submit(screen.getByTestId("user-create-submit").closest("form")!);
    expect(await screen.findByText(/e-mail inválido/i)).toBeInTheDocument();
    expect(createUser).not.toHaveBeenCalled();
  });

  it("bloqueia senha curta antes do POST", async () => {
    render(
      <MemoryRouter>
        <UserCreatePage user={admin} />
      </MemoryRouter>,
    );
    await screen.findByTestId("user-create-page");
    fireEvent.change(screen.getByTestId("user-name"), { target: { value: "Ricardo" } });
    fireEvent.change(screen.getByTestId("user-email"), { target: { value: "ricardo@epic.com.br" } });
    fireEvent.change(screen.getByTestId("user-password"), { target: { value: "abc" } });
    fireEvent.change(screen.getByTestId("user-password-confirm"), { target: { value: "abc" } });
    fireEvent.submit(screen.getByTestId("user-create-submit").closest("form")!);
    expect(await screen.findByText(/pelo menos 8 caracteres/i)).toBeInTheDocument();
    expect(createUser).not.toHaveBeenCalled();
  });

  it("envia create válido", async () => {
    createUser.mockResolvedValue({ id: 9, email: "ricardo@epic.com.br", name: "Ricardo" });
    render(
      <MemoryRouter>
        <UserCreatePage user={admin} />
      </MemoryRouter>,
    );
    await screen.findByTestId("user-create-page");
    await waitFor(() => expect(screen.getByTestId("user-role")).toHaveValue("2"));
    fireEvent.change(screen.getByTestId("user-name"), { target: { value: "Ricardo" } });
    fireEvent.change(screen.getByTestId("user-email"), { target: { value: "ricardo@epic.com.br" } });
    fireEvent.change(screen.getByTestId("user-password"), { target: { value: "admin123" } });
    fireEvent.change(screen.getByTestId("user-password-confirm"), { target: { value: "admin123" } });
    fireEvent.submit(screen.getByTestId("user-create-submit").closest("form")!);
    await waitFor(() => expect(createUser).toHaveBeenCalledTimes(1));
    expect(createUser).toHaveBeenCalledWith(
      expect.objectContaining({
        email: "ricardo@epic.com.br",
        name: "Ricardo",
        password: "admin123",
        is_active: true,
      }),
    );
  });
});
