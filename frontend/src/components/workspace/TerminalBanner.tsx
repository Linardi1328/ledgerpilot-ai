import React from "react";
import { ReviewOutcomeResponse, ReviewTaskResponse } from "@/types/api";
import { ReviewOutcomeType } from "@/types/roles";
import { CheckCircle, XCircle } from "lucide-react";

export function TerminalBanner({
  task,
  outcome,
}: {
  task: ReviewTaskResponse;
  outcome: ReviewOutcomeResponse | null | undefined;
}) {
  const isApproved =
    outcome?.outcome_type === ReviewOutcomeType.APPROVED ||
    outcome?.outcome_type === ReviewOutcomeType.CORRECTED_AND_APPROVED ||
    task.status === "approved";

  const isCorrected =
    outcome?.outcome_type === ReviewOutcomeType.CORRECTED_AND_APPROVED ||
    (outcome?.source_correction_count && outcome.source_correction_count > 0);

  return (
    <div
      className={`border rounded-lg p-5 space-y-3 shadow-lg ${
        isApproved
          ? "bg-emerald-950/40 border-emerald-800/80 text-emerald-100"
          : "bg-rose-950/40 border-rose-800/80 text-rose-100"
      }`}
    >
      <div className="flex items-center space-x-3">
        <div
          className={`p-2 rounded-lg ${
            isApproved ? "bg-emerald-900/60 text-emerald-300" : "bg-rose-900/60 text-rose-300"
          }`}
        >
          {isApproved ? <CheckCircle className="w-6 h-6" /> : <XCircle className="w-6 h-6" />}
        </div>
        <div>
          <h3 className="font-bold text-sm tracking-tight text-white">
            {isApproved
              ? isCorrected
                ? "Attributable Accounting Review Outcome: Corrected and Approved"
                : "Attributable Accounting Review Outcome: Approved"
              : "Attributable Accounting Review Outcome: Rejected"}
          </h3>
          <p className="text-xs text-slate-300 mt-0.5">
            {isApproved
              ? isCorrected
                ? "Human corrections to extracted source information were incorporated before this accounting decision was approved."
                : "This transaction was reviewed and confirmed by an authorised accountant. A permanent journal record was authorized."
              : "This review task was rejected. No posting records were exported to general ledger."}
          </p>
        </div>
      </div>

      {outcome && (
        <div className="bg-slate-950/80 border border-slate-800/80 rounded p-3 text-xs font-mono grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-2 text-slate-300">
          <div>
            <span className="text-slate-500 block text-[10px]">Actor User</span>
            <span className="font-semibold text-slate-200">{outcome.actor_user_id.slice(0, 12)}...</span>
          </div>
          <div>
            <span className="text-slate-500 block text-[10px]">Timestamp</span>
            <span className="text-slate-200">{new Date(outcome.created_at).toUTCString()}</span>
          </div>
          <div>
            <span className="text-slate-500 block text-[10px]">Corrections</span>
            <span className="text-slate-200">{outcome.source_correction_count || 0} applied</span>
          </div>
          <div>
            <span className="text-slate-500 block text-[10px]">Resolution Note</span>
            <span className="text-slate-200 truncate">{outcome.reason || "None specified"}</span>
          </div>
        </div>
      )}
    </div>
  );
}
