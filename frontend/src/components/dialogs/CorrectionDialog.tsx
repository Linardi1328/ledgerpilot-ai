"use client";

import React, { useState, useEffect } from "react";
import { Modal } from "../ui/Modal";
import { ExtractedFieldResponse, ExtractionFieldCorrectionRequest } from "@/types/api";
import { getFriendlyErrorMessage } from "@/lib/api/errors";
import { Edit3 } from "lucide-react";

export function CorrectionDialog({
  isOpen,
  onClose,
  field,
  onConfirmCorrection,
}: {
  isOpen: boolean;
  onClose: () => void;
  field: ExtractedFieldResponse | null;
  onConfirmCorrection: (
    fieldId: string,
    req: ExtractionFieldCorrectionRequest
  ) => Promise<void>;
}) {
  const [correctedValue, setCorrectedValue] = useState("");
  const [reason, setReason] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (field) {
      setCorrectedValue(field.effective_raw_value);
      setReason("");
      setError(null);
    }
  }, [field]);

  if (!field) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!reason.trim()) {
      setError("A reason for this correction is required.");
      return;
    }

    try {
      setIsSubmitting(true);
      setError(null);
      await onConfirmCorrection(field.id, {
        corrected_raw_value: correctedValue.trim(),
        corrected_normalized_value: correctedValue.trim(),
        corrected_value_type: field.value_type,
        reason: reason.trim(),
      });
      onClose();
    } catch (err: unknown) {
      setError(getFriendlyErrorMessage(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Correct Extracted Field Value" maxWidth="md">
      <form onSubmit={handleSubmit} className="space-y-4 text-xs text-slate-200">
        <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 space-y-1.5 font-mono text-[11px]">
          <div className="text-slate-400">
            Field: <span className="text-blue-400 font-semibold">{field.field_path}</span>
          </div>
          <div className="text-slate-400">
            Original Value: <span className="text-slate-200 font-semibold">{field.original_raw_value}</span>
          </div>
          <div className="text-slate-400">
            Current Effective Value: <span className="text-slate-200 font-semibold">{field.effective_raw_value}</span>
          </div>
        </div>

        <div>
          <label htmlFor="correctedValInput" className="block text-slate-300 font-medium mb-1">
            New Corrected Value (Required):
          </label>
          <input
            id="correctedValInput"
            type="text"
            value={correctedValue}
            onChange={(e) => setCorrectedValue(e.target.value)}
            required
            className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-xs text-slate-200 font-mono focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>

        <div>
          <label htmlFor="correctionReasonInput" className="block text-slate-300 font-medium mb-1">
            Reason for Correction (Required):
          </label>
          <textarea
            id="correctionReasonInput"
            rows={2}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="Explain why this extracted value required human correction..."
            required
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
            disabled={!reason.trim() || isSubmitting}
            className="px-4 py-1.5 rounded bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold transition flex items-center space-x-1.5"
          >
            <Edit3 className="w-3.5 h-3.5" />
            <span>{isSubmitting ? "Saving..." : "Save Correction"}</span>
          </button>
        </div>
      </form>
    </Modal>
  );
}
