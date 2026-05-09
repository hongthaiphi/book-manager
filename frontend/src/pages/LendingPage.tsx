import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Layout from "@/components/Layout";
import { loansApi, type LoanRequest, type Loan } from "@/api/loans";
import { useAuthStore } from "@/stores/auth";

type Tab = "incoming" | "sent" | "active" | "history";

const TAB_LABELS: Record<Tab, string> = {
  incoming: "Chờ xử lý",
  sent: "Đã gửi",
  active: "Đang mượn",
  history: "Lịch sử",
};

// ---------------------------------------------------------------------------
// Approve Modal
// ---------------------------------------------------------------------------

function ApproveModal({
  request,
  onClose,
}: {
  request: LoanRequest;
  onClose: () => void;
}) {
  const [form, setForm] = useState({ agreed_deposit: "0", meet_location: "", due_days: 14 });
  const qc = useQueryClient();

  const mutation = useMutation({
    mutationFn: () =>
      loansApi.approve(request.id, {
        agreed_deposit: parseFloat(form.agreed_deposit) || 0,
        meet_location: form.meet_location,
        due_days: form.due_days,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["loan-requests-incoming"] });
      onClose();
    },
  });

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl max-w-md w-full p-6">
        <h3 className="text-lg font-bold mb-1">Chấp nhận yêu cầu</h3>
        <p className="text-sm text-gray-500 mb-4">
          Từ: <strong>{request.borrower.name}</strong>
        </p>

        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Tiền cọc (VNĐ)</label>
            <input
              type="number"
              value={form.agreed_deposit}
              onChange={(e) => setForm({ ...form, agreed_deposit: e.target.value })}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
              placeholder="0 = không cần cọc"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Địa điểm / thời gian hẹn gặp *
            </label>
            <input
              type="text"
              value={form.meet_location}
              onChange={(e) => setForm({ ...form, meet_location: e.target.value })}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
              placeholder="vd: Tầng trệt, chiều thứ 6 sau 18h"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Hạn mượn (ngày)
            </label>
            <select
              value={form.due_days}
              onChange={(e) => setForm({ ...form, due_days: parseInt(e.target.value) })}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
            >
              {[7, 14, 21, 30].map((d) => (
                <option key={d} value={d}>{d} ngày</option>
              ))}
            </select>
          </div>
        </div>

        <div className="mt-4 flex justify-end gap-2">
          <button onClick={onClose} className="px-4 py-2 border border-gray-200 rounded-lg text-sm">
            Huỷ
          </button>
          <button
            onClick={() => mutation.mutate()}
            disabled={mutation.isPending || !form.meet_location.trim()}
            className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm hover:bg-green-700 disabled:opacity-50"
          >
            {mutation.isPending ? "Đang xử lý…" : "Chấp nhận"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Loan Request Card (incoming)
// ---------------------------------------------------------------------------

function IncomingRequestCard({ req }: { req: LoanRequest }) {
  const [showApprove, setShowApprove] = useState(false);
  const qc = useQueryClient();

  const rejectMutation = useMutation({
    mutationFn: () => loansApi.reject(req.id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["loan-requests-incoming"] }),
  });

  const STATUS_BADGE: Record<string, string> = {
    pending: "bg-yellow-100 text-yellow-700",
    approved: "bg-green-100 text-green-700",
    rejected: "bg-red-100 text-red-600",
    cancelled: "bg-gray-100 text-gray-500",
    confirmed: "bg-blue-100 text-blue-700",
  };

  const STATUS_LABEL: Record<string, string> = {
    pending: "Chờ xử lý",
    approved: "Đã chấp nhận",
    rejected: "Đã từ chối",
    cancelled: "Đã huỷ",
    confirmed: "Đã giao sách",
  };

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          {req.borrower.avatar_url ? (
            <img src={req.borrower.avatar_url} className="w-10 h-10 rounded-full" alt={req.borrower.name} />
          ) : (
            <div className="w-10 h-10 rounded-full bg-gray-200 flex items-center justify-center text-sm font-medium text-gray-500">
              {req.borrower.name[0]}
            </div>
          )}
          <div>
            <p className="font-medium text-sm text-gray-900">{req.borrower.name}</p>
            <p className="text-xs text-gray-400">{new Date(req.created_at).toLocaleDateString("vi")}</p>
          </div>
        </div>
        <span className={`text-xs px-2 py-1 rounded-full font-medium ${STATUS_BADGE[req.status] || "bg-gray-100 text-gray-500"}`}>
          {STATUS_LABEL[req.status] || req.status}
        </span>
      </div>

      {req.message && (
        <p className="mt-3 text-sm text-gray-600 bg-gray-50 rounded-lg px-3 py-2 italic">
          "{req.message}"
        </p>
      )}

      {req.status === "approved" && (
        <div className="mt-3 text-xs text-green-700 bg-green-50 rounded-lg px-3 py-2">
          📍 {req.meet_location} · Cọc: {parseFloat(req.agreed_deposit || "0").toLocaleString("vi")}đ
        </div>
      )}

      {req.status === "pending" && (
        <div className="mt-3 flex gap-2">
          <button
            onClick={() => setShowApprove(true)}
            className="flex-1 py-1.5 bg-green-600 text-white rounded-lg text-xs font-medium hover:bg-green-700"
          >
            Chấp nhận
          </button>
          <button
            onClick={() => rejectMutation.mutate()}
            disabled={rejectMutation.isPending}
            className="flex-1 py-1.5 border border-red-200 text-red-600 rounded-lg text-xs font-medium hover:bg-red-50"
          >
            Từ chối
          </button>
        </div>
      )}

      {req.status === "approved" && (
        <ConfirmHandoverButton loanRequestId={req.id} />
      )}

      {showApprove && (
        <ApproveModal request={req} onClose={() => setShowApprove(false)} />
      )}
    </div>
  );
}

