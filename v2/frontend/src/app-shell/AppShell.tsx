import { Outlet } from "react-router-dom";
import { useState } from "react";
import type { User } from "../features/auth/types";
import { FxQuoteStrip } from "../features/treasury/FxPanels";
import { RuntimeBadge } from "./RuntimeBadge";
import { DemoTour } from "../features/demo/DemoTour";
import "./experience.css";
import { AreaNavigation, PrimaryNavigation } from "./AreaNavigation";

export function AppShell({ user, onLogout }: { user: User; onLogout: () => Promise<void> | void }) {
  const [expanded, setExpanded] = useState(() => localStorage.getItem("epic.navigation.expanded") !== "false");
  return <div className={`shell shell-sidebar-layout experience-shell ${expanded ? "experience-expanded" : "experience-collapsed"}`}>
    <a className="skip-link" href="#main-content">Ir para o conteúdo</a>
    <aside className="shell-sidebar" aria-label="Navegação principal">
      <div className="experience-brand"><span className="experience-mark">E</span>{expanded && <div><strong>EPIC</strong><small>Controle</small></div>}
        <button className="shell-rail-toggle" data-testid="shell-rail-toggle" aria-expanded={expanded} aria-label={expanded ? "Recolher navegação" : "Expandir navegação"} onClick={() => setExpanded(v => { localStorage.setItem("epic.navigation.expanded", String(!v)); return !v; })}>{expanded ? "‹" : "›"}</button></div>
      <PrimaryNavigation user={user} expanded={expanded} />
      <div className="shell-side-footer"><RuntimeBadge /><div className="shell-fx-slot"><FxQuoteStrip user={user} /></div>
        {expanded && <small className="experience-user">{user.name}</small>}<button className="shell-logout" aria-label="Sair" onClick={async () => { await fetch("/api/auth/logout", { method:"POST", credentials:"include" }); await onLogout(); }}>Sair</button></div>
    </aside>
    <div className="shell-content"><main id="main-content" className="shell-main" tabIndex={-1}>
      {import.meta.env.VITE_ENABLE_DEMO === "true" && user.role === "admin" ? <DemoTour /> : null}<AreaNavigation user={user} /><Outlet />
    </main></div>
  </div>;
}
