import React from "react";
import { DuplicateCandidateResponse } from "@/types/api";
import { Copy, AlertTriangle } from "lucide-react";

export function DuplicateCard({
  candidates,
}: {
  candidates: DuplicateCandidateResponse[];
}) {
  if (!candidates || candidates.length === 0) {
    return null;
  }

  return (
    <div className="bg-slate-900 border border-amber-900/60 rounded-lg p-4 space-y-3">
      <div className="flex items-center justify-between pb-2 border-b border-slate-800">
        <span className="font-semibold text-xs text-amber-300 flex items-center space-x-1.5">
          <Copy className="w-3.5 h-3.5" />
          <span>Possible Duplicate Detection</span>
        </span>
        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-950 text-amber-300 border border-amber-800">
          Senior Review Required Trigger
        </span>
      </div>

      <div className="space-y-2">
        {candidates.map((cand) => (
          <div key={cand.id} className="bg-slate-950 p-3 rounded-lg border border-slate-800 text-xs space-y-1.5 font-mono">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-amber-200">Matching Prior Document</span>
              <span className="text-emerald-400">{(parseFloat(cand.confidence) * 100).toFixed(1)}% Confidence</span>
            </div>

            <p className="text-[11px] text-slate-300 font-sans">{cand.explanation}</p>

            <div className="text-[10px] text-slate-500 pt-1 space-y-0.5">
              <div>Candidate Document: {cand.candidate_document_id}</div>
              <div>Candidate Decision: {cand.candidate_decision_run_id}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
