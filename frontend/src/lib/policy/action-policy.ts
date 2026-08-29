import {
  Permission,
  Principal,
  ReviewEscalationState,
  ReviewRiskClass,
  ReviewTaskStatus,
  Role,
} from "@/types/roles";
import { ProposedJournalResponse, ReviewTaskResponse } from "@/types/api";

export function isTerminalTask(task: ReviewTaskResponse | null | undefined): boolean {
  if (!task) return false;
  return (
    task.status === ReviewTaskStatus.APPROVED ||
    task.status === ReviewTaskStatus.REJECTED ||
    task.status === "approved" ||
    task.status === "rejected"
  );
}

export function canViewReviewWorkspace(principal: Principal | null | undefined): boolean {
  if (!principal) return false;
  if (principal.role === Role.FIRM_ADMIN || principal.role === Role.CLIENT_SUBMITTER) {
    return false;
  }
  return principal.permissions.includes(Permission.VIEW_REVIEW_TASK);
}

export function canViewClientPortal(principal: Principal | null | undefined): boolean {
  if (!principal) return false;
  return (
    principal.role === Role.CLIENT_SUBMITTER ||
    principal.permissions.includes(Permission.VIEW_INFORMATION_REQUEST)
  );
}

export function canApproveOrdinary(
  principal: Principal | null | undefined,
  task: ReviewTaskResponse | null | undefined,
  journal: ProposedJournalResponse | null | undefined,
  isStale = false
): boolean {
  if (!principal || !task || isTerminalTask(task) || isStale) return false;
  if (
    principal.role !== Role.ACCOUNTANT &&
    principal.role !== Role.SENIOR_REVIEWER
  ) {
    return false;
  }
  if (!principal.permissions.includes(Permission.APPROVE_ORDINARY_TRANSACTION)) {
    return false;
  }
  if (task.owner_membership_id !== principal.membership_id) {
    return false;
  }
  if (task.status !== ReviewTaskStatus.OPEN && task.status !== "open") {
    return false;
  }
  if (
    task.risk_class !== ReviewRiskClass.ORDINARY &&
    task.risk_class !== "ordinary"
  ) {
    return false;
  }
  if (!journal || !journal.is_balanced) {
    return false;
  }
  return true;
}

export function canApproveSenior(
  principal: Principal | null | undefined,
  task: ReviewTaskResponse | null | undefined,
  journal: ProposedJournalResponse | null | undefined,
  isStale = false
): boolean {
  if (!principal || !task || isTerminalTask(task) || isStale) return false;
  if (principal.role !== Role.SENIOR_REVIEWER) {
    return false;
  }
  if (!principal.permissions.includes(Permission.APPROVE_HIGH_RISK_TRANSACTION)) {
    return false;
  }
  if (task.owner_membership_id !== principal.membership_id) {
    return false;
  }
  if (task.status !== ReviewTaskStatus.ESCALATED && task.status !== "escalated") {
    return false;
  }
  if (
    task.escalation_state !== ReviewEscalationState.SENIOR_REVIEW &&
    task.escalation_state !== "senior_review"
  ) {
    return false;
  }
  if (
    task.risk_class !== ReviewRiskClass.SENIOR_REVIEW_REQUIRED &&
    task.risk_class !== "senior_review_required"
  ) {
    return false;
  }
  if (!journal || !journal.is_balanced) {
    return false;
  }
  return true;
}

export function canEscalate(
  principal: Principal | null | undefined,
  task: ReviewTaskResponse | null | undefined
): boolean {
  if (!principal || !task || isTerminalTask(task)) return false;
  if (
    principal.role !== Role.ACCOUNTANT &&
    principal.role !== Role.SENIOR_REVIEWER
  ) {
    return false;
  }
  if (!principal.permissions.includes(Permission.ESCALATE_TRANSACTION)) {
    return false;
  }
  if (task.owner_membership_id !== principal.membership_id) {
    return false;
  }
  return task.status === ReviewTaskStatus.OPEN || task.status === "open";
}

export function canRequestInformation(
  principal: Principal | null | undefined,
  task: ReviewTaskResponse | null | undefined
): boolean {
  if (!principal || !task || isTerminalTask(task)) return false;
  if (
    principal.role !== Role.ACCOUNTANT &&
    principal.role !== Role.SENIOR_REVIEWER
  ) {
    return false;
  }
  if (!principal.permissions.includes(Permission.REQUEST_INFORMATION)) {
    return false;
  }
  if (task.owner_membership_id !== principal.membership_id) {
    return false;
  }
  return (
    task.status === ReviewTaskStatus.OPEN ||
    task.status === "open" ||
    task.status === ReviewTaskStatus.ESCALATED ||
    task.status === "escalated"
  );
}

export function canReject(
  principal: Principal | null | undefined,
  task: ReviewTaskResponse | null | undefined
): boolean {
  if (!principal || !task || isTerminalTask(task)) return false;
  if (
    principal.role !== Role.ACCOUNTANT &&
    principal.role !== Role.SENIOR_REVIEWER
  ) {
    return false;
  }
  if (!principal.permissions.includes(Permission.REJECT_TRANSACTION)) {
    return false;
  }
  if (task.owner_membership_id !== principal.membership_id) {
    return false;
  }
  // The backend allows rejection from open, escalated, or information_requested
  return (
    task.status === ReviewTaskStatus.OPEN ||
    task.status === "open" ||
    task.status === ReviewTaskStatus.ESCALATED ||
    task.status === "escalated" ||
    task.status === ReviewTaskStatus.INFORMATION_REQUESTED ||
    task.status === "information_requested"
  );
}

export function canComment(
  principal: Principal | null | undefined,
  task: ReviewTaskResponse | null | undefined
): boolean {
  if (!principal || !task || isTerminalTask(task)) return false;
  if (
    principal.role !== Role.ACCOUNTANT &&
    principal.role !== Role.SENIOR_REVIEWER
  ) {
    return false;
  }
  if (!principal.permissions.includes(Permission.ADD_REVIEW_COMMENT)) {
    return false;
  }
  // Reviewer comments do NOT require ownership
  return (
    task.status === ReviewTaskStatus.OPEN ||
    task.status === "open" ||
    task.status === ReviewTaskStatus.ESCALATED ||
    task.status === "escalated" ||
    task.status === ReviewTaskStatus.INFORMATION_REQUESTED ||
    task.status === "information_requested"
  );
}

export function canCorrectField(
  principal: Principal | null | undefined,
  task: ReviewTaskResponse | null | undefined
): boolean {
  if (!principal || (task && isTerminalTask(task))) return false;
  if (
    principal.role !== Role.ACCOUNTANT &&
    principal.role !== Role.SENIOR_REVIEWER
  ) {
    return false;
  }
  return principal.permissions.includes(Permission.CORRECT_EXTRACTED_INFORMATION);
}

export function canRegenerateAccountingDecision(
  principal: Principal | null | undefined
): boolean {
  if (!principal) return false;
  if (
    principal.role !== Role.ACCOUNTANT &&
    principal.role !== Role.SENIOR_REVIEWER
  ) {
    return false;
  }
  return (
    principal.permissions.includes(Permission.RUN_ACCOUNTING_DECISION) &&
    principal.permissions.includes(Permission.CREATE_REVIEW_TASK)
  );
}
