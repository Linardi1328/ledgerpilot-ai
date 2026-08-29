"use client";

import React, { useState } from "react";
import { Modal } from "../ui/Modal";
import { XCircle, AlertTriangle } from "lucide-react";

export function RejectDialog({
  isOpen,
  onClose,
  onConfirmReject,
}: {
  isOpen: boolean;
  onClose: () => void;
  onConfirmReject: (reason: string) => Promise<void>;
}) {
  const [reason, setReason] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!reason.trim()) {
      setError("A non-empty rejection reason is required.");
      return;
    }

    try {
      setIsSubmitting(true);
      setError(null);
      await onConfirmReject(reason.trim());
      onClose();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Rejection failed.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Reject Accounting Review Task" maxWidth="md">
      <form onSubmit={handleSubmit} className="space-y-4 text-xs text-slate-200">
        <div className="bg-rose-950/40 border border-rose-800/60 p-3 rounded-lg flex items-start space-x-2.5">
          <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
          <p className="text-[11px] leading-relaxed text-rose-200">
            <strong>Terminal Action Warning</strong>: Rejection is an immutable accounting review outcome. The task will be closed and no journal entries will be posted.
          </p>
        </div>

        <div>
          <label htmlFor="rejectionReason" className="block text-slate-300 font-medium mb-1">
            Mandatory Rejection Reason:
          </label>
          <textarea
            id="rejectionReason"
            rows={3}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="Explain why this invoice/transaction is rejected (e.g. fraudulent duplicate, invalid tax invoice, wrong corporate billing entity)..."
            required
            className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-rose-500"
          />
        </div>

        {error && (
          <div className="bg-rose-950/60 border border-rose-800 text-rose-300 p-2.5 rounded text-xs">
            {error}
          </div>
        )}

        <div className="flex items-center justify-end space-x-2 pt-2 border-t border-slate-800">
          <button
            type="button"
            onClick={onClose}
            disabled={isSubmitting}
            className="px-3.5 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium transition"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={!reason.trim() || isSubmitting}
            className="px-4 py-1.5 rounded bg-rose-600 hover:bg-rose-500 text-white text-xs font-bold transition flex items-center space-x-1.5"
          >
            <XCircle className="w-3.5 h-3.5" />
            <span>{isSubmitting ? "Rejecting..." : "Confirm Rejection"}</span>
          </button>
        </div>
      </form>
    </Modal>
  );
}
