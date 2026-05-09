import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Layout from "@/components/Layout";
import { communityApi, type CommunityBook } from "@/api/community";
import { loansApi } from "@/api/loans";
import { useAuthStore } from "@/stores/auth";

// ---------------------------------------------------------------------------
// Loan Request Modal
// ---------------------------------------------------------------------------

function RequestModal({
  book,
  onClose,
}: {
  book: CommunityBook;
  onClose: () => void;
}) {
  const [message, setMessage] = useState("");
  const qc = useQueryClient();

  const mutation = useMutation({
    mutationFn: () => loansApi.requestLoan(book.id, message || undefined),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["community-books"] });
      onClose();
    },
  });

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl max-w-md w-full p-6">
        <h3 className="text-lg font-bold mb-1">Gửi yêu cầu mượn sách</h3>
        <p className="text-sm text-gray-500 mb-4">
          <span className="font-medium">{book.title}</span> — {book.owner_name}
        </p>

        {book.deposit_amount > 0 && (
          <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg text-sm text-yellow-800">
            Tiền cọc yêu cầu: <strong>{book.deposit_amount.toLocaleString("vi")}đ</strong>
            {book.lend_note && <div className="mt-1 text-yellow-700">{book.lend_note}</div>}
          </div>
        )}

        <textarea
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder="Lời nhắn cho chủ sách (tuỳ chọn)..."
          rows={3}
          className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-400"
        />

        {mutation.isError && (
          <p className="mt-2 text-red-500 text-sm">
            {(mutation.error as any)?.response?.data?.detail || "Có lỗi xảy ra"}
          </p>
        )}

        <div className="mt-4 flex justify-end gap-2">
          <button onClick={onClose} className="px-4 py-2 border border-gray-200 rounded-lg text-sm">
            Huỷ
          </button>
          <button
            onClick={() => mutation.mutate()}
            disabled={mutation.isPending}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50"
          >
            {mutation.isPending ? "Đang gửi…" : "Gửi yêu cầu"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Join Building Modal
// ---------------------------------------------------------------------------

function JoinBuildingModal({ onClose }: { onClose: () => void }) {
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [mode, setMode] = useState<"join" | "create">("join");
  const qc = useQueryClient();

  const joinMutation = useMutation({
    mutationFn: () => communityApi.join(code),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["my-building"] });
      qc.invalidateQueries({ queryKey: ["community-books"] });
      onClose();
    },
  });

  const createMutation = useMutation({
    mutationFn: () => communityApi.createBuilding(name),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["my-building"] });
      onClose();
    },
  });

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl max-w-md w-full p-6">
        <h3 className="text-lg font-bold mb-4">Tham gia cộng đồng</h3>

        <div className="flex gap-2 mb-4">
          <button
            onClick={() => setMode("join")}
            className={`flex-1 py-2 rounded-lg text-sm font-medium ${mode === "join" ? "bg-blue-600 text-white" : "border border-gray-200 text-gray-600"}`}
          >
            Nhập code
          </button>
          <button
            onClick={() => setMode("create")}
            className={`flex-1 py-2 rounded-lg text-sm font-medium ${mode === "create" ? "bg-blue-600 text-white" : "border border-gray-200 text-gray-600"}`}
          >
            Tạo mới
          </button>
        </div>

        {mode === "join" ? (
          <>
            <input
              value={code}
              onChange={(e) => setCode(e.target.value.toUpperCase())}
              placeholder="Invite code (vd: AB12CD34)"
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm font-mono tracking-widest"
              maxLength={8}
            />
            <button
              onClick={() => joinMutation.mutate()}
              disabled={joinMutation.isPending || code.length < 4}
              className="mt-3 w-full py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50"
            >
              {joinMutation.isPending ? "Đang tham gia…" : "Tham gia"}
            </button>
            {joinMutation.isError && (
              <p className="mt-2 text-red-500 text-sm text-center">Code không hợp lệ</p>
            )}
          </>
        ) : (
          <>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Tên toà nhà (vd: Vinhomes Central Park T2)"
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
            />
            <button
              onClick={() => createMutation.mutate()}
              disabled={createMutation.isPending || !name.trim()}
              className="mt-3 w-full py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50"
            >
              {createMutation.isPending ? "Đang tạo…" : "Tạo cộng đồng"}
            </button>
          </>
        )}

        <button onClick={onClose} className="mt-3 w-full py-2 text-gray-400 text-sm">
          Đóng
        </button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Community Book Card
