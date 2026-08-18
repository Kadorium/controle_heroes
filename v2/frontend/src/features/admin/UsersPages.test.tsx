import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { UsersListPage } from "./UsersListPage";

vi.mock("../../navigation/useListReturn", () => ({
  useListReturn: () => undefined,
}));

vi.mock("./identityApi", () => ({
  listUsers: vi.fn(async () => ({
    items: [
      {
        id: 1,
        email: "admin@epic.com.br",
        name: "Admin",
        role: "admin",
        role_id: 1,
        is_active: true,
        last_login: null,
        created_at: null,
        permissions: [],
      },
    ],
    total: 1,
    limit: 50,
    offset: 0,
  })),
}));

describe("UsersListPage", () => {
  it("lista usuários para admin", async () => {
    render(
      <MemoryRouter>
        <UsersListPage
          user={{
            id: 1,
            email: "admin@epic.com.br",
            name: "Admin",
            role: "admin",
            permissions: ["users:read", "users:write"],
          }}
        />
      </MemoryRouter>,
    );
    expect(await screen.findByTestId("users-list-page")).toBeInTheDocument();
    expect(screen.getByText("Admin")).toBeInTheDocument();
    expect(screen.getByTestId("users-new-cta")).toHaveAttribute("href", "/admin/users/new");
  });

  it("bloqueia sem users:read", () => {
    render(
      <MemoryRouter>
        <UsersListPage
          user={{
            id: 2,
            email: "c@e.c",
            name: "Comprador",
            role: "comprador",
            permissions: ["orders:read"],
          }}
        />
      </MemoryRouter>,
    );
    expect(screen.getByText(/sem permissão/i)).toBeInTheDocument();
  });
});
