import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { notificationsApi, type Notification } from "@/api/loans";

export default function NotificationBell() {
  const [open, setOpen] = useState(false);
  const qc = useQueryClient();

  const { data: notifications = [] } = useQuery({
    queryKey: ["notifications"],
    queryFn: () => notificationsApi.list().then((r) => r.data),
    refetchInterval: 30000,
  });

  const unreadCount = notifications.filter((n) => !n.is_read).length;

  const markAll = useMutation({
    mutationFn: notificationsApi.markAllRead,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["notifications"] }),
  });

  return (
    <div className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        className="relative p-1.5 text-gray-500 hover:text-gray-800"
        aria-label="Notifications"
      >
        🔔
        {unreadCount > 0 && (
          <span className="absolute -top-0.5 -right-0.5 w-4 h-4 bg-red-500 text-white text-xs rounded-full flex items-center justify-center leading-none">
            {unreadCount > 9 ? "9+" : unreadCount}
          </span>
        )}
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-30" onClick={() => setOpen(false)} />
          <div className="absolute right-0 top-8 z-40 w-80 bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden">
            <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
              <span className="font-semibold text-sm">Thông báo</span>
              {unreadCount > 0 && (
                <button
                  onClick={() => markAll.mutate()}
                  className="text-xs text-blue-600 hover:text-blue-800"
                >
                  Đọc tất cả
                </button>
              )}
            </div>
            <div className="max-h-96 overflow-y-auto divide-y divide-gray-50">
              {notifications.length === 0 ? (
                <p className="text-center py-6 text-gray-400 text-sm">Không có thông báo</p>
              ) : (
                notifications.map((n) => <NotifItem key={n.id} notif={n} />)
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function NotifItem({ notif }: { notif: Notification }) {
  const qc = useQueryClient();
  const markRead = useMutation({
    mutationFn: () => notificationsApi.markRead(notif.id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["notifications"] }),
  });

  return (
    <div
      onClick={() => !notif.is_read && markRead.mutate()}
      className={`px-4 py-3 cursor-pointer hover:bg-gray-50 ${!notif.is_read ? "bg-blue-50" : ""}`}
    >
      <p className="text-sm font-medium text-gray-900 leading-snug">{notif.title}</p>
      {notif.body && <p className="text-xs text-gray-500 mt-0.5 line-clamp-2">{notif.body}</p>}
      <p className="text-xs text-gray-400 mt-1">
        {new Date(notif.created_at).toLocaleDateString("vi", {
          day: "numeric",
          month: "short",
          hour: "2-digit",
          minute: "2-digit",
        })}
      </p>
    </div>
  );
}
