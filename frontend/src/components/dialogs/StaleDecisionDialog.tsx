"use client";

import React, { useState } from "react";
import { Modal } from "../ui/Modal";
import { AlertTriangle, RefreshCw, CheckCircle2, ShieldAlert } from "lucide-react";

export function StaleDecisionDialog({
  isOpen,
  onClose,
  onGenerateFreshDecision,
}: {
  isOpen: boolean;
  onClose: () => void;
  onGenerateFreshDecision: (
    setStep: (step: string) => void,
    existingDecisionId?: string | null
  ) => Promise<void>;
}) {
  const [isRegenerating, setIsRegenerating] = useState(false);
  const [createdDecisionId, setCreatedDecisionId] = useState<string | null>(null);
  const [currentStep, setCurrentStep] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleRegenerate = async () => {
    try {
      setIsRegenerating(true);
      setError(null);
      await onGenerateFreshDecision(
        (step) => setCurrentStep(step),
        createdDecisionId
      );
      onClose();
    } catch (err: unknown) {
      const maybeDecId = (err as { createdDecisionId?: string })?.createdDecisionId;
      if (maybeDecId) {
        setCreatedDecisionId(maybeDecId);
      }
      setError(err instanceof Error ? err.message : "Failed to generate fresh accounting decision.");
      setCurrentStep(null);
    } finally {
      setIsRegenerating(false);
    }
  };

  const handleClose = () => {
    if (isRegenerating) return;
    setError(null);
    setCurrentStep(null);
    onClose();
  };

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title="Accounting Decision Out of Date" maxWidth="md">
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
          Because extracted source fields were corrected, the existing journal and risk classification must be re-evaluated deterministically. This workflow will create a new accounting decision run and review task.
        </p>

        {createdDecisionId && (
          <div className="bg-blue-950/60 border border-blue-800/80 p-3 rounded-lg space-y-1.5 text-blue-200">
            <div className="flex items-center space-x-1.5 font-semibold text-xs text-blue-300">
              <CheckCircle2 className="w-4 h-4 text-blue-400" />
              <span>Fresh Decision Run Created:</span>
            </div>
            <p className="font-mono text-[11px] bg-slate-950 p-1 rounded text-slate-200">
              {createdDecisionId}
            </p>
            <p className="text-[11px] text-blue-300">
              The accounting decision exists. Retry will create the review task for this decision without re-evaluating another decision run.
            </p>
          </div>
        )}

        {currentStep && (
          <div className="bg-slate-950 p-2.5 rounded border border-slate-800 font-mono text-[11px] text-blue-400 flex items-center space-x-2">
            <span className="w-3 h-3 border-2 border-blue-400 border-t-transparent rounded-full animate-spin shrink-0" />
            <span>{currentStep}</span>
          </div>
        )}

        {error && (
          <div className="bg-rose-950/60 border border-rose-800 text-rose-300 p-2.5 rounded text-xs space-y-1">
            <div className="flex items-center space-x-1 font-semibold">
              <ShieldAlert className="w-3.5 h-3.5" />
              <span>Workflow Interrupted:</span>
            </div>
            <p>{error}</p>
          </div>
        )}

        <div className="flex items-center justify-end space-x-2 pt-2 border-t border-slate-800">
          <button
            type="button"
            onClick={handleClose}
            disabled={isRegenerating}
            className="px-3.5 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium transition"
          >
            Close
          </button>
          <button
            type="button"
            onClick={handleRegenerate}
            disabled={isRegenerating}
            className="px-4 py-1.5 rounded bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold transition flex items-center space-x-1.5 disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRegenerating ? "animate-spin" : ""}`} />
            <span>
              {isRegenerating
                ? "Processing..."
                : createdDecisionId
                ? "Retry Creating Review Task"
                : "Generate Fresh Accounting Decision"}
            </span>
          </button>
        </div>
      </div>
    </Modal>
  );
}
