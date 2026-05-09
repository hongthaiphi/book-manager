import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuthStore } from "@/stores/auth";
import { useUIStore } from "@/stores/ui";
import NotificationBell from "@/components/NotificationBell";

export default function Layout({ children }: { children: React.ReactNode }) {
  const { user, logout } = useAuthStore();
  const { theme, toggleTheme } = useUIStore();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
      <header className="bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800 sticky top-0 z-10">
        <div className="max-w-5xl mx-auto px-4 h-14 flex items-center justify-between">
          <Link to="/shelf" className="font-bold text-lg flex items-center gap-2 text-gray-900 dark:text-white">
            📚 <span className="hidden sm:inline">Book Manager</span>
          </Link>

          {/* Desktop nav */}
          <nav className="hidden sm:flex items-center gap-5 text-sm">
            {[
              ["/shelf", "Tủ sách"],
              ["/community", "Cộng đồng"],
              ["/lending", "Mượn sách"],
              ["/stats", "Thống kê"],
            ].map(([href, label]) => (
              <Link
                key={href}
                to={href}
                className="text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white transition-colors"
              >
                {label}
              </Link>
            ))}

            {user && (
              <div className="flex items-center gap-3 ml-2">
                <NotificationBell />
                <button
                  onClick={toggleTheme}
                  className="p-1.5 text-gray-500 dark:text-gray-300 hover:text-gray-800 dark:hover:text-white"
                  aria-label="Toggle theme"
                >
                  {theme === "dark" ? "☀️" : "🌙"}
                </button>
                <Link to="/settings" className="flex items-center gap-2">
                  {user.avatar_url ? (
                    <img src={user.avatar_url} alt={user.name} className="w-8 h-8 rounded-full object-cover" />
                  ) : (
                    <div className="w-8 h-8 rounded-full bg-blue-500 flex items-center justify-center text-white text-sm font-medium">
                      {user.name[0]}
                    </div>
                  )}
                </Link>
                <button
                  onClick={handleLogout}
                  className="text-gray-400 hover:text-red-500 text-xs transition-colors"
                >
                  Đăng xuất
                </button>
              </div>
            )}
          </nav>

          {/* Mobile hamburger */}
          <button
            className="sm:hidden p-2 text-gray-500 dark:text-gray-300"
            onClick={() => setMenuOpen((o) => !o)}
          >
            {menuOpen ? "✕" : "☰"}
          </button>
        </div>

        {/* Mobile menu */}
        {menuOpen && (
          <div className="sm:hidden bg-white dark:bg-gray-900 border-t border-gray-100 dark:border-gray-800 px-4 py-3 space-y-3">
            {[
              ["/shelf", "📚 Tủ sách"],
              ["/community", "🏢 Cộng đồng"],
              ["/lending", "🤝 Mượn sách"],
              ["/stats", "📊 Thống kê"],
              ["/settings", "⚙️ Cài đặt"],
            ].map(([href, label]) => (
              <Link
                key={href}
                to={href}
                onClick={() => setMenuOpen(false)}
                className="block text-sm text-gray-700 dark:text-gray-200 py-1"
              >
                {label}
              </Link>
            ))}
            <div className="flex items-center gap-3 pt-2 border-t border-gray-100 dark:border-gray-800">
              <button onClick={toggleTheme} className="text-sm text-gray-500 dark:text-gray-300">
                {theme === "dark" ? "☀️ Sáng" : "🌙 Tối"}
              </button>
              <button onClick={handleLogout} className="text-sm text-red-500 ml-auto">
                Đăng xuất
              </button>
            </div>
          </div>
        )}
      </header>

      <main className="max-w-5xl mx-auto px-4 py-6">{children}</main>
    </div>
  );
}
