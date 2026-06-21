import { NavLink, Outlet, useMatch } from "react-router-dom";

const TABS = [
  {
    to: "/cadastros/produtos",
    label: "Produtos",
    description: "Catálogo de produtos importados",
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />
      </svg>
    ),
  },
  {
    to: "/cadastros/fornecedores",
    label: "Fornecedores",
    description: "Fornecedores internacionais",
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
        <circle cx="9" cy="7" r="4" />
        <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
        <path d="M16 3.13a4 4 0 0 1 0 7.75" />
      </svg>
    ),
  },
  {
    to: "/cadastros/heroes",
    label: "Importar Heroes", // i18n
    description: "Upload de planilha Heroes (CSV)",
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
        <polyline points="14 2 14 8 20 8" />
        <line x1="12" y1="18" x2="12" y2="12" />
        <line x1="9" y1="15" x2="15" y2="15" />
      </svg>
    ),
  },
  {
    to: "/cadastros/revisao",
    label: "Fila de revisão",
    description: "Linhas ambíguas aguardando revisão",
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <polyline points="9 11 12 14 22 4" />
        <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
      </svg>
    ),
  },
  {
    to: "/cadastros/glossario",
    label: "Glossário operacional",
    description: "Termos técnicos e rótulos em português",
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
        <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
      </svg>
    ),
  },
];

export function CadastrosPage() {
  const isIndex = useMatch("/cadastros");

  if (!isIndex) {
    return <Outlet />;
  }

  return (
    <div className="cadastros">
      <div className="cadastros__header">
        <h1>Cadastros</h1>
        <p className="cadastros__subtitle">Gerencie produtos, fornecedores e dados auxiliares.</p>
      </div>
      <div className="cadastros__grid">
        {TABS.map((tab) => (
          <NavLink key={tab.to} to={tab.to} className="cadastros__card">
            <div className="cadastros__card-icon">{tab.icon}</div>
            <div>
              <h3 className="cadastros__card-title">{tab.label}</h3>
              <p className="cadastros__card-desc">{tab.description}</p>
            </div>
          </NavLink>
        ))}
      </div>
    </div>
  );
}
