import { OperatingMode } from "@/lib/context/AuthContext";
import { Permission, Principal, Role } from "@/types/roles";
import { ReconciliationWorklistItemResponse } from "@/types/reconciliation";

const REVIEWER_MOCK_PERMISSIONS = [
  Permission.IMPORT_BANK_TRANSACTIONS,
  Permission.VIEW_BANK_TRANSACTIONS,
  Permission.RUN_RECONCILIATION_MATCHING,
  Permission.VIEW_RECONCILIATION_MATCHES,
  Permission.CREATE_RECONCILIATION_REVIEW,
  Permission.REVIEW_RECONCILIATION,
  Permission.APPROVE_RECONCILIATION,
  Permission.VIEW_RECONCILIATION_HISTORY,
] as const;

const AUDITOR_MOCK_PERMISSIONS = [
  Permission.VIEW_BANK_TRANSACTIONS,
  Permission.VIEW_RECONCILIATION_MATCHES,
  Permission.VIEW_RECONCILIATION_HISTORY,
] as const;

export function reconciliationPrincipalForMode(
  principal: Principal | null | undefined,
  mode: OperatingMode
): Principal | null {
  if (!principal) return null;
  if (mode === "live") return principal;

  let additions: readonly Permission[] = [];
  if (principal.role === Role.ACCOUNTANT || principal.role === Role.SENIOR_REVIEWER) {
    additions = REVIEWER_MOCK_PERMISSIONS;
  } else if (principal.role === Role.AUDITOR) {
    additions = AUDITOR_MOCK_PERMISSIONS;
  }

  return {
    ...principal,
    permissions: Array.from(new Set([...principal.permissions, ...additions])),
  };
}

export function canViewReconciliationWorkspace(
  principal: Principal | null | undefined
): boolean {
  return Boolean(
    principal?.permissions.includes(Permission.VIEW_RECONCILIATION_HISTORY) &&
      principal.permissions.includes(Permission.VIEW_BANK_TRANSACTIONS)
  );
}

export function isReconciliationTerminal(
  item: ReconciliationWorklistItemResponse | null | undefined
): boolean {
  return Boolean(
    item &&
      (item.workflow_state === "matched" || item.workflow_state === "resolved_unmatched")
  );
}

function hasPermission(
  principal: Principal | null | undefined,
  permission: Permission
): boolean {
  return Boolean(principal?.permissions.includes(permission));
}

export function canGenerateCandidates(
  principal: Principal | null | undefined,
  item: ReconciliationWorklistItemResponse | null | undefined
): boolean {
  if (!principal || !item || isReconciliationTerminal(item) || item.review_id) return false;
  return hasPermission(principal, Permission.RUN_RECONCILIATION_MATCHING);
}

export function canStartReconciliationReview(
  principal: Principal | null | undefined,
  item: ReconciliationWorklistItemResponse | null | undefined
): boolean {
  if (!principal || !item || isReconciliationTerminal(item) || item.review_id) return false;
  if (!item.latest_match_run) return false;
  return hasPermission(principal, Permission.CREATE_RECONCILIATION_REVIEW);
}

export function canSelectReconciliationCandidate(
  principal: Principal | null | undefined,
  item: ReconciliationWorklistItemResponse | null | undefined
): boolean {
  if (!principal || !item || isReconciliationTerminal(item)) return false;
  return (
    item.review_status === "open" &&
    hasPermission(principal, Permission.REVIEW_RECONCILIATION)
  );
}

export function canDisputeReconciliation(
  principal: Principal | null | undefined,
  item: ReconciliationWorklistItemResponse | null | undefined
): boolean {
  return canSelectReconciliationCandidate(principal, item);
}

export function canReopenReconciliation(
  principal: Principal | null | undefined,
  item: ReconciliationWorklistItemResponse | null | undefined
): boolean {
  if (!principal || !item || isReconciliationTerminal(item)) return false;
  return (
    item.review_status === "disputed" &&
    hasPermission(principal, Permission.REVIEW_RECONCILIATION)
  );
}

export function canApproveReconciliation(
  principal: Principal | null | undefined,
  item: ReconciliationWorklistItemResponse | null | undefined
): boolean {
  if (!principal || !item || isReconciliationTerminal(item)) return false;
  return (
    item.review_status === "open" &&
    item.selected_review_outcome_id !== null &&
    hasPermission(principal, Permission.APPROVE_RECONCILIATION)
  );
}

export function canMarkReconciliationUnmatched(
  principal: Principal | null | undefined,
  item: ReconciliationWorklistItemResponse | null | undefined
): boolean {
  if (!principal || !item || isReconciliationTerminal(item)) return false;
  return (
    item.review_status === "open" &&
    hasPermission(principal, Permission.APPROVE_RECONCILIATION)
  );
}
