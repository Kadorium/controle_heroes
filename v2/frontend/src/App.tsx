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
import type { User } from "./features/auth/types";

function LoginRoute({ user, onSuccess }: { user: User | null; onSuccess: () => Promise<void> | void }) {
  const [params] = useSearchParams();
  if (user) {
    return <Navigate to={sanitizeNextPath(params.get("next"))} replace />;
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
        <Route index element={<Navigate to="/orders" replace />} />
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
        <Route path="customs/:processId" element={<CustomsDetailPage user={user!} />} />
        <Route path="inventory/movements" element={<MovementsPage user={user!} />} />
        <Route path="inventory/sku/:productId" element={<SkuPositionPage user={user!} />} />
      </Route>
    </Routes>
  );
}
