import { Navigate, Route, Routes } from "react-router-dom";
import { Card, LoadingState } from "./components";
import { useAuth } from "./context/AuthContext";
import { AppShell } from "./layouts/AppShell";
import { ProtectedRoute } from "./layouts/ProtectedRoute";
import { LoginPage } from "./LoginPage";
import { CadastrosPage } from "./pages/CadastrosPage";
import { DashboardPage } from "./pages/DashboardPage";
import { DemoGuidePage } from "./pages/DemoGuidePage";
import { DocumentsPage } from "./pages/DocumentsPage";
import { FinancePage } from "./pages/FinancePage";
import { HeroesUploadPage } from "./pages/HeroesUploadPage";
import { ImportationLayout } from "./pages/importation/ImportationLayout";
import { ImportationSectionPage } from "./pages/importation/ImportationSectionPage";
import { ImportationsPage } from "./pages/ImportationsPage";
import { ProductsPage } from "./pages/ProductsPage";
import { ProductDetailPage } from "./pages/products/ProductDetailPage";
import { ReviewQueuePage } from "./pages/ReviewQueuePage";
import { GlossaryPage } from "./pages/GlossaryPage";
import { SuppliersPage } from "./pages/SuppliersPage";
import { UsersPage } from "./pages/users/UsersPage";

function LoginRoute() {
  const { user, loading } = useAuth();
  if (loading) {
    return (
      <div className="app-shell">
        <Card>
          <LoadingState />
        </Card>
      </div>
    );
  }
  if (user) {
    return <Navigate to="/" replace />;
  }
  return <LoginPage />;
}

export function AppRouter() {
  return (
    <Routes>
      <Route path="/login" element={<LoginRoute />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<AppShell />}>
          <Route index element={<DashboardPage />} />
          <Route path="importacoes" element={<ImportationsPage />} />
          <Route path="importacoes/:id" element={<ImportationLayout />}>
            <Route index element={<Navigate to="resumo" replace />} />
            <Route path="resumo" element={<ImportationSectionPage section="resumo" />} />
            <Route path="itens" element={<ImportationSectionPage section="itens" />} />
            <Route path="invoices" element={<ImportationSectionPage section="invoices" />} />
            <Route path="financeiro" element={<ImportationSectionPage section="financeiro" />} />
            <Route path="documentos" element={<ImportationSectionPage section="documentos" />} />
            <Route path="logistica" element={<ImportationSectionPage section="logistica" />} />
            <Route path="aduaneiro" element={<ImportationSectionPage section="aduaneiro" />} />
            <Route path="conciliacao" element={<ImportationSectionPage section="conciliacao" />} />
            <Route path="historico" element={<ImportationSectionPage section="historico" />} />
          </Route>
          <Route path="financeiro" element={<FinancePage />} />
          <Route path="demo" element={<DemoGuidePage />} />

          {/* /cadastros agrupa sub-cadastros */}
          <Route path="cadastros" element={<CadastrosPage />}>
            <Route path="produtos" element={<ProductsPage />} />
            <Route path="produtos/:productId" element={<ProductDetailPage />} />
            <Route path="fornecedores" element={<SuppliersPage />} />
            <Route path="usuarios" element={<UsersPage />} />
            <Route path="heroes" element={<HeroesUploadPage />} />
            <Route path="revisao" element={<ReviewQueuePage />} />
            <Route path="glossario" element={<GlossaryPage />} />
          </Route>

          {/* Redirects de compatibilidade para URLs antigas */}
          <Route path="skus" element={<Navigate to="/cadastros/produtos" replace />} />
          <Route path="documentos" element={<DocumentsPage />} />
          <Route path="revisao" element={<Navigate to="/cadastros/revisao" replace />} />
          <Route path="heroes" element={<Navigate to="/cadastros/heroes" replace />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
