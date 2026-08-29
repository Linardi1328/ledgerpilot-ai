"use client";

import React, { useState } from "react";
import { Modal } from "../ui/Modal";
import { ReviewTaskResponse, ProposedJournalResponse } from "@/types/api";
import { Principal } from "@/types/roles";
import { formatMoney } from "@/lib/decimal/money";
import { CheckCircle2, ShieldAlert } from "lucide-react";

export function ApproveDialog({
  isOpen,
  onClose,
  task,
  journal,
  principal,
  onConfirmApprove,
}: {
  isOpen: boolean;
  onClose: () => void;
  task: ReviewTaskResponse | null;
  journal: ProposedJournalResponse | null;
  principal: Principal | null;
  onConfirmApprove: (note?: string) => Promise<void>;
}) {
  const [note, setNote] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!task || !journal || !principal) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setIsSubmitting(true);
      setError(null);
      await onConfirmApprove(note.trim() || undefined);
      onClose();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Approval request failed.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Confirm Accounting Approval" maxWidth="lg">
      <form onSubmit={handleSubmit} className="space-y-4 text-xs text-slate-200">
        <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 space-y-2 font-mono text-[11px]">
          <div className="flex justify-between">
            <span className="text-slate-400">Review Task:</span>
            <span className="text-slate-200">{task.id}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-400">Risk Class:</span>
            <span className="text-slate-200 uppercase font-semibold">{task.risk_class}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-400">Journal Balance:</span>
            <span className="text-emerald-400 font-semibold">
              {formatMoney(journal.total_debits, journal.currency)} (Balanced)
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-400">Authorising Actor:</span>
            <span className="text-blue-400 font-semibold">{principal.membership_id}</span>
          </div>
        </div>

        <div className="bg-blue-950/40 border border-blue-800/60 p-3 rounded-lg flex items-start space-x-2.5">
          <ShieldAlert className="w-4 h-4 text-blue-400 shrink-0 mt-0.5" />
          <p className="text-[11px] leading-relaxed text-blue-200">
            You are confirming that you have reviewed the available source evidence, accounting recommendations, validation findings, and proposed journal. This action creates an <strong>attributable human review outcome</strong>.
          </p>
        </div>

        <div>
          <label htmlFor="approvalNote" className="block text-slate-300 font-medium mb-1">
            Approval Note (Optional):
          </label>
          <textarea
            id="approvalNote"
            rows={2}
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="Add optional notes or practitioner verification references..."
            className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
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
            disabled={isSubmitting}
            className="px-4 py-1.5 rounded bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold transition flex items-center space-x-1.5"
          >
            {isSubmitting ? (
              <span>Authorizing...</span>
            ) : (
              <>
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>Confirm Accounting Approval</span>
              </>
            )}
          </button>
        </div>
      </form>
    </Modal>
  );
}
