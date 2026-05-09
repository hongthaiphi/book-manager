import { useQuery } from "@tanstack/react-query";
import Layout from "@/components/Layout";
import { statsApi } from "@/api/trust";

const STATUS_LABELS: Record<string, string> = {
  want_to_read: "Muốn đọc",
  reading: "Đang đọc",
  read: "Đã đọc",
  did_not_finish: "Bỏ dở",
};

const STATUS_COLORS: Record<string, string> = {
  want_to_read: "bg-blue-400",
  reading: "bg-yellow-400",
  read: "bg-green-400",
  did_not_finish: "bg-gray-300",
};

export default function StatsPage() {
  const { data: summary } = useQuery({
    queryKey: ["stats-summary"],
    queryFn: () => statsApi.summary().then((r) => r.data),
  });

  const { data: reading } = useQuery({
    queryKey: ["stats-reading"],
    queryFn: () => statsApi.reading().then((r) => r.data),
  });

  const { data: lending } = useQuery({
    queryKey: ["stats-lending"],
    queryFn: () => statsApi.lending().then((r) => r.data),
  });

  const maxMonthly = reading
    ? Math.max(...reading.monthly.map((m) => m.count), 1)
    : 1;

  return (
    <Layout>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Thống kê</h1>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        {/* Summary cards */}
        <StatCard
          label="Tổng sách trong tủ"
          value={summary?.total_books ?? "—"}
          icon="📚"
        />
        <StatCard
          label="Đọc năm nay"
          value={summary?.read_this_year ?? "—"}
          icon="📖"
        />
        <StatCard
          label="Đọc tháng này"
          value={summary?.read_this_month ?? "—"}
          icon="🗓️"
        />
      </div>

      {/* By status breakdown */}
      {summary && summary.total_books > 0 && (
        <section className="bg-white rounded-xl border border-gray-200 p-5 mb-6">
          <h2 className="font-semibold text-gray-800 mb-4">Phân bổ tủ sách</h2>
          <div className="space-y-3">
            {Object.entries(summary.by_status).map(([s, count]) => {
              const pct = Math.round((count / summary.total_books) * 100);
              return (
                <div key={s}>
                  <div className="flex items-center justify-between text-sm mb-1">
                    <span className="text-gray-600">{STATUS_LABELS[s] || s}</span>
                    <span className="font-medium text-gray-900">{count} ({pct}%)</span>
                  </div>
                  <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full ${STATUS_COLORS[s] || "bg-gray-400"}`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      )}

      {/* Reading trend */}
      {reading && reading.monthly.length > 0 && (
        <section className="bg-white rounded-xl border border-gray-200 p-5 mb-6">
          <h2 className="font-semibold text-gray-800 mb-4">Tốc độ đọc (12 tháng)</h2>
          <div className="flex items-end gap-1.5 h-32">
            {reading.monthly.map((m) => {
              const height = Math.round((m.count / maxMonthly) * 100);
              const [year, month] = m.month.split("-");
              return (
                <div key={m.month} className="flex-1 flex flex-col items-center gap-1 group relative">
                  <div
                    className="w-full bg-blue-400 rounded-t-sm hover:bg-blue-500 transition-colors"
                    style={{ height: `${Math.max(height, 4)}%` }}
                  />
                  <span className="text-xs text-gray-400 leading-none">{month}</span>
                  {/* Tooltip */}
                  <div className="absolute -top-7 left-1/2 -translate-x-1/2 bg-gray-800 text-white text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 whitespace-nowrap pointer-events-none">
                    {m.count} sách · T{month}/{year}
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      )}

      {/* Lending stats */}
      {lending && (
        <section className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="font-semibold text-gray-800 mb-4">Cho mượn & Đi mượn</h2>
          <div className="grid grid-cols-3 gap-4 text-center">
            <div>
              <div className="text-2xl font-bold text-gray-900">{lending.total_lent}</div>
              <div className="text-xs text-gray-500 mt-1">Lần cho mượn</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-gray-900">{lending.total_borrowed}</div>
              <div className="text-xs text-gray-500 mt-1">Lần đi mượn</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-green-600">{lending.on_time_rate}%</div>
              <div className="text-xs text-gray-500 mt-1">Trả đúng hạn</div>
            </div>
          </div>
        </section>
      )}
    </Layout>
  );
}

function StatCard({ label, value, icon }: { label: string; value: number | string; icon: string }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <div className="text-3xl mb-2">{icon}</div>
      <div className="text-3xl font-bold text-gray-900">{value}</div>
      <div className="text-sm text-gray-500 mt-1">{label}</div>
    </div>
  );
}
