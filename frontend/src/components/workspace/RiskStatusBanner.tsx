import React from "react";
import { ReviewEscalationState, ReviewRiskClass, ReviewTaskStatus } from "@/types/roles";
import { ReviewTaskResponse } from "@/types/api";
import { StatusBadge } from "../ui/Badge";
import { Shield, AlertTriangle, XCircle, Info } from "lucide-react";

export function RiskStatusBanner({
  task,
  ownerLabel,
}: {
  task: ReviewTaskResponse;
  ownerLabel?: string;
}) {
  const isOrdinary = task.risk_class === ReviewRiskClass.ORDINARY || task.risk_class === "ordinary";
  const isSenior =
    task.risk_class === ReviewRiskClass.SENIOR_REVIEW_REQUIRED ||
    task.risk_class === "senior_review_required";
  const isBlocked = task.risk_class === ReviewRiskClass.BLOCKED || task.risk_class === "blocked";
  const isInfoReq =
    task.status === ReviewTaskStatus.INFORMATION_REQUESTED ||
    task.status === "information_requested";

  const getContainerStyle = () => {
    if (isBlocked) return "bg-rose-950/40 border-rose-800/80 text-rose-200";
    if (isSenior) return "bg-amber-950/40 border-amber-800/80 text-amber-200";
    if (isInfoReq) return "bg-purple-950/40 border-purple-800/80 text-purple-200";
    return "bg-slate-800/80 border-slate-700 text-slate-200";
  };

  const getIcon = () => {
    if (isBlocked) return <XCircle className="w-6 h-6 text-rose-400 shrink-0" />;
    if (isSenior) return <AlertTriangle className="w-6 h-6 text-amber-400 shrink-0" />;
    if (isInfoReq) return <Info className="w-6 h-6 text-purple-400 shrink-0" />;
    return <Shield className="w-6 h-6 text-blue-400 shrink-0" />;
  };

  const getTitle = () => {
    if (isBlocked) return "APPROVAL BLOCKED BY CONTROLS";
    if (isSenior) return "SENIOR REVIEW REQUIRED";
    if (isInfoReq) return "INFORMATION REQUESTED";
    return "ORDINARY REVIEW";
  };

  const getDescription = () => {
    if (isBlocked) {
      return "Deterministic accounting controls block approval. Proposed journal is unbalanced or contains error findings. Resolve errors before approval.";
    }
    if (isSenior) {
      return "Senior reviewer authority is required before this transaction can be approved. Triggered by duplicate detection, new supplier, or material warning.";
    }
    if (isInfoReq) {
      return "Workflow is currently waiting for client submitter response. Approval controls are disabled until the request is answered or rejected.";
    }
    return "Human review required. Deterministic validation checks passed. Double-entry journal is balanced.";
  };

  return (
    <div className={`border rounded-lg p-4 flex flex-wrap items-center justify-between gap-3 ${getContainerStyle()}`}>
      <div className="flex items-center space-x-3">
        <div className="p-2 rounded-lg bg-slate-900/60 border border-slate-800">{getIcon()}</div>
        <div>
          <div className="flex items-center space-x-2">
            <span className="font-bold text-sm tracking-tight text-slate-100">{getTitle()}</span>
            <StatusBadge status={task.status} />
          </div>
          <p className="text-xs text-slate-300 mt-0.5 max-w-2xl">{getDescription()}</p>
        </div>
      </div>

      <div className="text-right text-xs space-y-0.5 font-mono">
        <div className="text-slate-400">
          Owner: <span className="text-slate-200 font-semibold">{ownerLabel || task.owner_membership_id}</span>
        </div>
        <div className="text-slate-500 text-[11px]">
          {task.escalation_state === ReviewEscalationState.SENIOR_REVIEW ||
          task.escalation_state === "senior_review"
            ? `Escalation: senior_review (${task.escalated_at ? new Date(task.escalated_at).toUTCString() : "Active"})`
            : "Escalation: None"}
        </div>
      </div>
    </div>
  );
}
