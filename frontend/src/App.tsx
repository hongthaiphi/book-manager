import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import ProtectedRoute from "@/components/ProtectedRoute";
import { Toaster } from "@/components/Toast";
import LoginPage from "@/pages/LoginPage";
import AuthCallbackPage from "@/pages/AuthCallbackPage";
import ShelfPage from "@/pages/ShelfPage";
import CommunityPage from "@/pages/CommunityPage";
import LendingPage from "@/pages/LendingPage";
import StatsPage from "@/pages/StatsPage";
import SettingsPage from "@/pages/SettingsPage";
import PublicProfilePage from "@/pages/PublicProfilePage";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5,
      retry: 1,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          {/* Public */}
          <Route path="/login" element={<LoginPage />} />
          <Route path="/auth/callback" element={<AuthCallbackPage />} />
          <Route path="/u/:slug" element={<PublicProfilePage />} />

          {/* Protected */}
          <Route element={<ProtectedRoute />}>
            <Route path="/shelf" element={<ShelfPage />} />
            <Route path="/community" element={<CommunityPage />} />
            <Route path="/lending" element={<LendingPage />} />
            <Route path="/stats" element={<StatsPage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Route>

          {/* Redirect root */}
          <Route path="/" element={<Navigate to="/shelf" replace />} />
        </Routes>

        <Toaster />
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
