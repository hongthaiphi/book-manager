import apiClient from "./client";

export interface Building {
  id: string;
  name: string;
  address: string | null;
  invite_code: string | null;
  created_at: string;
}

export interface CommunityBook {
  id: string;
  owner_id: string;
  owner_name: string;
  owner_avatar: string | null;
  catalog_id: string;
  title: string;
  authors: string[] | null;
  cover_url: string | null;
  deposit_amount: number;
  lend_note: string | null;
  is_blocked: boolean;
}

export interface Member {
  id: string;
  name: string;
  avatar_url: string | null;
  profile_slug: string | null;
  phone_verified: boolean;
}

export const communityApi = {
  createBuilding: (name: string, address?: string) =>
    apiClient.post<Building>("/buildings", { name, address }),

  join: (invite_code: string) =>
    apiClient.post<Building>("/buildings/join", { invite_code }),

  myBuilding: () => apiClient.get<Building>("/buildings/me"),

  books: (params?: { limit?: number; offset?: number }) =>
    apiClient.get<CommunityBook[]>("/buildings/books", { params }),

  members: () => apiClient.get<Member[]>("/buildings/members"),
};
