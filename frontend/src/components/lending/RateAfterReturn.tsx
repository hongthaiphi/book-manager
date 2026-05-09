import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { trustApi } from "@/api/trust";

interface Props {
  loanId: string;
  borrowerName: string;
  onClose: () => void;
}

export default function RateAfterReturn({ loanId, borrowerName, onClose }: Props) {
  const [rating, setRating] = useState<boolean | null>(null);
  const [note, setNote] = useState("");
  const [blockUser, setBlockUser] = useState(false);
  const qc = useQueryClient();

  const mutation = useMutation({
    mutationFn: () =>
      trustApi.rateLoan(loanId, {
        is_positive: rating!,
        note: note || undefined,
        block_user: blockUser,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["loans-active"] });
      qc.invalidateQueries({ queryKey: ["loans-history"] });
      onClose();
    },
  });

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl max-w-md w-full p-6">
        <h3 className="text-lg font-bold mb-1">Đánh giá người mượn</h3>
        <p className="text-sm text-gray-500 mb-5">
          Bạn muốn đánh giá <strong>{borrowerName}</strong> như thế nào?
        </p>

        {/* Thumbs */}
        <div className="flex gap-4 mb-5">
          <button
            onClick={() => setRating(true)}
            className={`flex-1 py-4 rounded-xl text-3xl border-2 transition-all ${
              rating === true
                ? "border-green-400 bg-green-50"
                : "border-gray-200 hover:border-green-300"
            }`}
          >
            👍
            <div className="text-xs text-gray-600 mt-1">Đáng tin cậy</div>
          </button>
          <button
            onClick={() => setRating(false)}
            className={`flex-1 py-4 rounded-xl text-3xl border-2 transition-all ${
              rating === false
                ? "border-red-400 bg-red-50"
                : "border-gray-200 hover:border-red-300"
            }`}
          >
            👎
            <div className="text-xs text-gray-600 mt-1">Không đáng tin</div>
          </button>
        </div>

        {/* Note */}
        <textarea
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="Ghi chú (tuỳ chọn): trả đúng hạn, sách còn nguyên vẹn..."
          rows={3}
          className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-400"
        />

        {/* Block option — only if negative */}
        {rating === false && (
          <label className="flex items-center gap-2 mt-3 cursor-pointer">
            <input
              type="checkbox"
              checked={blockUser}
              onChange={(e) => setBlockUser(e.target.checked)}
              className="w-4 h-4"
            />
            <span className="text-sm text-red-600">Chặn người này khỏi mượn sách của tôi</span>
          </label>
        )}

        <div className="mt-5 flex justify-end gap-2">
          <button onClick={onClose} className="px-4 py-2 border border-gray-200 rounded-lg text-sm text-gray-500">
            Bỏ qua
          </button>
          <button
            onClick={() => mutation.mutate()}
            disabled={rating === null || mutation.isPending}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 disabled:opacity-40"
          >
            {mutation.isPending ? "Đang lưu…" : "Lưu đánh giá"}
          </button>
        </div>
      </div>
    </div>
  );
}
