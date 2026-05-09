import apiClient from "./client";

export interface BlacklistEntry {
  id: string;
  lender_id: string;
  blocked_user_id: string;
  reason: string | null;
  created_at: string;
  blocked_user_name: string;
  blocked_user_avatar: string | null;
}

export interface RatingOut {
  id: string;
  loan_id: string;
  is_positive: boolean;
  note: string | null;
  created_at: string;
}

export interface PublicProfile {
  id: string;
  name: string;
  avatar_url: string | null;
  profile_slug: string | null;
  bio: string | null;
  total_books: number;
  books_read: number;
  books_lending: number;
}

export interface PublicBook {
  id: string;
  catalog: {
    id: string;
    title: string;
    authors: string[] | null;
    cover_url: string | null;
    language: string;
  };
  status: string;
  personal_rating: number | null;
  can_lend: boolean;
  deposit_amount: number;
  tags: string[] | null;
}

export const trustApi = {
  rateLoan: (loanId: string, data: { is_positive: boolean; note?: string; block_user?: boolean }) =>
    apiClient.post<RatingOut>(`/loans/${loanId}/rate`, data),

  getBlacklist: () => apiClient.get<BlacklistEntry[]>("/blacklist"),

  blockUser: (blocked_user_id: string, reason?: string) =>
    apiClient.post<BlacklistEntry>("/blacklist", { blocked_user_id, reason }),

  unblock: (userId: string) => apiClient.delete(`/blacklist/${userId}`),
};

export const profileApi = {
  getPublic: (slug: string) => apiClient.get<PublicProfile>(`/public/users/${slug}`),

  getPublicBooks: (slug: string) => apiClient.get<PublicBook[]>(`/public/users/${slug}/books`),

  updateOwn: (data: { profile_slug?: string; bio?: string; is_public?: boolean; name?: string }) =>
    apiClient.put<PublicProfile>("/profile/me", data),
};

export const statsApi = {
  summary: () => apiClient.get<{
    total_books: number;
    by_status: Record<string, number>;
    read_this_year: number;
    read_this_month: number;
  }>("/stats/summary"),

  reading: () => apiClient.get<{ monthly: Array<{ month: string; count: number }> }>("/stats/reading"),

  lending: () => apiClient.get<{
    total_lent: number;
    total_borrowed: number;
    on_time_rate: number;
    most_lent_books: Array<{ user_book_id: string; times: number }>;
  }>("/stats/lending"),
};
