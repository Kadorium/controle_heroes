import { Navigate, Route, Routes } from "react-router-dom";
import { LoginPage } from "./features/auth/LoginPage";
import { AppShell } from "./app-shell/AppShell";
import { useAuth } from "./features/auth/useAuth";
import { OrdersListPage } from "./features/orders/OrdersListPage";
import { OrderCreatePage } from "./features/orders/OrderCreatePage";
import { OrderDetailPage } from "./features/orders/OrderDetailPage";
import { InvoiceDetailPage } from "./features/billing/InvoiceDetailPage";
import { InvoicesListPage, PayablesListPage } from "./features/billing/InvoicesListPage";
import {
  PaymentCreatePage,
  PaymentDetailPage,
  PaymentsListPage,
} from "./features/treasury/PaymentsPages";
import { PayableFxPage } from "./features/treasury/PayableFxPage";

export function App() {
  const { user, loading, refresh } = useAuth();

  if (loading) {
    return <div className="page-center">Carregando…</div>;
  }

  return (
    <Routes>
      <Route
        path="/login"
        element={user ? <Navigate to="/orders" replace /> : <LoginPage onSuccess={refresh} />}
      />
      <Route
        path="/"
        element={user ? <AppShell user={user} onLogout={refresh} /> : <Navigate to="/login" replace />}
      >
        <Route index element={<Navigate to="/orders" replace />} />
        <Route path="orders" element={<OrdersListPage user={user!} />} />
        <Route path="orders/new" element={<OrderCreatePage user={user!} />} />
        <Route path="orders/:orderId" element={<OrderDetailPage user={user!} />} />
        <Route path="invoices" element={<InvoicesListPage user={user!} />} />
        <Route path="invoices/:invoiceId" element={<InvoiceDetailPage user={user!} />} />
        <Route path="payables" element={<PayablesListPage user={user!} />} />
        <Route path="payables/:payableId/fx" element={<PayableFxPage user={user!} />} />
        <Route path="payments" element={<PaymentsListPage user={user!} />} />
        <Route path="payments/new" element={<PaymentCreatePage user={user!} />} />
        <Route path="payments/:paymentId" element={<PaymentDetailPage user={user!} />} />
      </Route>
    </Routes>
  );
}
