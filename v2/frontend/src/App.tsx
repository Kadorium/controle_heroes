import { Navigate, Route, Routes, useLocation, useSearchParams } from "react-router-dom";
import { LoginPage } from "./features/auth/LoginPage";
import { loginUrlWithNext, sanitizeNextPath } from "./features/auth/safeNext";
import { AppShell } from "./app-shell/AppShell";
import { useAuth } from "./features/auth/useAuth";
import { OrdersListPage } from "./features/orders/OrdersListPage";
import { OrderCreatePage } from "./features/orders/OrderCreatePage";
import { InvoiceDetailPage } from "./features/billing/InvoiceDetailPage";
import { InvoicesListPage, PayablesListPage } from "./features/billing/InvoicesListPage";
import { ApQueuePage } from "./features/billing/ApQueuePage";
import {
  PaymentCreatePage,
  PaymentDetailPage,
  PaymentsListPage,
} from "./features/treasury/PaymentsPages";
import { PayableFxPage } from "./features/treasury/PayableFxPage";
import { OrderCockpitPage } from "./features/orders/OrderCockpitPage";
import { OrderDetailPage } from "./features/orders/OrderDetailPage";
import { ShipmentsListPage } from "./features/shipments/ShipmentsListPage";
import { ShipmentCreatePage } from "./features/shipments/ShipmentCreatePage";
import { ShipmentDetailPage } from "./features/shipments/ShipmentDetailPage";
import { LogisticsProvidersPage } from "./features/shipments/LogisticsProvidersPage";
import { CustomsListPage } from "./features/customs/CustomsListPage";
import { CustomsCreatePage } from "./features/customs/CustomsCreatePage";
import { CustomsDetailPage } from "./features/customs/CustomsDetailPage";
import { SkuPositionPage } from "./features/inventory/SkuPositionPage";
import { MovementsPage } from "./features/inventory/MovementsPage";
import { FundingRedirectPage } from "./features/customs/FundingRedirectPage";
import { IngestionQueuePage } from "./features/ingestion/IngestionQueuePage";
import { IngestionWorkspacePage } from "./features/ingestion/IngestionWorkspacePage";
import { CostingListPage } from "./features/costing/CostingListPage";
import { CostingWorkspacePage } from "./features/costing/CostingWorkspacePage";
import { CostingComparePage } from "./features/costing/CostingComparePage";
import { ProductListPage } from "./features/catalog/ProductListPage";
import { ProductCreatePage } from "./features/catalog/ProductCreatePage";
import { ProductDetailPage } from "./features/catalog/ProductDetailPage";
import { ProductComparePage } from "./features/catalog/ProductComparePage";
import { SupplierListPage } from "./features/catalog/SupplierListPage";
import { SupplierCreatePage } from "./features/catalog/SupplierCreatePage";
import { SupplierDetailPage } from "./features/catalog/SupplierDetailPage";
import { UsersListPage } from "./features/admin/UsersListPage";
import { UserCreatePage } from "./features/admin/UserCreatePage";
import { UserDetailPage } from "./features/admin/UserDetailPage";
import { DashboardPage } from "./features/dashboard/DashboardPage";
import type { User } from "./features/auth/types";

function can(user: User, perm: string) {
  return user.role === "admin" || (user.permissions ?? []).includes(perm);
}

function HomeRedirect({ user }: { user: User }) {
  if (can(user, "reporting:read")) {
    return <Navigate to="/dashboard" replace />;
  }
  if (can(user, "orders:read")) return <Navigate to="/orders" replace />;
  if (can(user, "customs:read")) return <Navigate to="/customs" replace />;
  if (can(user, "inventory:read")) return <Navigate to="/inventory/movements" replace />;
  return <Navigate to="/orders" replace />;
}

function LoginRoute({ user, onSuccess }: { user: User | null; onSuccess: () => Promise<void> | void }) {
  const [params] = useSearchParams();
  if (user) {
    const next = params.get("next");
    if (!next) {
      return <Navigate to="/" replace />;
    }
    return <Navigate to={sanitizeNextPath(next)} replace />;
  }
  return <LoginPage onSuccess={onSuccess} />;
}

