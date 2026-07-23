import { NavLink, Outlet } from "react-router-dom";
import type { User } from "../features/auth/types";
import { FxQuoteStrip } from "../features/treasury/FxPanels";

type Props = {
  user: User;
  onLogout: () => Promise<void> | void;
};

export function AppShell({ user, onLogout }: Props) {
  async function logout() {
    await fetch("/api/auth/logout", { method: "POST", credentials: "include" });
    await onLogout();
  }

  const canOrders = user.role === "admin" || user.permissions.includes("orders:read");
  const canBilling = user.role === "admin" || user.permissions.includes("billing:read");
  const canTreasury = user.role === "admin" || user.permissions.includes("treasury:read");

  return (
    <div className="shell">
      <header className="shell-header">
        <div className="shell-brand">
          <strong>Epic Controle V2</strong>
          <div className="shell-user">
            {user.name} · {user.role}
          </div>
        </div>
        <nav className="shell-nav" aria-label="Principal">
          {canOrders ? (
            <>
              <NavLink to="/orders" end>
                Ordens
              </NavLink>
              {(user.role === "admin" || user.permissions.includes("orders:write")) && (
                <NavLink to="/orders/new">Nova ordem</NavLink>
              )}
            </>
          ) : null}
          {canBilling ? (
            <>
              <NavLink to="/invoices">Faturas</NavLink>
              <NavLink to="/payables">Payables</NavLink>
            </>
          ) : null}
          {canTreasury ? <NavLink to="/payments">Pagamentos</NavLink> : null}
        </nav>
        <FxQuoteStrip user={user} />
        <button type="button" onClick={() => void logout()}>
          Sair
        </button>
      </header>
      <main className="shell-main">
        <Outlet />
      </main>
    </div>
  );
}
