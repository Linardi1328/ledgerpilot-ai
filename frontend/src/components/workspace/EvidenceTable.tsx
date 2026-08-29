import React from "react";
import { ExtractedFieldResponse } from "@/types/api";
import { Edit3 } from "lucide-react";

export function EvidenceTable({
  fields,
  onOpenCorrection,
  canCorrect = true,
}: {
  fields: ExtractedFieldResponse[];
  onOpenCorrection?: (field: ExtractedFieldResponse) => void;
  canCorrect?: boolean;
}) {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 space-y-3 text-slate-100">
      <div className="flex items-center justify-between pb-2 border-b border-slate-800">
        <span className="font-semibold text-xs text-slate-200">📄 Extracted Source Evidence</span>
        <span className="text-[10px] font-mono text-slate-400">Non-Destructive Lineage</span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
        {fields.map((field) => {
          const confidencePct = field.confidence
            ? `${(parseFloat(field.confidence) * 100).toFixed(0)}%`
            : null;

          return (
            <div
              key={field.id}
              className={`p-3 rounded-lg border text-xs space-y-1 ${
                field.corrected
                  ? "bg-slate-950 border-blue-800/60"
                  : "bg-slate-950 border-slate-800"
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="font-mono text-[11px] text-slate-400">{field.field_path}</span>

                <div className="flex items-center space-x-1.5">
                  {field.corrected && (
                    <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-blue-950 text-blue-300 border border-blue-800">
                      Rev {field.latest_revision_number || 1}
                    </span>
                  )}
                  {canCorrect && onOpenCorrection && (
                    <button
                      onClick={() => onOpenCorrection(field)}
                      title="Correct extracted field"
                      className="p-1 text-slate-400 hover:text-blue-300 rounded hover:bg-slate-800 transition"
                    >
                      <Edit3 className="w-3 h-3" />
                    </button>
                  )}
                </div>
              </div>

              <div className="font-mono font-semibold text-slate-100 text-xs">
                {field.effective_raw_value}
              </div>

              {field.corrected && field.original_raw_value !== field.effective_raw_value && (
                <div className="text-[10px] font-mono text-slate-400">
                  Original: <span className="text-amber-400/90 line-through">{field.original_raw_value}</span>
                </div>
              )}

              <div className="flex items-center justify-between text-[10px] font-mono text-slate-500 pt-1">
                <span>{confidencePct ? `Confidence: ${confidencePct}` : "Deterministic"}</span>
                {field.source_page_number && <span>Page {field.source_page_number}</span>}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
