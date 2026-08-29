import React from "react";
import { ReviewRiskClass, ReviewTaskStatus } from "@/types/roles";

export function RiskBadge({ riskClass }: { riskClass: ReviewRiskClass | string }) {
  switch (riskClass) {
    case ReviewRiskClass.ORDINARY:
    case "ordinary":
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold bg-slate-800 border border-slate-700 text-slate-300">
          🛡️ Ordinary Review
        </span>
      );
    case ReviewRiskClass.SENIOR_REVIEW_REQUIRED:
    case "senior_review_required":
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold bg-amber-950/60 border border-amber-600 text-amber-300">
          🎖️ Senior Review Required
        </span>
      );
    case ReviewRiskClass.BLOCKED:
    case "blocked":
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold bg-rose-950 border border-rose-700 text-rose-300">
          🛑 Approval Blocked
        </span>
      );
    default:
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold bg-slate-800 text-slate-400">
          {riskClass}
        </span>
      );
  }
}

export function StatusBadge({ status }: { status: ReviewTaskStatus | string }) {
  switch (status) {
    case ReviewTaskStatus.OPEN:
    case "open":
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-mono font-medium bg-blue-950 border border-blue-800 text-blue-300">
          Open
        </span>
      );
    case ReviewTaskStatus.ESCALATED:
    case "escalated":
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-mono font-medium bg-amber-950 border border-amber-700 text-amber-300">
          Escalated
        </span>
      );
    case ReviewTaskStatus.INFORMATION_REQUESTED:
    case "information_requested":
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-mono font-medium bg-purple-950 border border-purple-800 text-purple-300">
          Info Requested
        </span>
      );
    case ReviewTaskStatus.APPROVED:
    case "approved":
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-mono font-semibold bg-emerald-950 border border-emerald-800 text-emerald-300">
          ✓ Approved
        </span>
      );
    case ReviewTaskStatus.REJECTED:
    case "rejected":
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-mono font-semibold bg-rose-950 border border-rose-800 text-rose-300">
          ✕ Rejected
        </span>
      );
    default:
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-mono bg-slate-800 text-slate-400">
          {status}
        </span>
      );
  }
}
