import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Layout from "@/components/Layout";
import { trustApi, profileApi, type BlacklistEntry } from "@/api/trust";
import { useAuthStore } from "@/stores/auth";

type Tab = "profile" | "blacklist";

// ---------------------------------------------------------------------------
// Profile Tab
// ---------------------------------------------------------------------------

function ProfileTab() {
  const user = useAuthStore((s) => s.user);
  const fetchUser = useAuthStore((s) => s.fetchUser);
  const [form, setForm] = useState({
    name: user?.name || "",
    profile_slug: user?.profile_slug || "",
    bio: "",
    is_public: true,
  });
  const [saved, setSaved] = useState(false);

  const mutation = useMutation({
    mutationFn: () => profileApi.updateOwn(form),
    onSuccess: () => {
      fetchUser();
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    },
  });

  return (
    <div className="space-y-4 max-w-md">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Tên hiển thị</label>
        <input
          value={form.name}
          onChange={(e) => setForm({ ...form, name: e.target.value })}
          className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
        />
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Profile slug{" "}
          <span className="text-gray-400 font-normal">(/u/your-slug)</span>
        </label>
        <div className="flex items-center border border-gray-200 rounded-lg overflow-hidden">
          <span className="px-3 py-2 bg-gray-50 text-gray-400 text-sm border-r border-gray-200">/u/</span>
          <input
            value={form.profile_slug}
            onChange={(e) => setForm({ ...form, profile_slug: e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, "") })}
            className="flex-1 px-3 py-2 text-sm outline-none"
            placeholder="ten-cua-ban"
          />
        </div>
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Bio</label>
        <textarea
          value={form.bio}
          onChange={(e) => setForm({ ...form, bio: e.target.value })}
          rows={3}
          placeholder="Giới thiệu ngắn về bạn..."
          className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm resize-none"
        />
      </div>
      <label className="flex items-center gap-2 cursor-pointer">
        <input
          type="checkbox"
          checked={form.is_public}
          onChange={(e) => setForm({ ...form, is_public: e.target.checked })}
          className="w-4 h-4"
        />
        <span className="text-sm text-gray-700">Tủ sách công khai</span>
      </label>
      <button
        onClick={() => mutation.mutate()}
        disabled={mutation.isPending}
        className="px-5 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
      >
        {mutation.isPending ? "Đang lưu…" : saved ? "✓ Đã lưu" : "Lưu thay đổi"}
      </button>
      {mutation.isError && (
        <p className="text-red-500 text-sm">
          {(mutation.error as any)?.response?.data?.detail || "Có lỗi xảy ra"}
        </p>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Blacklist Tab
// ---------------------------------------------------------------------------

function BlacklistTab() {
  const qc = useQueryClient();
  const { data: entries = [], isLoading } = useQuery({
    queryKey: ["blacklist"],
    queryFn: () => trustApi.getBlacklist().then((r) => r.data),
  });

  const unblockMutation = useMutation({
    mutationFn: (userId: string) => trustApi.unblock(userId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["blacklist"] }),
  });

  if (isLoading) return <div className="text-gray-400 text-sm">Đang tải…</div>;

  if (entries.length === 0) {
    return (
      <div className="text-center py-12">
        <div className="text-4xl mb-3">🛡️</div>
        <p className="text-gray-500 text-sm">Danh sách chặn trống.</p>
      </div>
    );
  }

  return (
    <div className="space-y-3 max-w-md">
      {entries.map((entry: BlacklistEntry) => (
        <div key={entry.id} className="flex items-center justify-between p-4 bg-white border border-gray-200 rounded-xl">
          <div className="flex items-center gap-3">
            {entry.blocked_user_avatar ? (
              <img src={entry.blocked_user_avatar} className="w-10 h-10 rounded-full" alt="" />
            ) : (
              <div className="w-10 h-10 rounded-full bg-gray-200 flex items-center justify-center text-sm font-medium">
                {entry.blocked_user_name[0]}
              </div>
            )}
            <div>
              <p className="font-medium text-sm text-gray-900">{entry.blocked_user_name}</p>
              {entry.reason && <p className="text-xs text-gray-400 mt-0.5">{entry.reason}</p>}
              <p className="text-xs text-gray-400">
                {new Date(entry.created_at).toLocaleDateString("vi")}
              </p>
            </div>
          </div>
          <button
            onClick={() => unblockMutation.mutate(entry.blocked_user_id)}
            disabled={unblockMutation.isPending}
            className="text-xs text-red-500 hover:text-red-700 border border-red-200 rounded-lg px-3 py-1.5 hover:bg-red-50 disabled:opacity-50"
          >
            Bỏ chặn
          </button>
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Settings Page
// ---------------------------------------------------------------------------

export default function SettingsPage() {
  const [tab, setTab] = useState<Tab>("profile");

  return (
    <Layout>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Cài đặt</h1>

      <div className="flex gap-1 bg-gray-100 rounded-xl p-1 mb-6 max-w-xs">
        {(["profile", "blacklist"] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`flex-1 py-2 rounded-lg text-sm font-medium transition-colors ${
              tab === t ? "bg-white shadow-sm text-gray-900" : "text-gray-500"
            }`}
          >
            {t === "profile" ? "Hồ sơ" : "Danh sách chặn"}
          </button>
        ))}
      </div>

      {tab === "profile" ? <ProfileTab /> : <BlacklistTab />}
    </Layout>
  );
}
