import { SYNTHETIC_CLIENT_A_ID, SYNTHETIC_CLIENT_B_ID } from "./fixtures";
import {
  ReconciliationCandidateResponse,
  ReconciliationMatchResponse,
  ReconciliationMatchRunResponse,
  ReconciliationOutcomeResponse,
  ReconciliationReviewActionResponse,
  ReconciliationReviewHistoryResponse,
  ReconciliationReviewResponse,
  ReconciliationTerminalDecisionResponse,
  ReconciliationWorkflowState,
  ReconciliationWorklistItemResponse,
} from "@/types/reconciliation";

const ACCOUNTANT_USER_ID = "aaaa0001-aaaa-aaaa-aaaa-aaaaaaaaaaaa";
const ACCOUNTANT_MEMBERSHIP_ID = "bbbb0001-bbbb-bbbb-bbbb-bbbbbbbbbbbb";
const BASE_TIME = Date.parse("2026-08-30T12:00:00Z");

function stamp(offset: number): string {
  return new Date(BASE_TIME + offset * 60_000).toISOString();
}

function transaction(
  id: string,
  amount: string,
  bookingDate: string,
  reference: string,
  counterparty: string
) {
  return {
    id,
    import_batch_id: "mock-bank-batch-a",
    source_transaction_id: `mock-source-${id}`,
    booking_date: bookingDate,
    value_date: bookingDate,
    direction: "debit",
    amount,
    currency: "MYR",
    description: "Synthetic feature-test supplier settlement.",
    reference,
    counterparty_name: counterparty,
    created_at: stamp(1),
  };
}

function run(
  id: string,
  transactionId: string,
  status: "unmatched" | "candidates_available",
  offset: number
): ReconciliationMatchRunResponse {
  return {
    id,
    bank_transaction_id: transactionId,
    status,
    matcher_name: "deterministic_exact_bank_matcher",
    matcher_version: "1.0",
    created_at: stamp(offset),
  };
}

function candidate(
  id: string,
  matchRunId: string,
  transactionId: string,
  reviewOutcomeId: string,
  amount: string,
  reference: string,
  offset: number
): ReconciliationCandidateResponse {
  return {
    id,
    match_run_id: matchRunId,
    bank_transaction_id: transactionId,
    review_outcome_id: reviewOutcomeId,
    decision_run_id: `mock-decision-${reviewOutcomeId}`,
    document_id: `mock-document-${reviewOutcomeId}`,
    score: "1.0000",
    reasons: [
      "exact_amount",
      "exact_currency",
      "exact_direction",
      "same_date",
      "exact_reference",
      "exact_counterparty",
    ],
    target_transaction_date: "2026-08-11",
    target_direction: "debit",
    target_amount: amount,
    target_currency: "MYR",
    target_reference: reference,
    target_counterparty_name: "Synthetic Feature Test Supplier Sdn Bhd",
    created_at: stamp(offset),
  };
}

function review(
  id: string,
  transactionId: string,
  matchRunId: string,
  status: "open" | "disputed" | "matched" | "unmatched",
  selected: string | null,
  offset: number
): ReconciliationReviewResponse {
  return {
    id,
    bank_transaction_id: transactionId,
    match_run_id: matchRunId,
    created_by_user_id: ACCOUNTANT_USER_ID,
    created_by_membership_id: ACCOUNTANT_MEMBERSHIP_ID,
    status,
    selected_review_outcome_id: selected,
    request_id: `mock-request-${id}`,
    created_at: stamp(offset),
    updated_at: stamp(offset),
  };
}

function action(
  id: string,
  reviewValue: ReconciliationReviewResponse,
  actionType: string,
  offset: number,
  candidateOutcome: string | null = null,
  reason: string | null = null
): ReconciliationReviewActionResponse {
  return {
    id,
    reconciliation_review_id: reviewValue.id,
    bank_transaction_id: reviewValue.bank_transaction_id,
    match_run_id: reviewValue.match_run_id,
    actor_user_id: ACCOUNTANT_USER_ID,
    actor_membership_id: ACCOUNTANT_MEMBERSHIP_ID,
    action_type: actionType,
    candidate_review_outcome_id: candidateOutcome,
    reason,
    request_id: `mock-request-${id}`,
    created_at: stamp(offset),
  };
}

