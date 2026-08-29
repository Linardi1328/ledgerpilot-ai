"use client";

import React, { useState } from "react";
import { Modal } from "../ui/Modal";
import { DEV_USERS } from "@/lib/mock/fixtures";
import { CornerUpRight } from "lucide-react";

export function EscalateDialog({
  isOpen,
  onClose,
  onConfirmEscalate,
}: {
  isOpen: boolean;
  onClose: () => void;
  onConfirmEscalate: (seniorMembershipId: string, reason: string) => Promise<void>;
}) {
  const [seniorMembershipId, setSeniorMembershipId] = useState(DEV_USERS.senior.membership_id);
  const [reason, setReason] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!reason.trim()) {
      setError("An escalation reason is required.");
      return;
    }

    try {
      setIsSubmitting(true);
      setError(null);
      await onConfirmEscalate(seniorMembershipId, reason.trim());
      onClose();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Escalation failed.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Escalate to Senior Reviewer" maxWidth="md">
      <form onSubmit={handleSubmit} className="space-y-4 text-xs text-slate-200">
        <div>
          <label htmlFor="seniorSelect" className="block text-slate-300 font-medium mb-1">
            Target Senior Reviewer:
          </label>
          <select
            id="seniorSelect"
            value={seniorMembershipId}
            onChange={(e) => setSeniorMembershipId(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:ring-1 focus:ring-amber-500 font-mono"
          >
            <option value={DEV_USERS.senior.membership_id}>
              {DEV_USERS.senior.name} ({DEV_USERS.senior.membership_id.slice(0, 8)}...)
            </option>
          </select>
          <p className="text-[10px] text-slate-500 mt-1">
            Note: Target membership ID is verified by backend RBAC against firm Senior Reviewer role.
          </p>
        </div>

        <div>
          <label htmlFor="escalateReason" className="block text-slate-300 font-medium mb-1">
            Reason for Escalation (Required):
          </label>
          <textarea
            id="escalateReason"
            rows={3}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="Explain why senior review is required (e.g. duplicate candidate verification, new supplier threshold, anomalous tax treatment)..."
            required
            className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-amber-500"
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
            className="px-4 py-1.5 rounded bg-amber-600 hover:bg-amber-500 text-white text-xs font-bold transition flex items-center space-x-1.5"
          >
            <CornerUpRight className="w-3.5 h-3.5" />
            <span>{isSubmitting ? "Escalating..." : "Confirm Escalation"}</span>
          </button>
        </div>
      </form>
    </Modal>
  );
}
