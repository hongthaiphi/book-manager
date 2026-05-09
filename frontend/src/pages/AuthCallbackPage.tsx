import { useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useAuthStore } from "@/stores/auth";

export default function AuthCallbackPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const setTokenAndFetchUser = useAuthStore((s) => s.setTokenAndFetchUser);

  useEffect(() => {
    const token = searchParams.get("access_token");
    if (!token) {
      navigate("/login");
      return;
    }
    setTokenAndFetchUser(token).then(() => navigate("/shelf"));
  }, [searchParams, navigate, setTokenAndFetchUser]);

  return (
    <div className="min-h-screen flex items-center justify-center">
      <p className="text-gray-500">Đang đăng nhập…</p>
    </div>
  );
}