function outcome(
  id: string,
  reviewValue: ReconciliationReviewResponse,
  type: "matched" | "unmatched",
  offset: number,
  matchedReviewOutcomeId: string | null = null,
  reason: string | null = null
): ReconciliationOutcomeResponse {
  return {
    id,
    reconciliation_review_id: reviewValue.id,
    bank_transaction_id: reviewValue.bank_transaction_id,
    match_run_id: reviewValue.match_run_id,
    matched_review_outcome_id: matchedReviewOutcomeId,
    actor_user_id: ACCOUNTANT_USER_ID,
    actor_membership_id: ACCOUNTANT_MEMBERSHIP_ID,
    outcome_type: type,
    reason,
    request_id: `mock-request-${id}`,
    created_at: stamp(offset),
  };
}

function clone<T>(value: T): T {
  return structuredClone(value);
}

export class MockReconciliationStore {
  private items = new Map<string, ReconciliationWorklistItemResponse[]>();
  private candidatesByRun = new Map<string, ReconciliationCandidateResponse[]>();
  private histories = new Map<string, ReconciliationReviewHistoryResponse>();
  private sequence = 100;

  constructor() {
    this.reset();
  }

  reset(): void {
    this.sequence = 100;
    this.items.clear();
    this.candidatesByRun.clear();
    this.histories.clear();

    const candidateTx = transaction(
      "mock-tx-candidates",
      "100.0000",
      "2026-08-11",
      "SYN-FT-INV-001",
      "Synthetic Feature Test Supplier Sdn Bhd"
    );
    const candidateRun = run("mock-run-candidates", candidateTx.id, "candidates_available", 10);
    const candidateValue = candidate(
      "mock-candidate-candidates",
      candidateRun.id,
      candidateTx.id,
      "mock-review-outcome-001",
      "100.0000",
      "SYN-FT-INV-001",
      11
    );
    this.candidatesByRun.set(candidateRun.id, [candidateValue]);

    const reviewTx = transaction(
      "mock-tx-in-review",
      "100.0000",
      "2026-08-11",
      "SYN-FT-INV-001",
      "Synthetic Feature Test Supplier Sdn Bhd"
    );
    const reviewRun = run("mock-run-in-review", reviewTx.id, "candidates_available", 20);
    const reviewCandidate = candidate(
      "mock-candidate-in-review",
      reviewRun.id,
      reviewTx.id,
      "mock-review-outcome-002",
      "100.0000",
      "SYN-FT-INV-001",
      21
    );
    const openReview = review(
      "mock-review-open",
      reviewTx.id,
      reviewRun.id,
      "open",
      reviewCandidate.review_outcome_id,
      22
    );
    this.candidatesByRun.set(reviewRun.id, [reviewCandidate]);
    this.histories.set(openReview.id, {
      review: openReview,
      actions: [
        action(
          "mock-action-selected",
          openReview,
          "candidate_selected",
          23,
          reviewCandidate.review_outcome_id
        ),
      ],
      outcome: null,
    });

    const disputedTx = transaction(
      "mock-tx-disputed",
      "100.0000",
      "2026-08-11",
      "SYN-FT-INV-001",
      "Synthetic Feature Test Supplier Sdn Bhd"
    );
    const disputedRun = run("mock-run-disputed", disputedTx.id, "candidates_available", 30);
    const disputedCandidate = candidate(
      "mock-candidate-disputed",
      disputedRun.id,
      disputedTx.id,
      "mock-review-outcome-003",
      "100.0000",
      "SYN-FT-INV-001",
      31
    );
    const disputedReview = review(
      "mock-review-disputed",
      disputedTx.id,
      disputedRun.id,
      "disputed",
      disputedCandidate.review_outcome_id,
      32
    );
    this.candidatesByRun.set(disputedRun.id, [disputedCandidate]);
    this.histories.set(disputedReview.id, {
      review: disputedReview,
      actions: [
        action(
          "mock-action-disputed-selected",
          disputedReview,
          "candidate_selected",
          33,
          disputedCandidate.review_outcome_id
        ),
        action(
          "mock-action-disputed",
          disputedReview,
          "disputed",
          34,
          disputedCandidate.review_outcome_id,
          "Synthetic discrepancy requires human follow-up."
        ),
      ],
      outcome: null,
    });

    const matchedTx = transaction(
      "mock-tx-matched",
      "100.0000",
      "2026-08-11",
      "SYN-FT-INV-001",
      "Synthetic Feature Test Supplier Sdn Bhd"
    );
    const matchedRun = run("mock-run-matched", matchedTx.id, "candidates_available", 40);
    const matchedCandidate = candidate(
      "mock-candidate-matched",
      matchedRun.id,
      matchedTx.id,
      "mock-review-outcome-004",
      "100.0000",
      "SYN-FT-INV-001",
      41
    );
    const matchedReview = review(
      "mock-review-matched",
      matchedTx.id,
      matchedRun.id,
      "matched",
      matchedCandidate.review_outcome_id,
      42
    );
    const matchedOutcome = outcome(
      "mock-outcome-matched",
      matchedReview,
      "matched",
      44,
      matchedCandidate.review_outcome_id
    );
    this.candidatesByRun.set(matchedRun.id, [matchedCandidate]);
    this.histories.set(matchedReview.id, {
      review: matchedReview,
      actions: [
        action(
          "mock-action-matched-selected",
          matchedReview,
          "candidate_selected",
          43,
          matchedCandidate.review_outcome_id
        ),
        action(
          "mock-action-approved-match",
          matchedReview,
          "approved_match",
          44,
          matchedCandidate.review_outcome_id
        ),
      ],
      outcome: matchedOutcome,
    });

    const resolvedTx = transaction(
      "mock-tx-resolved-unmatched",
      "74.2500",
      "2026-08-17",
      "SYN-FT-NO-MATCH-002",
      "Synthetic No Match Supplier"
    );
    const resolvedRun = run("mock-run-resolved-unmatched", resolvedTx.id, "unmatched", 50);
    const resolvedReview = review(
      "mock-review-resolved-unmatched",
      resolvedTx.id,
      resolvedRun.id,
      "unmatched",
      null,
      51
    );
    const resolvedOutcome = outcome(
      "mock-outcome-resolved-unmatched",
      resolvedReview,
      "unmatched",
      52,
      null,
      "No approved accounting target corresponds to this synthetic bank transaction."
    );
    this.histories.set(resolvedReview.id, {
      review: resolvedReview,
      actions: [
        action(
          "mock-action-marked-unmatched",
          resolvedReview,
          "marked_unmatched",
          52,
          null,
          resolvedOutcome.reason
        ),
      ],
      outcome: resolvedOutcome,
    });

    const unmatchedTx = transaction(
      "mock-tx-unmatched",
      "73.2500",
      "2026-08-16",
      "SYN-FT-NO-MATCH-001",
      "Synthetic No Match Supplier"
    );
    const unmatchedRun = run("mock-run-unmatched", unmatchedTx.id, "unmatched", 5);

    const items: ReconciliationWorklistItemResponse[] = [
      {
        workflow_state: "not_evaluated",
        transaction: transaction(
          "mock-tx-not-evaluated",
          "100.0000",
          "2026-08-11",
          "SYN-FT-INV-001",
          "Synthetic Feature Test Supplier Sdn Bhd"
        ),
        latest_match_run: null,
        review_id: null,
        review_status: null,
        selected_review_outcome_id: null,
        outcome_id: null,
        outcome_type: null,
        matched_review_outcome_id: null,
        last_activity_at: stamp(1),
      },
      {
        workflow_state: "unmatched",
        transaction: unmatchedTx,
        latest_match_run: unmatchedRun,
        review_id: null,
        review_status: null,
        selected_review_outcome_id: null,
        outcome_id: null,
        outcome_type: null,
        matched_review_outcome_id: null,
        last_activity_at: unmatchedRun.created_at,
      },
      {
        workflow_state: "candidates_available",
        transaction: candidateTx,
        latest_match_run: candidateRun,
        review_id: null,
        review_status: null,
        selected_review_outcome_id: null,
        outcome_id: null,
        outcome_type: null,
        matched_review_outcome_id: null,
        last_activity_at: candidateRun.created_at,
      },
      {
        workflow_state: "in_review",
        transaction: reviewTx,
        latest_match_run: reviewRun,
        review_id: openReview.id,
        review_status: openReview.status,
        selected_review_outcome_id: openReview.selected_review_outcome_id,
        outcome_id: null,
        outcome_type: null,
        matched_review_outcome_id: null,
        last_activity_at: openReview.updated_at,
      },
      {
        workflow_state: "disputed",
        transaction: disputedTx,
        latest_match_run: disputedRun,
        review_id: disputedReview.id,
        review_status: disputedReview.status,
        selected_review_outcome_id: disputedReview.selected_review_outcome_id,
        outcome_id: null,
        outcome_type: null,
        matched_review_outcome_id: null,
        last_activity_at: disputedReview.updated_at,
      },
      {
        workflow_state: "matched",
        transaction: matchedTx,
        latest_match_run: matchedRun,
        review_id: matchedReview.id,
        review_status: matchedReview.status,
        selected_review_outcome_id: matchedReview.selected_review_outcome_id,
        outcome_id: matchedOutcome.id,
        outcome_type: matchedOutcome.outcome_type,
        matched_review_outcome_id: matchedOutcome.matched_review_outcome_id,
        last_activity_at: matchedOutcome.created_at,
      },
      {
        workflow_state: "resolved_unmatched",
        transaction: resolvedTx,
        latest_match_run: resolvedRun,
        review_id: resolvedReview.id,
        review_status: resolvedReview.status,
        selected_review_outcome_id: null,
        outcome_id: resolvedOutcome.id,
        outcome_type: resolvedOutcome.outcome_type,
        matched_review_outcome_id: null,
        last_activity_at: resolvedOutcome.created_at,
      },
    ];
    this.items.set(SYNTHETIC_CLIENT_A_ID, items);
    this.items.set(SYNTHETIC_CLIENT_B_ID, [
      {
        workflow_state: "not_evaluated",
        transaction: transaction(
          "mock-tx-client-b",
          "240.0000",
          "2026-08-11",
          "SYN-FT-BETA-001",
          "Synthetic Beta Supplier"
        ),
        latest_match_run: null,
        review_id: null,
        review_status: null,
        selected_review_outcome_id: null,
        outcome_id: null,
        outcome_type: null,
        matched_review_outcome_id: null,
        last_activity_at: stamp(1),
      },
    ]);
  }