// ---------------------------------------------------------------------------

function CommunityBookCard({
  book,
  onRequest,
}: {
  book: CommunityBook;
  onRequest: (book: CommunityBook) => void;
}) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden hover:shadow-md transition-shadow">
      <div className="aspect-[2/3] bg-gray-100">
        {book.cover_url ? (
          <img src={book.cover_url} alt={book.title} className="w-full h-full object-cover" />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-4xl">📖</div>
        )}
      </div>
      <div className="p-3">
        <h3 className="font-medium text-sm text-gray-900 line-clamp-2 leading-snug mb-1">
          {book.title}
        </h3>
        <p className="text-xs text-gray-500 truncate">{book.authors?.join(", ")}</p>
        <div className="mt-2 flex items-center justify-between">
          <div className="flex items-center gap-1.5">
            {book.owner_avatar ? (
              <img src={book.owner_avatar} alt={book.owner_name} className="w-4 h-4 rounded-full" />
            ) : (
              <div className="w-4 h-4 rounded-full bg-gray-200" />
            )}
            <span className="text-xs text-gray-500 truncate max-w-[80px]">{book.owner_name}</span>
          </div>
          {book.deposit_amount > 0 && (
            <span className="text-xs text-orange-600">
              Cọc {(book.deposit_amount / 1000).toFixed(0)}k
            </span>
          )}
        </div>
        <button
          onClick={() => onRequest(book)}
          disabled={book.is_blocked}
          className="mt-2 w-full py-1.5 text-xs rounded-lg bg-blue-50 text-blue-700 hover:bg-blue-100 disabled:opacity-40 disabled:cursor-not-allowed font-medium"
        >
          {book.is_blocked ? "Không khả dụng" : "Xin mượn"}
        </button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Community Page
// ---------------------------------------------------------------------------

export default function CommunityPage() {
  const [requestBook, setRequestBook] = useState<CommunityBook | null>(null);
  const [showJoin, setShowJoin] = useState(false);

  const { data: building, isLoading: buildingLoading } = useQuery({
    queryKey: ["my-building"],
    queryFn: () => communityApi.myBuilding().then((r) => r.data),
    retry: false,
  });

  const { data: books = [], isLoading: booksLoading } = useQuery({
    queryKey: ["community-books"],
    queryFn: () => communityApi.books().then((r) => r.data),
    enabled: !!building,
  });

  if (buildingLoading) {
    return (
      <Layout>
        <div className="text-center py-16 text-gray-400">Đang tải…</div>
      </Layout>
    );
  }

  if (!building) {
    return (
      <Layout>
        <div className="text-center py-16">
          <div className="text-5xl mb-4">🏢</div>
          <h2 className="text-xl font-bold text-gray-800 mb-2">Chưa tham gia cộng đồng nào</h2>
          <p className="text-gray-500 mb-6 text-sm">
            Tham gia cộng đồng trong toà nhà của bạn để xem và mượn sách từ hàng xóm.
          </p>
          <button
            onClick={() => setShowJoin(true)}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700"
          >
            Tham gia / Tạo cộng đồng
          </button>
        </div>
        {showJoin && <JoinBuildingModal onClose={() => setShowJoin(false)} />}
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Sách cộng đồng</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            🏢 {building.name}
            <span className="ml-2 font-mono text-xs bg-gray-100 px-2 py-0.5 rounded">
              {building.invite_code}
            </span>
          </p>
        </div>
      </div>

      {booksLoading ? (
        <div className="text-center py-16 text-gray-400">Đang tải…</div>
      ) : books.length === 0 ? (
        <div className="text-center py-16">
          <div className="text-5xl mb-4">📚</div>
          <p className="text-gray-500">Chưa có sách nào được chia sẻ trong toà nhà.</p>
          <p className="text-sm text-gray-400 mt-1">
            Đánh dấu sách của bạn "Cho mượn" để bắt đầu!
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
          {books.map((book) => (
            <CommunityBookCard key={book.id} book={book} onRequest={setRequestBook} />
          ))}
        </div>
      )}

      {requestBook && (
        <RequestModal book={requestBook} onClose={() => setRequestBook(null)} />
      )}
    </Layout>
  );
}
