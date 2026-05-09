/**
 * Minimal toast system — no external deps.
 * Usage:
 *   import { toast } from "@/components/Toast"
 *   toast.success("Đã thêm sách!")
 *   toast.error("Có lỗi xảy ra")
 */

import { useEffect, useState } from "react";
import { create } from "zustand";

type ToastType = "success" | "error" | "info";

interface ToastItem {
  id: number;
  type: ToastType;
  message: string;
}

interface ToastState {
  items: ToastItem[];
  add: (type: ToastType, message: string) => void;
  remove: (id: number) => void;
}

let _nextId = 0;

const useToastStore = create<ToastState>((set) => ({
  items: [],
  add: (type, message) => {
    const id = ++_nextId;
    set((s) => ({ items: [...s.items, { id, type, message }] }));
    setTimeout(() => set((s) => ({ items: s.items.filter((i) => i.id !== id) })), 3500);
  },
  remove: (id) => set((s) => ({ items: s.items.filter((i) => i.id !== id) })),
}));

export const toast = {
  success: (msg: string) => useToastStore.getState().add("success", msg),
  error: (msg: string) => useToastStore.getState().add("error", msg),
  info: (msg: string) => useToastStore.getState().add("info", msg),
};

const COLORS: Record<ToastType, string> = {
  success: "bg-green-600",
  error: "bg-red-600",
  info: "bg-blue-600",
};

const ICONS: Record<ToastType, string> = {
  success: "✓",
  error: "✕",
  info: "ℹ",
};

export function Toaster() {
  const { items, remove } = useToastStore();

  return (
    <div className="fixed bottom-5 right-5 z-50 flex flex-col gap-2 pointer-events-none">
      {items.map((item) => (
        <div
          key={item.id}
          onClick={() => remove(item.id)}
          className={`flex items-center gap-3 px-4 py-3 rounded-xl text-white text-sm shadow-lg cursor-pointer pointer-events-auto animate-fade-in ${COLORS[item.type]}`}
        >
          <span className="font-bold text-base leading-none">{ICONS[item.type]}</span>
          <span>{item.message}</span>
        </div>
      ))}
    </div>
  );
}
