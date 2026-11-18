import { Link, useLocation } from "react-router-dom";
import type { User } from "../features/auth/types";
import { activeNavigation, visibleNavigation } from "./navigation";
import { buildReturnTo } from "../navigation/returnState";
import "./areaNavigation.css";

const paths: Record<string, string> = {
  home: "M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h7v7h-7z",
  product: "m3 7 9-4 9 4v10l-9 4-9-4V7Zm0 0 9 4 9-4M12 11v10",
  purchase: "M6 7h15l-2 9H7L4 3H1M8 21h.01M18 21h.01",
  shipment: "M3 13h18l-3 7H6l-3-7ZM7 13V6h10v7M12 6V2M3 22q3-3 6 0 3-3 6 0 3-3 6 0",
  money: "M3 5h18v14H3zM3 9h18M7 14h4",
  document: "M6 2h8l4 4v16H6zM14 2v5h4M9 11h6M9 15h6",
  users: "M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M13 3a4 4 0 0 1 0 8M22 21v-2a4 4 0 0 0-3-3.87M9 3a4 4 0 1 0 0 8 4 4 0 0 0 0-8Z",
};

export function PrimaryNavigation({ user, expanded }: { user: User; expanded: boolean }) {
  const { pathname } = useLocation();
  const areas = visibleNavigation(user);
  const { area: active } = activeNavigation(areas, pathname);
  return <nav className="shell-side-nav consolidated-nav" aria-label="Módulos">
    {[false, true].map(secondary => <div key={String(secondary)} className={secondary ? "nav-secondary" : "nav-primary"}>
      {areas.filter(area => !!area.secondary === secondary).map(area => <Link
        key={area.id} to={area.sections[0].to} data-testid={`nav-${area.id}`}
        className={active?.id === area.id ? "active" : undefined}
        aria-current={active?.id === area.id ? "page" : undefined}
        aria-label={area.label} title={!expanded ? area.label : undefined}>
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" aria-hidden="true"><path d={paths[area.icon]} /></svg>
        <span className="shell-nav-label">{area.label}</span>
        {!expanded && <span className="nav-rail-caption" aria-hidden="true">{area.label}</span>}
      </Link>)}
    </div>)}
  </nav>;
}

export function AreaNavigation({ user }: { user: User }) {
  const { pathname, search, state } = useLocation();
  const { area, section: active } = activeNavigation(visibleNavigation(user), pathname);
  if (!area || area.secondary || area.id === "overview") return null;
  return <nav className="area-navigation" aria-label={`Área de ${area.label.toLocaleLowerCase("pt-BR")}`}>
    <span className="area-navigation-label">{area.label}</span>
    <div className="area-navigation-links">
      {area.sections.map(section => <Link key={section.id}
        to={active?.id === section.id && pathname === section.to.split("?")[0]
          ? pathname + search : active?.id === section.id && !section.to.includes("?")
            ? buildReturnTo(section.to) : section.to}
        state={active?.id === section.id ? state : undefined}
        aria-current={active?.id === section.id ? "page" : undefined}
        className={active?.id === section.id ? "active" : undefined}
        data-testid={`section-${section.id}`}>{section.label}</Link>)}
    </div>
  </nav>;
}