  listWorklist(
    clientId: string,
    state?: ReconciliationWorkflowState
  ): ReconciliationWorklistItemResponse[] {
    const values = this.items.get(clientId) ?? [];
    return clone(state ? values.filter((item) => item.workflow_state === state) : values);
  }

  listCandidates(matchRunId: string): ReconciliationCandidateResponse[] {
    return clone(this.candidatesByRun.get(matchRunId) ?? []);
  }

  history(reviewId: string): ReconciliationReviewHistoryResponse | null {
    const value = this.histories.get(reviewId);
    return value ? clone(value) : null;
  }

  generateMatch(clientId: string, transactionId: string): ReconciliationMatchResponse {
    const item = this.requireItem(clientId, transactionId);
    if (item.review_id || item.outcome_id) {
      throw new Error("Mock reconciliation transaction is already under human review.");
    }
    const hasCandidate = item.transaction.amount === "100.0000";
    const matchRun = run(
      this.nextId("run"),
      transactionId,
      hasCandidate ? "candidates_available" : "unmatched",
      this.sequence
    );
    const candidates = hasCandidate
      ? [
          candidate(
            this.nextId("candidate"),
            matchRun.id,
            transactionId,
            "mock-review-outcome-generated",
            item.transaction.amount,
            item.transaction.reference ?? "SYN-FT-INV-001",
            this.sequence
          ),
        ]
      : [];
    this.candidatesByRun.set(matchRun.id, candidates);
    item.latest_match_run = matchRun;
    item.workflow_state = hasCandidate ? "candidates_available" : "unmatched";
    item.last_activity_at = matchRun.created_at;
    return clone({ run: matchRun, candidates });
  }

