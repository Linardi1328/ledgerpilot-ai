import React from "react";
import { ProposedJournalResponse, ReviewTaskResponse } from "@/types/api";
import { Principal, ReviewRiskClass, ReviewTaskStatus, Role } from "@/types/roles";
import {
  canApproveOrdinary,
  canApproveSenior,
  canEscalate,
  canReject,
  canRequestInformation,
  isTerminalTask,
} from "@/lib/policy/action-policy";
import { CheckCircle2, CornerUpRight, HelpCircle, XCircle } from "lucide-react";

export function ActionBar({
  task,
  journal,
  principal,
  isStale = false,
  onOpenApprove,
  onOpenEscalate,
  onOpenInfoRequest,
  onOpenReject,
}: {
  task: ReviewTaskResponse | null | undefined;
  journal: ProposedJournalResponse | null | undefined;
  principal: Principal | null | undefined;
  isStale?: boolean;
  onOpenApprove: () => void;
  onOpenEscalate: () => void;
  onOpenInfoRequest: () => void;
  onOpenReject: () => void;
}) {
  if (!task || !principal || isTerminalTask(task) || principal.role === Role.AUDITOR) {
    return null;
  }

  const allowOrdinary = canApproveOrdinary(principal, task, journal, isStale);
  const allowSenior = canApproveSenior(principal, task, journal, isStale);
  const allowApprove = allowOrdinary || allowSenior;

  const allowEscalate = canEscalate(principal, task);
  const allowInfoReq = canRequestInformation(principal, task);
  const allowReject = canReject(principal, task);

  const getApproveDisabledTooltip = () => {
    if (isStale) return "Accounting decision is stale after newer field corrections.";
    if (task.risk_class === ReviewRiskClass.BLOCKED || task.risk_class === "blocked") {
      return "Approval blocked by deterministic controls (Unbalanced journal or error findings).";
    }
    if (
      (task.risk_class === ReviewRiskClass.SENIOR_REVIEW_REQUIRED ||
        task.risk_class === "senior_review_required") &&
      principal.role !== Role.SENIOR_REVIEWER
    ) {
      return "Senior reviewer authority is required for approval.";
    }
    if (
      task.status === ReviewTaskStatus.INFORMATION_REQUESTED ||
      task.status === "information_requested"
    ) {
      return "Approval blocked while awaiting client information response.";
    }
    if (task.owner_membership_id !== principal.membership_id) {
      return "Action requires current task ownership.";
    }
    if (!journal?.is_balanced) {
      return "A balanced proposed journal is required for approval.";
    }
    return "Approval not permitted in current state.";
  };

  return (
    <div className="bg-slate-950 border border-slate-800 rounded-lg p-3 flex flex-wrap items-center justify-between gap-3 shadow-lg">
      <div className="flex items-center space-x-2.5">
        {allowEscalate && (
          <button
            onClick={onOpenEscalate}
            className="px-3.5 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium transition flex items-center space-x-1.5 border border-slate-700"
          >
            <CornerUpRight className="w-3.5 h-3.5 text-amber-400" />
            <span>Escalate to Senior</span>
          </button>
        )}

        {allowInfoReq && (
          <button
            onClick={onOpenInfoRequest}
            className="px-3.5 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium transition flex items-center space-x-1.5 border border-slate-700"
          >
            <HelpCircle className="w-3.5 h-3.5 text-purple-400" />
            <span>Request Info</span>
          </button>
        )}

        {allowReject && (
          <button
            onClick={onOpenReject}
            className="px-3.5 py-1.5 rounded bg-slate-800 hover:bg-rose-900/50 text-rose-300 text-xs font-medium transition border border-slate-700"
          >
            <XCircle className="w-3.5 h-3.5 inline mr-1" />
            <span>Reject Task...</span>
          </button>
        )}
      </div>

      <div>
        <button
          onClick={onOpenApprove}
          disabled={!allowApprove}
          title={!allowApprove ? getApproveDisabledTooltip() : undefined}
          className={`px-5 py-2 rounded text-xs font-semibold shadow-lg transition flex items-center space-x-1.5 ${
            allowApprove
              ? allowSenior
                ? "bg-amber-600 hover:bg-amber-500 text-white cursor-pointer"
                : "bg-emerald-600 hover:bg-emerald-500 text-white cursor-pointer"
              : "bg-slate-800/80 text-slate-500 border border-slate-700 cursor-not-allowed"
          }`}
        >
          <CheckCircle2 className="w-4 h-4" />
          <span>
            {allowSenior ? "Authorize Senior Approval" : "Confirm & Authorize Approval"}
          </span>
        </button>
      </div>
    </div>
  );
}
