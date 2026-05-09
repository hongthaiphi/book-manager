import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import Layout from "@/components/Layout";
import { profileApi, type PublicBook } from "@/api/trust";

const STATUS_LABELS: Record<string, string> = {
  want_to_read: "Muốn đọc",
  reading: "Đang đọc",
  read: "Đã đọc",
  did_not_finish: "Bỏ dở",
};

export default function PublicProfilePage() {
  const { slug } = useParams<{ slug: string }>();

  const { data: profile, isLoading, isError } = useQuery({
    queryKey: ["public-profile", slug],
    queryFn: () => profileApi.getPublic(slug!).then((r) => r.data),
    enabled: !!slug,
    retry: false,
  });

  const { data: books = [] } = useQuery({
    queryKey: ["public-books", slug],
    queryFn: () => profileApi.getPublicBooks(slug!).then((r) => r.data),
    enabled: !!profile,
  });

  if (isLoading) {
    return (
      <Layout>
        <div className="text-center py-16 text-gray-400">Đang tải…</div>
      </Layout>
    );
  }

  if (isError || !profile) {
    return (
      <Layout>
        <div className="text-center py-16">
          <div className="text-5xl mb-4">🔒</div>
          <h2 className="text-xl font-bold text-gray-800">Profile không tồn tại</h2>
          <p className="text-gray-500 text-sm mt-2">Người dùng này không công khai hồ sơ của họ.</p>
        </div>
      </Layout>
    );
  }

  const lendingBooks = books.filter((b) => b.can_lend);
  const readBooks = books.filter((b) => b.status === "read");

  return (
    <Layout>
      {/* Profile header */}
      <div className="flex items-start gap-5 mb-8">
        {profile.avatar_url ? (
          <img src={profile.avatar_url} alt={profile.name} className="w-20 h-20 rounded-full object-cover" />
        ) : (
          <div className="w-20 h-20 rounded-full bg-gradient-to-br from-blue-400 to-indigo-500 flex items-center justify-center text-white text-2xl font-bold">
            {profile.name[0]}
          </div>
        )}
        <div className="flex-1">
          <h1 className="text-2xl font-bold text-gray-900">{profile.name}</h1>
          {profile.profile_slug && (
            <p className="text-sm text-gray-400 font-mono">@{profile.profile_slug}</p>
          )}
          {profile.bio && <p className="text-gray-600 text-sm mt-2">{profile.bio}</p>}
          <div className="flex gap-6 mt-3">
            <div className="text-center">
              <div className="text-xl font-bold text-gray-900">{profile.total_books}</div>
              <div className="text-xs text-gray-400">Tổng sách</div>
            </div>
            <div className="text-center">
              <div className="text-xl font-bold text-gray-900">{profile.books_read}</div>
              <div className="text-xs text-gray-400">Đã đọc</div>
            </div>
            <div className="text-center">
              <div className="text-xl font-bold text-gray-900">{profile.books_lending}</div>
              <div className="text-xs text-gray-400">Đang cho mượn</div>
            </div>
          </div>
        </div>
      </div>

      {/* Lending books */}
      {lendingBooks.length > 0 && (
        <section className="mb-8">
          <h2 className="text-lg font-semibold text-gray-800 mb-4">📗 Sách đang cho mượn</h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
            {lendingBooks.map((book) => (
              <BookCard key={book.id} book={book} />
            ))}
          </div>
        </section>
      )}

      {/* All books */}
      {books.length > 0 && (
        <section>
          <h2 className="text-lg font-semibold text-gray-800 mb-4">📚 Tủ sách</h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
            {books.map((book) => (
              <BookCard key={book.id} book={book} />
            ))}
          </div>
        </section>
      )}

      {books.length === 0 && (
        <div className="text-center py-12 text-gray-400">Tủ sách trống hoặc không công khai.</div>
      )}
    </Layout>
  );
}

function BookCard({ book }: { book: PublicBook }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div className="aspect-[2/3] bg-gray-100">
        {book.catalog.cover_url ? (
          <img src={book.catalog.cover_url} alt={book.catalog.title} className="w-full h-full object-cover" />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-4xl">📖</div>
        )}
      </div>
      <div className="p-3">
        <h3 className="font-medium text-xs text-gray-900 line-clamp-2 leading-snug mb-1">
          {book.catalog.title}
        </h3>
        <p className="text-xs text-gray-400">{STATUS_LABELS[book.status] || book.status}</p>
        {book.personal_rating && (
          <p className="text-xs text-yellow-500 mt-0.5">
            {"★".repeat(book.personal_rating)}{"☆".repeat(5 - book.personal_rating)}
          </p>
        )}
        {book.can_lend && (
          <span className="mt-1 inline-block text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full">
            Cho mượn
          </span>
        )}
      </div>
    </div>
  );
}
