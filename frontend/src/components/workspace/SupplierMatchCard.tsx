import React, { useState } from "react";
import { SupplierMatchResponse } from "@/types/api";
import { Building2, ChevronDown, ChevronRight } from "lucide-react";

export function SupplierMatchCard({
  match,
}: {
  match: SupplierMatchResponse | null | undefined;
}) {
  const [showEvidence, setShowEvidence] = useState(false);

  if (!match || match.candidates.length === 0) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 space-y-2">
        <div className="flex items-center justify-between pb-2 border-b border-slate-800">
          <span className="font-semibold text-xs text-slate-200">🏢 Suggested Supplier Match</span>
          <span className="text-[10px] font-mono text-slate-400">No Match</span>
        </div>
        <p className="text-xs text-slate-400">No supplier directory match candidates found.</p>
      </div>
    );
  }

  const primaryCandidate = match.candidates[0];
  const confidencePct = (parseFloat(primaryCandidate.confidence || "0") * 100).toFixed(1);

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 space-y-2.5">
      <div className="flex items-center justify-between pb-2 border-b border-slate-800">
        <span className="font-semibold text-xs text-slate-200 flex items-center space-x-1.5">
          <Building2 className="w-3.5 h-3.5 text-blue-400" />
          <span>Suggested Supplier Match</span>
        </span>
        <span className="text-[10px] font-mono text-blue-400 bg-blue-950/60 border border-blue-900/80 px-2 py-0.5 rounded">
          AI / Rule Recommendation
        </span>
      </div>

      <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 text-xs space-y-1.5">
        <div className="flex items-center justify-between">
          <span className="font-bold text-slate-100">{primaryCandidate.supplier_name}</span>
          <span className="font-mono text-xs text-emerald-400 font-semibold">{confidencePct}% Confidence</span>
        </div>

        <div className="text-[11px] font-mono text-slate-400">
          Ref: <span className="text-slate-300">{primaryCandidate.supplier_reference}</span>
        </div>

        <p className="text-[11px] text-slate-300 italic">{primaryCandidate.explanation}</p>

        <div className="pt-1">
          <button
            onClick={() => setShowEvidence(!showEvidence)}
            className="text-[10px] font-mono text-slate-400 hover:text-slate-200 flex items-center space-x-1"
          >
            {showEvidence ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
            <span>{showEvidence ? "Hide Match Evidence" : "Inspect Match Evidence"}</span>
          </button>

          {showEvidence && (
            <pre className="mt-1 p-2 bg-slate-900 rounded border border-slate-800 text-[10px] font-mono text-slate-300 overflow-x-auto">
              {JSON.stringify(primaryCandidate.evidence, null, 2)}
            </pre>
          )}
        </div>
      </div>
    </div>
  );
}
