import { useRef, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Layout from "@/components/Layout";
import { booksApi, type UserBook, type BookSearchResult } from "@/api/books";
import ISBNScanner from "@/components/book/ISBNScanner";
import { BookGridSkeleton } from "@/components/Skeleton";
import { toast } from "@/components/Toast";

const STATUS_LABELS: Record<string, string> = {
  want_to_read: "Muốn đọc",
  reading: "Đang đọc",
  read: "Đã đọc",
  did_not_finish: "Bỏ dở",
};

const STATUS_COLORS: Record<string, string> = {
  want_to_read: "bg-blue-100 text-blue-700",
  reading: "bg-yellow-100 text-yellow-700",
  read: "bg-green-100 text-green-700",
  did_not_finish: "bg-gray-100 text-gray-500",
};

// ---------------------------------------------------------------------------
// Add Book Modal
// ---------------------------------------------------------------------------

function AddBookModal({ onClose, onAdded }: { onClose: () => void; onAdded: () => void }) {
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<BookSearchResult[]>([]);
  const [selected, setSelected] = useState<BookSearchResult | null>(null);
  const [isSearching, setIsSearching] = useState(false);
  const [form, setForm] = useState({
    status: "want_to_read",
    can_lend: false,
    deposit_amount: 0,
    purchase_price: "",
    purchase_where: "",
    acquired_how: "bought",
  });

  const qc = useQueryClient();
  const addMutation = useMutation({
    mutationFn: booksApi.add,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["books"] });
      toast.success("Đã thêm sách vào tủ!");
      onAdded();
      onClose();
    },
    onError: () => toast.error("Không thể thêm sách"),
  });

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;
    setIsSearching(true);
    try {
      // Try ISBN first
      if (/^\d{10,13}$/.test(searchQuery.trim())) {
        const { data } = await booksApi.lookupIsbn(searchQuery.trim());
        setSearchResults([data]);
      } else {
        const { data } = await booksApi.search(searchQuery);
        setSearchResults(data.slice(0, 8));
      }
    } catch {
      setSearchResults([]);
    } finally {
      setIsSearching(false);
    }
  };

  const handleAdd = () => {
    if (!selected) return;
    addMutation.mutate({
      ...selected,
      status: form.status,
      can_lend: form.can_lend,
      deposit_amount: form.deposit_amount,
      purchase_price: form.purchase_price ? parseFloat(form.purchase_price) : undefined,
      purchase_where: form.purchase_where || undefined,
      acquired_how: form.acquired_how,
    });
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto p-6">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-bold">Thêm sách vào tủ</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-2xl leading-none">&times;</button>
        </div>

        {!selected ? (
          <>
            <div className="flex gap-2 mb-4">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                placeholder="Tên sách, tác giả, hoặc ISBN..."
                className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <button
                onClick={handleSearch}
                disabled={isSearching}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50"
              >
                {isSearching ? "…" : "Tìm"}
              </button>
            </div>
            <div className="mb-4">
              <ISBNScanner
                onDetected={(isbn) => {
                  setSearchQuery(isbn);
                  handleSearch();
                }}
              />
            </div>

            {searchResults.length > 0 && (
              <div className="space-y-2">
                {searchResults.map((book, i) => (
                  <button
                    key={i}
                    onClick={() => setSelected(book)}
                    className="w-full text-left flex gap-3 p-3 border border-gray-200 rounded-lg hover:border-blue-400 hover:bg-blue-50 transition-colors"
                  >
                    {book.cover_url ? (
                      <img src={book.cover_url} alt={book.title} className="w-12 h-16 object-cover rounded" />
                    ) : (
                      <div className="w-12 h-16 bg-gray-100 rounded flex items-center justify-center text-2xl">📖</div>
                    )}
                    <div className="flex-1 min-w-0">
                      <div className="font-medium text-gray-900 truncate">{book.title}</div>
                      <div className="text-sm text-gray-500">{book.authors?.join(", ")}</div>
                      {book.publisher && <div className="text-xs text-gray-400">{book.publisher}</div>}
                    </div>
                  </button>
                ))}
              </div>
            )}

            {searchResults.length === 0 && searchQuery && !isSearching && (
              <p className="text-center text-gray-400 py-4 text-sm">Không tìm thấy. Thử từ khóa khác hoặc nhập ISBN.</p>
            )}
          </>
        ) : (
          <>
            <button onClick={() => setSelected(null)} className="text-sm text-blue-600 mb-4">&larr; Tìm lại</button>

            <div className="flex gap-4 mb-6">
              {selected.cover_url ? (
                <img src={selected.cover_url} alt={selected.title} className="w-20 h-28 object-cover rounded-lg shadow" />
              ) : (
                <div className="w-20 h-28 bg-gray-100 rounded-lg flex items-center justify-center text-3xl">📖</div>
              )}
              <div>
                <h3 className="font-bold text-gray-900">{selected.title}</h3>
                <p className="text-sm text-gray-600">{selected.authors?.join(", ")}</p>
                {selected.publisher && <p className="text-xs text-gray-400 mt-1">{selected.publisher}</p>}
              </div>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Trạng thái đọc</label>
                <select
                  value={form.status}
                  onChange={(e) => setForm({ ...form, status: e.target.value })}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                >
                  {Object.entries(STATUS_LABELS).map(([val, label]) => (
                    <option key={val} value={val}>{label}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Cách có được</label>
                <select
                  value={form.acquired_how}
                  onChange={(e) => setForm({ ...form, acquired_how: e.target.value })}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                >
                  <option value="bought">Tự mua</option>
                  <option value="gift">Được tặng</option>
                  <option value="other">Khác</option>
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Giá mua (VNĐ)</label>
                  <input
                    type="number"
                    value={form.purchase_price}
                    onChange={(e) => setForm({ ...form, purchase_price: e.target.value })}
                    placeholder="vd: 85000"
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Mua ở đâu</label>
                  <input
                    type="text"
                    value={form.purchase_where}
                    onChange={(e) => setForm({ ...form, purchase_where: e.target.value })}
                    placeholder="vd: Fahasa, Shopee..."
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                  />
                </div>
              </div>

              <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
                <input
                  type="checkbox"
                  id="can_lend"
                  checked={form.can_lend}
                  onChange={(e) => setForm({ ...form, can_lend: e.target.checked })}
                  className="w-4 h-4"
                />
                <label htmlFor="can_lend" className="text-sm font-medium text-gray-700">Cho mượn</label>
                {form.can_lend && (
                  <input
                    type="number"
                    value={form.deposit_amount}
                    onChange={(e) => setForm({ ...form, deposit_amount: parseFloat(e.target.value) || 0 })}
                    placeholder="Tiền cọc (0 = không cần)"
                    className="ml-auto border border-gray-300 rounded px-2 py-1 text-sm w-40"
                  />
                )}
              </div>
            </div>

            <div className="mt-6 flex justify-end gap-3">
              <button onClick={onClose} className="px-4 py-2 border border-gray-300 rounded-lg text-sm">Huỷ</button>
              <button
                onClick={handleAdd}
                disabled={addMutation.isPending}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50"
              >
                {addMutation.isPending ? "Đang thêm…" : "Thêm vào tủ"}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Book Card
// ---------------------------------------------------------------------------

function BookCard({ book }: { book: UserBook }) {
  const coverUrl = book.physical_cover_url || book.catalog.cover_url;

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden hover:shadow-md transition-shadow">
      <div className="aspect-[2/3] bg-gray-100 relative">
        {coverUrl ? (
          <img src={coverUrl} alt={book.catalog.title} className="w-full h-full object-cover" />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-4xl">📖</div>
        )}
        {book.can_lend && (
          <span className="absolute top-2 right-2 bg-emerald-500 text-white text-xs px-2 py-1 rounded-full">
            Cho mượn
          </span>
        )}
      </div>
      <div className="p-3">
        <h3 className="font-medium text-sm text-gray-900 line-clamp-2 leading-snug mb-1">
          {book.catalog.title}
        </h3>
        <p className="text-xs text-gray-500 truncate">
          {book.catalog.authors?.join(", ") || "Không rõ tác giả"}
        </p>
        <div className="mt-2">
          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_COLORS[book.status] || "bg-gray-100 text-gray-500"}`}>
            {STATUS_LABELS[book.status] || book.status}
          </span>
        </div>
        {book.personal_rating && (
          <div className="mt-1 text-xs text-yellow-600">
            {"★".repeat(book.personal_rating)}{"☆".repeat(5 - book.personal_rating)}
          </div>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Shelf Page
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// Goodreads Import Button
// ---------------------------------------------------------------------------

function GoodreadsImportButton({ onDone }: { onDone: () => void }) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [loading, setLoading] = useState(false);

  const handleFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setLoading(true);
    try {
      const { data } = await booksApi.importGoodreads(file);
      toast.success(`Đã import ${data.imported} sách${data.skipped ? `, bỏ qua ${data.skipped} trùng` : ""}.`);
      if (data.errors.length) {
        console.warn("Import warnings:", data.errors);
      }
      onDone();
    } catch {
      toast.error("Không thể import file Goodreads");
    } finally {
      setLoading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  return (
    <>
      <input ref={fileRef} type="file" accept=".csv" className="hidden" onChange={handleFile} />
      <button
        onClick={() => fileRef.current?.click()}
        disabled={loading}
        className="inline-flex items-center gap-2 px-3 py-2 border border-gray-200 rounded-lg text-sm text-gray-600 hover:border-blue-300 hover:text-blue-600 transition-colors disabled:opacity-50"
      >
        {loading ? "⏳ Đang import…" : "📥 Import Goodreads"}
      </button>
    </>
  );
}

// ---------------------------------------------------------------------------
// Shelf Page
// ---------------------------------------------------------------------------

export default function ShelfPage() {
  const [showAddModal, setShowAddModal] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [searchQ, setSearchQ] = useState("");
  const qc = useQueryClient();

  const { data: books = [], isLoading } = useQuery({
    queryKey: ["books", statusFilter, searchQ],
    queryFn: () =>
      booksApi
        .list({
          status: statusFilter || undefined,
          q: searchQ || undefined,
        })
        .then((r) => r.data),
  });

  return (
    <Layout>
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Tủ sách của tôi</h1>
        <div className="flex items-center gap-2">
          <GoodreadsImportButton onDone={() => qc.invalidateQueries({ queryKey: ["books"] })} />
          <button
            onClick={() => setShowAddModal(true)}
            className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700"
          >
            + Thêm sách
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-2 mb-6">
        {[["", "Tất cả"], ...Object.entries(STATUS_LABELS)].map(([val, label]) => (
          <button
            key={val}
            onClick={() => setStatusFilter(val)}
            className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
              statusFilter === val
                ? "bg-blue-600 text-white"
                : "bg-white border border-gray-200 text-gray-600 hover:border-blue-300"
            }`}
          >
            {label}
          </button>
        ))}
        <input
          type="text"
          value={searchQ}
          onChange={(e) => setSearchQ(e.target.value)}
          placeholder="Tìm trong tủ sách..."
          className="ml-auto border border-gray-200 rounded-full px-4 py-1.5 text-sm w-52 focus:outline-none focus:ring-2 focus:ring-blue-400"
        />
      </div>

      {/* Grid */}
      {isLoading ? (
        <BookGridSkeleton />
      ) : books.length === 0 ? (
        <div className="text-center py-16">
          <div className="text-5xl mb-4">📚</div>
          <p className="text-gray-500">Tủ sách trống. Thêm cuốn đầu tiên!</p>
        </div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
          {books.map((book) => (
            <BookCard key={book.id} book={book} />
          ))}
        </div>
      )}

      {showAddModal && (
        <AddBookModal
          onClose={() => setShowAddModal(false)}
          onAdded={() => setShowAddModal(false)}
        />
      )}
    </Layout>
  );
}
