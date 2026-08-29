import React, { useState } from "react";
import { AccountingDecisionFindingResponse } from "@/types/api";
import { AccountingFindingSeverity } from "@/types/roles";
import { AlertCircle, AlertTriangle, ChevronDown, ChevronRight, Info } from "lucide-react";

export function FindingsList({
  findings,
}: {
  findings: AccountingDecisionFindingResponse[];
}) {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const errors = findings.filter((f) => f.severity === AccountingFindingSeverity.ERROR || f.severity === "error");
  const warnings = findings.filter((f) => f.severity === AccountingFindingSeverity.WARNING || f.severity === "warning");
  const infos = findings.filter((f) => f.severity === AccountingFindingSeverity.INFO || f.severity === "info");

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 space-y-3">
      <div className="flex items-center justify-between pb-2 border-b border-slate-800">
        <span className="font-semibold text-xs text-slate-200">⚡ Deterministic Findings</span>
        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400">
          {errors.length} Error{errors.length === 1 ? "" : "s"} • {warnings.length} Warning{warnings.length === 1 ? "" : "s"}
        </span>
      </div>

      {findings.length === 0 ? (
        <div className="text-xs text-slate-400 p-3 text-center bg-slate-950/60 rounded border border-slate-800">
          ✓ No deterministic findings recorded. All checks passed.
        </div>
      ) : (
        <div className="space-y-2">
          {findings.map((f) => {
            const isError = f.severity === AccountingFindingSeverity.ERROR || f.severity === "error";
            const isWarning = f.severity === AccountingFindingSeverity.WARNING || f.severity === "warning";
            const isExpanded = expandedId === f.id;
            const hasEvidence = Object.keys(f.evidence || {}).length > 0;

            const cardStyle = isError
              ? "bg-rose-950/40 border-rose-800/80 text-rose-200"
              : isWarning
              ? "bg-amber-950/40 border-amber-800/80 text-amber-200"
              : "bg-blue-950/40 border-blue-800/80 text-blue-200";

            const badgeStyle = isError
              ? "bg-rose-900/60 text-rose-300 border-rose-700"
              : isWarning
              ? "bg-amber-900/60 text-amber-300 border-amber-700"
              : "bg-blue-900/60 text-blue-300 border-blue-700";

            return (
              <div key={f.id} className={`border rounded-lg p-3 text-xs space-y-1.5 ${cardStyle}`}>
                <div className="flex items-center justify-between font-semibold">
                  <div className="flex items-center space-x-1.5">
                    {isError ? (
                      <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
                    ) : isWarning ? (
                      <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
                    ) : (
                      <Info className="w-4 h-4 text-blue-400 shrink-0" />
                    )}
                    <span className="font-mono text-xs">{f.code}</span>
                  </div>

                  <div className="flex items-center space-x-2">
                    {f.field_path && (
                      <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-900/80 border border-slate-800 text-slate-300">
                        {f.field_path}
                      </span>
                    )}
                    <span className={`text-[10px] font-mono uppercase px-1.5 py-0.5 rounded border ${badgeStyle}`}>
                      {f.severity}
                    </span>
                  </div>
                </div>

                <p className="text-[11px] leading-relaxed text-slate-300">{f.description}</p>

                {hasEvidence && (
                  <div>
                    <button
                      onClick={() => setExpandedId(isExpanded ? null : f.id)}
                      className="text-[10px] font-mono text-slate-400 hover:text-slate-200 flex items-center space-x-1 pt-1"
                    >
                      {isExpanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
                      <span>{isExpanded ? "Hide Evidence" : "Inspect Evidence"}</span>
                    </button>

                    {isExpanded && (
                      <pre className="mt-1 p-2 bg-slate-950 rounded border border-slate-800 text-[10px] font-mono text-slate-300 overflow-x-auto">
                        {JSON.stringify(f.evidence, null, 2)}
                      </pre>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
