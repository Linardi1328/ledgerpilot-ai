"use client";

import React, { useState } from "react";
import { Modal } from "../ui/Modal";
import { HelpCircle } from "lucide-react";

export function InfoRequestDialog({
  isOpen,
  onClose,
  onConfirmRequest,
}: {
  isOpen: boolean;
  onClose: () => void;
  onConfirmRequest: (question: string) => Promise<void>;
}) {
  const [question, setQuestion] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim()) {
      setError("Question body is required.");
      return;
    }

    try {
      setIsSubmitting(true);
      setError(null);
      await onConfirmRequest(question.trim());
      onClose();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Information request failed.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Request Information from Client" maxWidth="md">
      <form onSubmit={handleSubmit} className="space-y-4 text-xs text-slate-200">
        <p className="text-slate-300">
          This question will be sent to the client submitter portal. The task status will transition to{" "}
          <code className="text-purple-400 font-mono">information_requested</code> and approval will be blocked until a response is received.
        </p>

        <div>
          <label htmlFor="infoQuestion" className="block text-slate-300 font-medium mb-1">
            Question for Submitter (Required):
          </label>
          <textarea
            id="infoQuestion"
            rows={3}
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="e.g. Please clarify if this invoice includes hardware installation services or goods only..."
            required
            className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-purple-500"
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
            disabled={!question.trim() || isSubmitting}
            className="px-4 py-1.5 rounded bg-purple-600 hover:bg-purple-500 text-white text-xs font-bold transition flex items-center space-x-1.5"
          >
            <HelpCircle className="w-3.5 h-3.5" />
            <span>{isSubmitting ? "Sending..." : "Send Request to Client"}</span>
          </button>
        </div>
      </form>
    </Modal>
  );
}
