"use client";

import React, { useState } from "react";
import { ReviewCommentResponse } from "@/types/api";
import { Send, FileText, HelpCircle } from "lucide-react";

export function PortalCard({
  documentFilename,
  inquiry,
  onSubmitResponse,
}: {
  documentFilename?: string;
  inquiry: ReviewCommentResponse | null;
  onSubmitResponse: (responseBody: string) => Promise<void>;
}) {
  const [responseBody, setResponseBody] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!responseBody.trim()) {
      setError("Please provide a response before submitting.");
      return;
    }

    try {
      setIsSubmitting(true);
      setError(null);
      await onSubmitResponse(responseBody.trim());
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to submit response.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="bg-slate-900 border border-purple-900/60 rounded-xl p-5 space-y-4 max-w-2xl mx-auto shadow-xl text-slate-100">
      <div className="flex items-center justify-between pb-3 border-b border-slate-800">
        <div className="flex items-center space-x-2">
          <FileText className="w-4 h-4 text-purple-400" />
          <span className="font-bold text-sm text-slate-100">
            Document: {documentFilename || "Uploaded Invoice"}
          </span>
        </div>
        <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-purple-950 text-purple-300 border border-purple-800">
          Information Required
        </span>
      </div>

      {inquiry ? (
        <div className="bg-slate-950 p-4 rounded-lg border border-slate-800 space-y-2">
          <div className="flex items-center space-x-1.5 text-xs text-purple-300 font-semibold">
            <HelpCircle className="w-4 h-4" />
            <span>Accounting Team Inquiry:</span>
          </div>
          <p className="text-xs text-slate-200 leading-relaxed font-sans">{inquiry.body}</p>
        </div>
      ) : (
        <div className="text-xs text-slate-400 p-3 bg-slate-950 rounded border border-slate-800">
          No outstanding questions pending for this document.
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-3">
        <div>
          <label htmlFor="portalResponseInput" className="block text-xs font-semibold text-slate-300 mb-1">
            Your Response / Clarification (Required):
          </label>
          <textarea
            id="portalResponseInput"
            rows={4}
            value={responseBody}
            onChange={(e) => setResponseBody(e.target.value)}
            placeholder="Type your explanation or response to the accounting inquiry here..."
            required
            disabled={isSubmitting || !inquiry}
            className="w-full bg-slate-950 border border-slate-800 rounded p-3 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-purple-500"
          />
        </div>

        {error && (
          <div className="bg-rose-950/60 border border-rose-800 text-rose-300 p-2.5 rounded text-xs">
            {error}
          </div>
        )}

        <div className="flex items-center justify-end">
          <button
            type="submit"
            disabled={!responseBody.trim() || isSubmitting || !inquiry}
            className="px-5 py-2 rounded bg-purple-600 hover:bg-purple-500 text-white text-xs font-bold transition flex items-center space-x-1.5 disabled:opacity-50"
          >
            <Send className="w-3.5 h-3.5" />
            <span>{isSubmitting ? "Submitting..." : "Submit Information Response"}</span>
          </button>
        </div>
      </form>
    </div>
  );
}

export function PortalSuccess({
  onReset,
}: {
  onReset?: () => void;
}) {
  return (
    <div className="bg-slate-900 border border-emerald-800/80 rounded-xl p-6 text-center space-y-4 max-w-2xl mx-auto shadow-xl text-slate-100">
      <div className="w-12 h-12 rounded-full bg-emerald-950 border border-emerald-700 flex items-center justify-center mx-auto text-emerald-400 text-xl font-bold">
        ✓
      </div>

      <div className="space-y-1">
        <h3 className="font-bold text-base text-slate-100">Information Response Submitted</h3>
        <p className="text-xs text-slate-300 max-w-md mx-auto">
          Your clarification has been recorded and submitted to the accounting review team. The review task has returned to the review queue.
        </p>
      </div>

      {onReset && (
        <div className="pt-2">
          <button
            onClick={onReset}
            className="px-4 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium transition"
          >
            Back to Portal Inbox
          </button>
        </div>
      )}
    </div>
  );
}
