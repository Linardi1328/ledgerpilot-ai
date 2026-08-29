"use client";

import React, { useState } from "react";
import { Modal } from "../ui/Modal";
import { AlertTriangle, RefreshCw } from "lucide-react";

export function StaleDecisionDialog({
  isOpen,
  onClose,
  onGenerateFreshDecision,
}: {
  isOpen: boolean;
  onClose: () => void;
  onGenerateFreshDecision: () => Promise<void>;
}) {
  const [isRegenerating, setIsRegenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleRegenerate = async () => {
    try {
      setIsRegenerating(true);
      setError(null);
      await onGenerateFreshDecision();
      onClose();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to regenerate accounting decision.");
    } finally {
      setIsRegenerating(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Accounting Decision Out of Date" maxWidth="md">
      <div className="space-y-4 text-xs text-slate-200">
        <div className="bg-amber-950/50 border border-amber-800/80 p-3 rounded-lg flex items-start space-x-2.5">
          <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <strong className="font-bold text-amber-100">Accounting decision is out of date</strong>
            <p className="text-[11px] leading-relaxed text-amber-200">
              Source information changed after this accounting decision was generated. Create a fresh accounting decision and review task before approval.
            </p>
          </div>
        </div>

        <p className="text-slate-300">
          Because extracted source fields were corrected, the existing journal and risk classification must be re-evaluated deterministically.
        </p>

        {error && (
          <div className="bg-rose-950/60 border border-rose-800 text-rose-300 p-2.5 rounded text-xs">
            {error}
          </div>
        )}

        <div className="flex items-center justify-end space-x-2 pt-2 border-t border-slate-800">
          <button
            type="button"
            onClick={onClose}
            disabled={isRegenerating}
            className="px-3.5 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium transition"
          >
            Close
          </button>
          <button
            type="button"
            onClick={handleRegenerate}
            disabled={isRegenerating}
            className="px-4 py-1.5 rounded bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold transition flex items-center space-x-1.5"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRegenerating ? "animate-spin" : ""}`} />
            <span>{isRegenerating ? "Regenerating..." : "Generate Fresh Accounting Decision"}</span>
          </button>
        </div>
      </div>
    </Modal>
  );
}