  createReview(clientId: string, transactionId: string): ReconciliationReviewResponse {
    const item = this.requireItem(clientId, transactionId);
    if (!item.latest_match_run || item.review_id) {
      throw new Error("Mock reconciliation review requires a current match run.");
    }
    const reviewValue = review(
      this.nextId("review"),
      transactionId,
      item.latest_match_run.id,
      "open",
      null,
      this.sequence
    );
    this.histories.set(reviewValue.id, { review: reviewValue, actions: [], outcome: null });
    item.review_id = reviewValue.id;
    item.review_status = "open";
    item.workflow_state = "in_review";
    item.last_activity_at = reviewValue.updated_at;
    return clone(reviewValue);
  }

  selectCandidate(
    clientId: string,
    transactionId: string,
    reviewId: string,
    reviewOutcomeId: string
  ): ReconciliationReviewResponse {
    const item = this.requireReviewItem(clientId, transactionId, reviewId);
    const history = this.requireHistory(reviewId);
    if (history.review.status !== "open") {
      throw new Error("Mock candidate selection requires an open review.");
    }
    const candidates = this.candidatesByRun.get(history.review.match_run_id) ?? [];
    if (!candidates.some((entry) => entry.review_outcome_id === reviewOutcomeId)) {
      throw new Error("Mock candidate does not belong to the review match run.");
    }
    history.review.selected_review_outcome_id = reviewOutcomeId;
    history.review.updated_at = this.nextStamp();
    history.actions.push(
      action(
        this.nextId("action"),
        history.review,
        "candidate_selected",
        this.sequence,
        reviewOutcomeId
      )
    );
    item.selected_review_outcome_id = reviewOutcomeId;
    item.last_activity_at = history.review.updated_at;
    return clone(history.review);
  }

