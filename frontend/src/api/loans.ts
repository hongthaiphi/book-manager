import apiClient from "./client";

export interface UserSummary {
  id: string;
  name: string;
  avatar_url: string | null;
  phone_verified: boolean;
}

export interface LoanRequest {
  id: string;
  user_book_id: string;
  lender_id: string;
  borrower_id: string;
  message: string | null;
  status: string;
  agreed_deposit: string | null;
  meet_location: string | null;
  agreed_at: string | null;
  rejected_reason: string | null;
  created_at: string;
  updated_at: string;
  lender: UserSummary;
  borrower: UserSummary;
}

export interface Loan {
  id: string;
  loan_request_id: string;
  user_book_id: string;
  lender_id: string;
  borrower_id: string;
  lent_at: string;
  due_at: string | null;
  returned_at: string | null;
  status: string;
  lender_note: string | null;
  created_at: string;
  lender: UserSummary;
  borrower: UserSummary;
}

export interface Notification {
  id: string;
  type: string;
  title: string;
  body: string | null;
  is_read: boolean;
  content_type: string | null;
  content_id: string | null;
  created_at: string;
}

export const loansApi = {
  requestLoan: (bookId: string, message?: string) =>
    apiClient.post<LoanRequest>(`/books/${bookId}/request-loan`, { message }),

  listIncoming: (status?: string) =>
    apiClient.get<LoanRequest[]>("/loan-requests", { params: status ? { status } : {} }),

  listSent: () => apiClient.get<LoanRequest[]>("/loan-requests/sent"),

  approve: (id: string, data: { agreed_deposit: number; meet_location: string; due_days?: number }) =>
    apiClient.put<LoanRequest>(`/loan-requests/${id}/approve`, data),

  reject: (id: string, reason?: string) =>
    apiClient.put<LoanRequest>(`/loan-requests/${id}/reject`, { reason }),

  cancel: (id: string) => apiClient.delete(`/loan-requests/${id}`),

  listLoans: (status?: string) =>
    apiClient.get<Loan[]>("/loans", { params: status ? { status } : {} }),

  confirm: (loanRequestId: string, due_days = 14) =>
    apiClient.put<Loan>(`/loans/${loanRequestId}/confirm`, null, { params: { due_days } }),

  markReturned: (loanId: string, note?: string) =>
    apiClient.put<Loan>(`/loans/${loanId}/return`, null, { params: note ? { note } : {} }),
};

export const notificationsApi = {
  list: () => apiClient.get<Notification[]>("/notifications"),
  markRead: (id: string) => apiClient.put(`/notifications/${id}/read`),
  markAllRead: () => apiClient.put("/notifications/read-all"),
};
