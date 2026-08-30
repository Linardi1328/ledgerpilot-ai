import { describe, expect, it } from "vitest";
import {
  canApproveReconciliation,
  canDisputeReconciliation,
  canGenerateCandidates,
  canMarkReconciliationUnmatched,
  canReopenReconciliation,
  canSelectReconciliationCandidate,
  canStartReconciliationReview,
  canViewReconciliationWorkspace,
  isReconciliationTerminal,
  reconciliationPrincipalForMode,
} from "@/lib/policy/reconciliation-policy";
import { Permission, Principal, Role } from "@/types/roles";
import { ReconciliationWorklistItemResponse } from "@/types/reconciliation";

const basePrincipal: Principal = {
  user_id: "user-1",
  firm_id: "firm-1",
  membership_id: "member-1",
  role: Role.ACCOUNTANT,
  permissions: [],
  authorized_client_ids: ["client-1"],
};

const baseItem: ReconciliationWorklistItemResponse = {
  workflow_state: "not_evaluated",
  transaction: {
    id: "tx-1",
    import_batch_id: "batch-1",
    source_transaction_id: "source-1",
    booking_date: "2026-08-11",
    value_date: "2026-08-11",
    direction: "debit",
    amount: "100.0000",
    currency: "MYR",
    description: "Synthetic",
    reference: "SYN-001",
    counterparty_name: "Synthetic Supplier",
    created_at: "2026-08-30T12:00:00Z",
  },
  latest_match_run: null,
  review_id: null,
  review_status: null,
  selected_review_outcome_id: null,
  outcome_id: null,
  outcome_type: null,
  matched_review_outcome_id: null,
  last_activity_at: "2026-08-30T12:00:00Z",
};

describe("reconciliation policy", () => {
  it("adds mock reviewer permissions without changing live authority", () => {
    const mock = reconciliationPrincipalForMode(basePrincipal, "mock");
    expect(mock?.permissions).toContain(Permission.RUN_RECONCILIATION_MATCHING);
    expect(mock?.permissions).toContain(Permission.APPROVE_RECONCILIATION);

    const live = reconciliationPrincipalForMode(basePrincipal, "live");
    expect(live).toBe(basePrincipal);
    expect(live?.permissions).toEqual([]);
  });

  it("makes Auditor mock reconciliation access read-only", () => {
    const auditor = reconciliationPrincipalForMode(
      { ...basePrincipal, role: Role.AUDITOR },
      "mock"
    );
    expect(canViewReconciliationWorkspace(auditor)).toBe(true);
    expect(auditor?.permissions).toContain(Permission.VIEW_RECONCILIATION_HISTORY);
    expect(auditor?.permissions).not.toContain(Permission.APPROVE_RECONCILIATION);
    expect(canGenerateCandidates(auditor, baseItem)).toBe(false);
  });

  it("keeps submitters and admins outside reconciliation workspace", () => {
    const submitter = reconciliationPrincipalForMode(
      { ...basePrincipal, role: Role.CLIENT_SUBMITTER },
      "mock"
    );
    const admin = reconciliationPrincipalForMode(
      { ...basePrincipal, role: Role.FIRM_ADMIN },
      "mock"
    );
    expect(canViewReconciliationWorkspace(submitter)).toBe(false);
    expect(canViewReconciliationWorkspace(admin)).toBe(false);
    expect(reconciliationPrincipalForMode(null, "mock")).toBeNull();
  });

  it("allows candidate generation before human review", () => {
    const reviewer = reconciliationPrincipalForMode(basePrincipal, "mock");
    expect(canGenerateCandidates(reviewer, baseItem)).toBe(true);
    expect(canStartReconciliationReview(reviewer, baseItem)).toBe(false);

    const withRun: ReconciliationWorklistItemResponse = {
      ...baseItem,
      workflow_state: "candidates_available",
      latest_match_run: {
        id: "run-1",
        bank_transaction_id: baseItem.transaction.id,
        status: "candidates_available",
        matcher_name: "matcher",
        matcher_version: "1",
        created_at: baseItem.last_activity_at,
      },
    };
    expect(canStartReconciliationReview(reviewer, withRun)).toBe(true);
  });

  it("gates human actions by review state and selected candidate", () => {
    const reviewer = reconciliationPrincipalForMode(basePrincipal, "mock");
    const open: ReconciliationWorklistItemResponse = {
      ...baseItem,
      workflow_state: "in_review",
      review_id: "review-1",
      review_status: "open",
    };
    expect(canSelectReconciliationCandidate(reviewer, open)).toBe(true);
    expect(canDisputeReconciliation(reviewer, open)).toBe(true);
    expect(canMarkReconciliationUnmatched(reviewer, open)).toBe(true);
    expect(canApproveReconciliation(reviewer, open)).toBe(false);

    const selected = { ...open, selected_review_outcome_id: "outcome-1" };
    expect(canApproveReconciliation(reviewer, selected)).toBe(true);

    const disputed = { ...selected, workflow_state: "disputed" as const, review_status: "disputed" };
    expect(canReopenReconciliation(reviewer, disputed)).toBe(true);
    expect(canApproveReconciliation(reviewer, disputed)).toBe(false);
  });

  it("suppresses all mutation controls for terminal states", () => {
    const reviewer = reconciliationPrincipalForMode(basePrincipal, "mock");
    for (const state of ["matched", "resolved_unmatched"] as const) {
      const terminal: ReconciliationWorklistItemResponse = {
        ...baseItem,
        workflow_state: state,
        review_id: "review-terminal",
        review_status: state === "matched" ? "matched" : "unmatched",
      };
      expect(isReconciliationTerminal(terminal)).toBe(true);
      expect(canGenerateCandidates(reviewer, terminal)).toBe(false);
      expect(canStartReconciliationReview(reviewer, terminal)).toBe(false);
      expect(canSelectReconciliationCandidate(reviewer, terminal)).toBe(false);
      expect(canDisputeReconciliation(reviewer, terminal)).toBe(false);
      expect(canReopenReconciliation(reviewer, terminal)).toBe(false);
      expect(canApproveReconciliation(reviewer, terminal)).toBe(false);
      expect(canMarkReconciliationUnmatched(reviewer, terminal)).toBe(false);
    }
  });
});