function ProtectedShell({
  user,
  onLogout,
}: {
  user: User | null;
  onLogout: () => Promise<void> | void;
}) {
  const location = useLocation();
  if (!user) {
    return <Navigate to={loginUrlWithNext(location.pathname, location.search)} replace />;
  }
  return <AppShell user={user} onLogout={onLogout} />;
}

export function App() {
  const { user, loading, refresh } = useAuth();

  if (loading) {
    return <div className="page-center">Carregando…</div>;
  }

  const useApQueue =
    !!user && (user.role === "admin" || (user.permissions ?? []).includes("reporting:read"));

  return (
    <Routes>
      <Route
        path="/login"
        element={<LoginRoute user={user} onSuccess={() => refresh({ silent: true })} />}
      />
      <Route path="/" element={<ProtectedShell user={user} onLogout={refresh} />}>
        <Route index element={<HomeRedirect user={user!} />} />
        <Route path="dashboard" element={<DashboardPage user={user!} />} />
        <Route path="catalog/products" element={<ProductListPage user={user!} />} />
        <Route path="catalog/products/new" element={<ProductCreatePage user={user!} />} />
        <Route path="catalog/products/compare" element={<ProductComparePage user={user!} />} />
        <Route path="catalog/products/:productId/edit" element={<ProductDetailPage user={user!} editing />} />
        <Route path="catalog/products/:productId" element={<ProductDetailPage user={user!} />} />
        <Route path="catalog/suppliers" element={<SupplierListPage user={user!} />} />
        <Route path="catalog/suppliers/new" element={<SupplierCreatePage user={user!} />} />
        <Route path="catalog/suppliers/:supplierId" element={<SupplierDetailPage user={user!} />} />
        <Route path="admin/users" element={<UsersListPage user={user!} />} />
        <Route path="admin/users/new" element={<UserCreatePage user={user!} />} />
        <Route path="admin/users/:userId" element={<UserDetailPage user={user!} />} />
        <Route path="orders" element={<OrdersListPage user={user!} />} />
        <Route path="orders/new" element={<OrderCreatePage user={user!} />} />
        <Route path="orders/:orderId" element={<OrderCockpitPage user={user!} />} />
        <Route path="orders/:orderId/commercial" element={<OrderDetailPage user={user!} />} />
        <Route path="invoices" element={<InvoicesListPage user={user!} />} />
        <Route path="invoices/:invoiceId" element={<InvoiceDetailPage user={user!} />} />
        <Route
          path="payables"
          element={useApQueue ? <ApQueuePage user={user!} /> : <PayablesListPage user={user!} />}
        />
        <Route path="payables/:payableId/fx" element={<PayableFxPage user={user!} />} />
        <Route path="payments" element={<PaymentsListPage user={user!} />} />
        <Route path="payments/new" element={<PaymentCreatePage user={user!} />} />
        <Route path="payments/:paymentId" element={<PaymentDetailPage user={user!} />} />
        <Route path="shipments" element={<ShipmentsListPage user={user!} />} />
        <Route path="shipments/new" element={<ShipmentCreatePage user={user!} />} />
        <Route path="shipments/:shipmentId" element={<ShipmentDetailPage user={user!} />} />
        <Route path="logistics-providers" element={<LogisticsProvidersPage user={user!} />} />
        <Route path="customs" element={<CustomsListPage user={user!} />} />
        <Route path="customs/new" element={<CustomsCreatePage user={user!} />} />
        <Route path="customs/funding/:fundingRequestId" element={<FundingRedirectPage />} />
        <Route path="customs/:processId" element={<CustomsDetailPage user={user!} />} />
        <Route path="inventory/movements" element={<MovementsPage user={user!} />} />
        <Route path="inventory/sku/:productId" element={<SkuPositionPage user={user!} />} />
        <Route path="ingestion" element={<IngestionQueuePage user={user!} />} />
        <Route path="ingestion/:documentId" element={<IngestionWorkspacePage user={user!} />} />
        <Route path="costing" element={<CostingListPage user={user!} />} />
        <Route path="costing/:caseId/compare" element={<CostingComparePage user={user!} />} />
        <Route path="costing/:caseId" element={<CostingWorkspacePage user={user!} />} />
      </Route>
    </Routes>
  );
}