function ConfirmHandoverButton({ loanRequestId }: { loanRequestId: string }) {
  const qc = useQueryClient();
  const mutation = useMutation({
    mutationFn: () => loansApi.confirm(loanRequestId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["loan-requests-incoming"] });
      qc.invalidateQueries({ queryKey: ["loans-active"] });
    },
  });

  return (
    <button
      onClick={() => mutation.mutate()}
      disabled={mutation.isPending}
      className="mt-2 w-full py-1.5 bg-blue-600 text-white rounded-lg text-xs font-medium hover:bg-blue-700 disabled:opacity-50"
    >
      {mutation.isPending ? "Đang xác nhận…" : "✓ Xác nhận đã giao sách"}
    </button>
  );
}

// ---------------------------------------------------------------------------
// Sent Request Card
// ---------------------------------------------------------------------------

function SentRequestCard({ req }: { req: LoanRequest }) {
  const qc = useQueryClient();
  const cancelMutation = useMutation({
    mutationFn: () => loansApi.cancel(req.id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["loan-requests-sent"] }),
  });

  const STATUS_BADGE: Record<string, string> = {
    pending: "bg-yellow-100 text-yellow-700",
    approved: "bg-green-100 text-green-700",
    rejected: "bg-red-100 text-red-600",
    cancelled: "bg-gray-100 text-gray-400",
    confirmed: "bg-blue-100 text-blue-700",
  };

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4">
      <div className="flex items-start justify-between">
        <div>
          <p className="font-medium text-sm text-gray-900">{req.lender.name}</p>
          <p className="text-xs text-gray-400">{new Date(req.created_at).toLocaleDateString("vi")}</p>
        </div>
        <span className={`text-xs px-2 py-1 rounded-full font-medium ${STATUS_BADGE[req.status] || ""}`}>
          {req.status}
        </span>
      </div>

      {req.status === "approved" && (
        <div className="mt-2 text-xs text-green-700 bg-green-50 rounded px-3 py-2">
          📍 {req.meet_location} · Cọc: {parseFloat(req.agreed_deposit || "0").toLocaleString("vi")}đ
        </div>
      )}

      {req.status === "rejected" && req.rejected_reason && (
        <p className="mt-2 text-xs text-red-500">{req.rejected_reason}</p>
      )}

      {req.status === "pending" && (
        <button
          onClick={() => cancelMutation.mutate()}
          disabled={cancelMutation.isPending}
          className="mt-2 text-xs text-gray-400 hover:text-red-500"
        >
          Huỷ yêu cầu
        </button>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Active Loan Card
// ---------------------------------------------------------------------------

function ActiveLoanCard({ loan }: { loan: Loan }) {
  const user = useAuthStore((s) => s.user);
  const isLender = loan.lender_id === user?.id;
  const qc = useQueryClient();

  const returnMutation = useMutation({
    mutationFn: () => loansApi.markReturned(loan.id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["loans-active"] });
      qc.invalidateQueries({ queryKey: ["loans-history"] });
    },
  });

  const today = new Date();
  const dueDate = loan.due_at ? new Date(loan.due_at) : null;
  const isOverdue = dueDate && dueDate < today;
  const daysLeft = dueDate ? Math.ceil((dueDate.getTime() - today.getTime()) / 86400000) : null;

  return (
    <div className={`bg-white border rounded-xl p-4 ${isOverdue ? "border-red-300" : "border-gray-200"}`}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs text-gray-400">{isLender ? "Bạn đang cho mượn" : "Bạn đang mượn từ"}</p>
          <p className="font-medium text-sm text-gray-900">{isLender ? loan.borrower.name : loan.lender.name}</p>
        </div>
        <span className={`text-xs px-2 py-1 rounded-full font-medium ${
          loan.status === "active" ? "bg-blue-100 text-blue-700" :
          loan.status === "overdue" ? "bg-red-100 text-red-600" :
          "bg-gray-100 text-gray-500"
        }`}>
          {loan.status === "active" ? "Đang mượn" : loan.status === "overdue" ? "Quá hạn" : loan.status}
        </span>
      </div>

      {dueDate && (
        <p className={`mt-2 text-xs ${isOverdue ? "text-red-500 font-medium" : "text-gray-500"}`}>
          {isOverdue
            ? `Quá hạn ${Math.abs(daysLeft!)} ngày (${dueDate.toLocaleDateString("vi")})`
            : `Hạn trả: ${dueDate.toLocaleDateString("vi")} (còn ${daysLeft} ngày)`}
        </p>
      )}

      {isLender && loan.status === "active" && (
        <button
          onClick={() => returnMutation.mutate()}
          disabled={returnMutation.isPending}
          className="mt-3 w-full py-1.5 bg-gray-800 text-white rounded-lg text-xs font-medium hover:bg-gray-900 disabled:opacity-50"
        >
          {returnMutation.isPending ? "Đang cập nhật…" : "✓ Xác nhận đã nhận lại sách"}
        </button>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Lending Page
// ---------------------------------------------------------------------------

export default function LendingPage() {
  const [tab, setTab] = useState<Tab>("incoming");

  const { data: incoming = [] } = useQuery({
    queryKey: ["loan-requests-incoming"],
    queryFn: () => loansApi.listIncoming().then((r) => r.data),
    enabled: tab === "incoming",
    refetchInterval: 30000,
  });

  const { data: sent = [] } = useQuery({
    queryKey: ["loan-requests-sent"],
    queryFn: () => loansApi.listSent().then((r) => r.data),
    enabled: tab === "sent",
  });

  const { data: activeLoans = [] } = useQuery({
    queryKey: ["loans-active"],
    queryFn: () => loansApi.listLoans("active").then((r) => r.data),
    enabled: tab === "active",
    refetchInterval: 30000,
  });

  const { data: history = [] } = useQuery({
    queryKey: ["loans-history"],
    queryFn: () => loansApi.listLoans("returned").then((r) => r.data),
    enabled: tab === "history",
  });

  const pendingCount = incoming.filter((r) => r.status === "pending").length;

  return (
    <Layout>
      <h1 className="text-2xl font-bold text-gray-900 mb-4">Cho mượn & Mượn sách</h1>

      {/* Tabs */}
      <div className="flex gap-1 bg-gray-100 rounded-xl p-1 mb-6">
        {(Object.keys(TAB_LABELS) as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`flex-1 py-2 rounded-lg text-sm font-medium transition-colors relative ${
              tab === t ? "bg-white shadow-sm text-gray-900" : "text-gray-500 hover:text-gray-700"
            }`}
          >
            {TAB_LABELS[t]}
            {t === "incoming" && pendingCount > 0 && (
              <span className="absolute -top-1 -right-1 w-4 h-4 bg-red-500 text-white text-xs rounded-full flex items-center justify-center">
                {pendingCount}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="space-y-3">
        {tab === "incoming" && (
          incoming.length === 0
            ? <EmptyState icon="📬" text="Chưa có yêu cầu mượn nào" />
            : incoming.map((r) => <IncomingRequestCard key={r.id} req={r} />)
        )}

        {tab === "sent" && (
          sent.length === 0
            ? <EmptyState icon="📤" text="Bạn chưa gửi yêu cầu mượn nào" />
            : sent.map((r) => <SentRequestCard key={r.id} req={r} />)
        )}

        {tab === "active" && (
          activeLoans.length === 0
            ? <EmptyState icon="📗" text="Không có sách đang mượn" />
            : activeLoans.map((l) => <ActiveLoanCard key={l.id} loan={l} />)
        )}

        {tab === "history" && (
          history.length === 0
            ? <EmptyState icon="📜" text="Chưa có lịch sử mượn sách" />
            : history.map((l) => <ActiveLoanCard key={l.id} loan={l} />)
        )}
      </div>
    </Layout>
  );
}

function EmptyState({ icon, text }: { icon: string; text: string }) {
  return (
    <div className="text-center py-16">
      <div className="text-4xl mb-3">{icon}</div>
      <p className="text-gray-500 text-sm">{text}</p>
    </div>
  );
}