  dispute(
    clientId: string,
    transactionId: string,
    reviewId: string,
    reason: string
  ): ReconciliationReviewResponse {
    const item = this.requireReviewItem(clientId, transactionId, reviewId);
    const history = this.requireHistory(reviewId);
    if (!reason.trim() || history.review.status !== "open") {
      throw new Error("Mock dispute requires an open review and a reason.");
    }
    history.review.status = "disputed";
    history.review.updated_at = this.nextStamp();
    history.actions.push(
      action(
        this.nextId("action"),
        history.review,
        "disputed",
        this.sequence,
        history.review.selected_review_outcome_id,
        reason.trim()
      )
    );
    item.review_status = "disputed";
    item.workflow_state = "disputed";
    item.last_activity_at = history.review.updated_at;
    return clone(history.review);
  }

  reopen(
    clientId: string,
    transactionId: string,
    reviewId: string,
    reason: string
  ): ReconciliationReviewResponse {
    const item = this.requireReviewItem(clientId, transactionId, reviewId);
    const history = this.requireHistory(reviewId);
    if (!reason.trim() || history.review.status !== "disputed") {
      throw new Error("Mock reopen requires a disputed review and a reason.");
    }
    history.review.status = "open";
    history.review.updated_at = this.nextStamp();
    history.actions.push(
      action(
        this.nextId("action"),
        history.review,
        "reopened",
        this.sequence,
        history.review.selected_review_outcome_id,
        reason.trim()
      )
    );
    item.review_status = "open";
    item.workflow_state = "in_review";
    item.last_activity_at = history.review.updated_at;
    return clone(history.review);
  }

