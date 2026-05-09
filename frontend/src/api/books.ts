import apiClient from "./client";

export interface BookCatalog {
  id: string;
  isbn: string | null;
  title: string;
  authors: string[] | null;
  publisher: string | null;
  published_at: string | null;
  cover_url: string | null;
  language: string;
  page_count: number | null;
  description: string | null;
}

export interface UserBook {
  id: string;
  user_id: string;
  catalog: BookCatalog;
  status: string;
  started_at: string | null;
  finished_at: string | null;
  acquired_how: string | null;
  gift_from: string | null;
  purchase_price: string | null;
  purchase_where: string | null;
  purchase_reason: string | null;
  personal_rating: number | null;
  met_expectations: boolean | null;
  personal_note: string | null;
  physical_cover_url: string | null;
  can_lend: boolean;
  deposit_amount: string;
  lend_note: string | null;
  tags: string[] | null;
  is_public: boolean;
  created_at: string;
  updated_at: string;
}

export interface UserBookCreate {
  // Catalog data (when adding manually or from search)
  isbn?: string;
  title?: string;
  authors?: string[];
  publisher?: string;
  published_at?: string;
  cover_url?: string;
  language?: string;
  page_count?: number;
  description?: string;
  genres?: string[];
  source?: string;
  catalog_id?: string;

  // Personal data
  status?: string;
  acquired_how?: string;
  gift_from?: string;
  purchase_price?: number;
  purchase_where?: string;
  purchase_reason?: string;
  can_lend?: boolean;
  deposit_amount?: number;
  lend_note?: string;
  tags?: string[];
  is_public?: boolean;
}

export interface UserBookUpdate {
  status?: string;
  acquired_how?: string;
  purchase_price?: number;
  purchase_where?: string;
  personal_rating?: number;
  met_expectations?: boolean;
  personal_note?: string;
  can_lend?: boolean;
  deposit_amount?: number;
  lend_note?: string;
  tags?: string[];
  is_public?: boolean;
}

export interface BookSearchResult {
  isbn: string | null;
  title: string;
  authors: string[];
  publisher: string | null;
  published_at: string | null;
  cover_url: string | null;
  language: string;
  page_count: number | null;
  description: string | null;
  genres: string[];
  source: string;
}

export interface ImportResult {
  imported: number;
  skipped: number;
  errors: string[];
}

export const booksApi = {
  list: (params?: { status?: string; can_lend?: boolean; q?: string }) =>
    apiClient.get<UserBook[]>("/books", { params }),

  get: (id: string) => apiClient.get<UserBook>(`/books/${id}`),

  add: (data: UserBookCreate) => apiClient.post<UserBook>("/books", data),

  update: (id: string, data: UserBookUpdate) =>
    apiClient.put<UserBook>(`/books/${id}`, data),

  delete: (id: string) => apiClient.delete(`/books/${id}`),

  lookupIsbn: (isbn: string) =>
    apiClient.get<BookSearchResult>(`/catalog/lookup/isbn/${isbn}`),

  search: (q: string) =>
    apiClient.get<BookSearchResult[]>("/catalog/search", { params: { q } }),

  importGoodreads: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return apiClient.post<ImportResult>("/books/import/goodreads", form, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },
};
