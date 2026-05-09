import { useEffect } from "react";
import { Navigate, Outlet } from "react-router-dom";
import { useAuthStore } from "@/stores/auth";

export default function ProtectedRoute() {
  const { user, accessToken, isLoading, fetchUser } = useAuthStore();

  useEffect(() => {
    if (accessToken && !user && !isLoading) {
      fetchUser();
    }
  }, [accessToken, user, isLoading, fetchUser]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-gray-400">Đang tải…</p>
      </div>
    );
  }

  if (!accessToken && !user) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}
