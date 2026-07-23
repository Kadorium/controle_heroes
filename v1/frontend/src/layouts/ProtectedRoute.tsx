import { Navigate, Outlet } from "react-router-dom";
import { Card, LoadingState } from "../components";
import { useAuth } from "../context/AuthContext";

export function ProtectedRoute() {
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

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}
