import { Navigate, Outlet, useLocation } from "react-router";

import { useAuth } from "../features/auth/AuthContext";

export function ProtectedRoute({ requireAdmin = false }: { requireAdmin?: boolean }) {
  const { user, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return <p className="text-slate-500">Loading your session...</p>;
  }
  if (user === null) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  if (requireAdmin && user.role !== "admin") {
    return <p className="text-red-700">Access denied: this page is only available to admins.</p>;
  }
  return <Outlet />;
}