  approve(
    clientId: string,
    transactionId: string,
    reviewId: string,
    note: string | null
  ): ReconciliationTerminalDecisionResponse {
    const item = this.requireReviewItem(clientId, transactionId, reviewId);
    const history = this.requireHistory(reviewId);
    if (history.review.status !== "open" || !history.review.selected_review_outcome_id) {
      throw new Error("Mock match approval requires an open review with a selected candidate.");
    }
    history.review.status = "matched";
    history.review.updated_at = this.nextStamp();
    const terminalOutcome = outcome(
      this.nextId("outcome"),
      history.review,
      "matched",
      this.sequence,
      history.review.selected_review_outcome_id,
      note?.trim() || null
    );
    history.actions.push(
      action(
        this.nextId("action"),
        history.review,
        "approved_match",
        this.sequence,
        history.review.selected_review_outcome_id,
        note?.trim() || null
      )
    );
    history.outcome = terminalOutcome;
    item.review_status = "matched";
    item.workflow_state = "matched";
    item.outcome_id = terminalOutcome.id;
    item.outcome_type = "matched";
    item.matched_review_outcome_id = terminalOutcome.matched_review_outcome_id;
    item.last_activity_at = terminalOutcome.created_at;
    return clone({ review: history.review, outcome: terminalOutcome });
  }

  markUnmatched(
    clientId: string,
    transactionId: string,
    reviewId: string,
    reason: string
  ): ReconciliationTerminalDecisionResponse {
    const item = this.requireReviewItem(clientId, transactionId, reviewId);
    const history = this.requireHistory(reviewId);
    if (history.review.status !== "open" || !reason.trim()) {
      throw new Error("Mock unmatched decision requires an open review and a reason.");
    }
    history.review.status = "unmatched";
    history.review.updated_at = this.nextStamp();
    const terminalOutcome = outcome(
      this.nextId("outcome"),
      history.review,
      "unmatched",
      this.sequence,
      null,
      reason.trim()
    );
    history.actions.push(
      action(
        this.nextId("action"),
        history.review,
        "marked_unmatched",
        this.sequence,
        null,
        reason.trim()
      )
    );
    history.outcome = terminalOutcome;
    item.review_status = "unmatched";
    item.workflow_state = "resolved_unmatched";
    item.outcome_id = terminalOutcome.id;
    item.outcome_type = "unmatched";
    item.matched_review_outcome_id = null;
    item.last_activity_at = terminalOutcome.created_at;
    return clone({ review: history.review, outcome: terminalOutcome });
  }

  private requireItem(clientId: string, transactionId: string): ReconciliationWorklistItemResponse {
    const item = (this.items.get(clientId) ?? []).find(
      (entry) => entry.transaction.id === transactionId
    );
    if (!item) throw new Error("Mock reconciliation transaction not found.");
    return item;
  }

  private requireReviewItem(
    clientId: string,
    transactionId: string,
    reviewId: string
  ): ReconciliationWorklistItemResponse {
    const item = this.requireItem(clientId, transactionId);
    if (item.review_id !== reviewId) throw new Error("Mock reconciliation review not found.");
    return item;
  }

  private requireHistory(reviewId: string): ReconciliationReviewHistoryResponse {
    const history = this.histories.get(reviewId);
    if (!history) throw new Error("Mock reconciliation history not found.");
    return history;
  }

  private nextId(kind: string): string {
    this.sequence += 1;
    return `mock-${kind}-${this.sequence}`;
  }

  private nextStamp(): string {
    this.sequence += 1;
    return stamp(this.sequence);
  }
}

export const mockReconciliationStore = new MockReconciliationStore();
