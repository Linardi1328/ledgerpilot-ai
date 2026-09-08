export type ReconciliationWorkflowState =
  | "not_evaluated"
  | "unmatched"
  | "candidates_available"
  | "in_review"
  | "disputed"
  | "matched"
  | "resolved_unmatched";

export type ReconciliationReviewStatus = "open" | "disputed" | "matched" | "unmatched";
export type ReconciliationOutcomeType = "matched" | "unmatched";
export type ReconciliationMatchStatus = "unmatched" | "candidates_available";

export interface BankTransactionResponse {
  id: string;
  import_batch_id: string;
  source_transaction_id: string;
  booking_date: string;
  value_date: string | null;
  direction: string;
  amount: string;
  currency: string;
  description: string;
  reference: string | null;
  counterparty_name: string | null;
  created_at: string;
}

export interface ReconciliationMatchRunResponse {
  id: string;
  bank_transaction_id: string;
  status: ReconciliationMatchStatus | string;
  matcher_name: string;
  matcher_version: string;
  created_at: string;
}

export interface ReconciliationCandidateResponse {
  id: string;
  match_run_id: string;
  bank_transaction_id: string;
  review_outcome_id: string;
  decision_run_id: string;
  document_id: string;
  score: string;
  reasons: string[];
  target_transaction_date: string;
  target_direction: string;
  target_amount: string;
  target_currency: string;
  target_reference: string | null;
  target_counterparty_name: string | null;
  created_at: string;
}

export interface ReconciliationMatchResponse {
  run: ReconciliationMatchRunResponse;
  candidates: ReconciliationCandidateResponse[];
}

export interface ReconciliationWorklistItemResponse {
  workflow_state: ReconciliationWorkflowState;
  transaction: BankTransactionResponse;
  latest_match_run: ReconciliationMatchRunResponse | null;
  review_id: string | null;
  review_status: ReconciliationReviewStatus | string | null;
  selected_review_outcome_id: string | null;
  outcome_id: string | null;
  outcome_type: ReconciliationOutcomeType | string | null;
  matched_review_outcome_id: string | null;
  last_activity_at: string;
}

export interface ReconciliationReviewResponse {
  id: string;
  bank_transaction_id: string;
  match_run_id: string;
  created_by_user_id: string;
  created_by_membership_id: string;
  status: ReconciliationReviewStatus | string;
  selected_review_outcome_id: string | null;
  request_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface ReconciliationReviewActionResponse {
  id: string;
  reconciliation_review_id: string;
  bank_transaction_id: string;
  match_run_id: string;
  actor_user_id: string;
  actor_membership_id: string;
  action_type: string;
  candidate_review_outcome_id: string | null;
  reason: string | null;
  request_id: string | null;
  created_at: string;
}

export interface ReconciliationOutcomeResponse {
  id: string;
  reconciliation_review_id: string;
  bank_transaction_id: string;
  match_run_id: string;
  matched_review_outcome_id: string | null;
  actor_user_id: string;
  actor_membership_id: string;
  outcome_type: ReconciliationOutcomeType | string;
  reason: string | null;
  request_id: string | null;
  created_at: string;
}

export interface ReconciliationTerminalDecisionResponse {
  review: ReconciliationReviewResponse;
  outcome: ReconciliationOutcomeResponse;
}

export interface ReconciliationReviewHistoryResponse {
  review: ReconciliationReviewResponse;
  actions: ReconciliationReviewActionResponse[];
  outcome: ReconciliationOutcomeResponse | null;
}

export interface ReconciliationRequestContext {
  devSubject: string;
  firmId: string;
}
