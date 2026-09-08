import { ApiClient, defaultApiClient } from "./client";
import {
  ReconciliationCandidateResponse,
  ReconciliationMatchResponse,
  ReconciliationRequestContext,
  ReconciliationReviewHistoryResponse,
  ReconciliationReviewResponse,
  ReconciliationTerminalDecisionResponse,
  ReconciliationWorkflowState,
  ReconciliationWorklistItemResponse,
} from "@/types/reconciliation";

function authOptions(context: ReconciliationRequestContext) {
  return {
    devSubject: context.devSubject,
    firmId: context.firmId,
  };
}

function root(clientId: string): string {
  return `/clients/${encodeURIComponent(clientId)}/bank-reconciliation`;
}

function transactionRoot(clientId: string, transactionId: string): string {
  return `${root(clientId)}/transactions/${encodeURIComponent(transactionId)}`;
}

function reviewRoot(clientId: string, transactionId: string, reviewId: string): string {
  return `${transactionRoot(clientId, transactionId)}/reviews/${encodeURIComponent(reviewId)}`;
}

export function listReconciliationWorklist(
  clientId: string,
  context: ReconciliationRequestContext,
  state?: ReconciliationWorkflowState,
  client: ApiClient = defaultApiClient
): Promise<ReconciliationWorklistItemResponse[]> {
  return client.get(root(clientId) + "/worklist", {
    ...authOptions(context),
    searchParams: state ? { state } : undefined,
  });
}

export function generateReconciliationMatch(
  clientId: string,
  transactionId: string,
  context: ReconciliationRequestContext,
  client: ApiClient = defaultApiClient
): Promise<ReconciliationMatchResponse> {
  return client.post(
    transactionRoot(clientId, transactionId) + "/match-runs",
    {},
    authOptions(context)
  );
}

export function listReconciliationCandidates(
  clientId: string,
  transactionId: string,
  matchRunId: string,
  context: ReconciliationRequestContext,
  client: ApiClient = defaultApiClient
): Promise<ReconciliationCandidateResponse[]> {
  return client.get(
    `${transactionRoot(clientId, transactionId)}/match-runs/${encodeURIComponent(matchRunId)}/candidates`,
    authOptions(context)
  );
}

export function createReconciliationReview(
  clientId: string,
  transactionId: string,
  matchRunId: string,
  context: ReconciliationRequestContext,
  client: ApiClient = defaultApiClient
): Promise<ReconciliationReviewResponse> {
  return client.post(
    transactionRoot(clientId, transactionId) + "/reviews",
    { match_run_id: matchRunId },
    authOptions(context)
  );
}

export function selectReconciliationCandidate(
  clientId: string,
  transactionId: string,
  reviewId: string,
  reviewOutcomeId: string,
  context: ReconciliationRequestContext,
  client: ApiClient = defaultApiClient
): Promise<ReconciliationReviewResponse> {
  return client.post(
    reviewRoot(clientId, transactionId, reviewId) + "/candidate-selection",
    { review_outcome_id: reviewOutcomeId },
    authOptions(context)
  );
}

export function disputeReconciliationReview(
  clientId: string,
  transactionId: string,
  reviewId: string,
  reason: string,
  context: ReconciliationRequestContext,
  client: ApiClient = defaultApiClient
): Promise<ReconciliationReviewResponse> {
  return client.post(
    reviewRoot(clientId, transactionId, reviewId) + "/dispute",
    { reason },
    authOptions(context)
  );
}

export function reopenReconciliationReview(
  clientId: string,
  transactionId: string,
  reviewId: string,
  reason: string,
  context: ReconciliationRequestContext,
  client: ApiClient = defaultApiClient
): Promise<ReconciliationReviewResponse> {
  return client.post(
    reviewRoot(clientId, transactionId, reviewId) + "/reopen",
    { reason },
    authOptions(context)
  );
}

export function approveReconciliationMatch(
  clientId: string,
  transactionId: string,
  reviewId: string,
  note: string | null,
  context: ReconciliationRequestContext,
  client: ApiClient = defaultApiClient
): Promise<ReconciliationTerminalDecisionResponse> {
  return client.post(
    reviewRoot(clientId, transactionId, reviewId) + "/approve",
    { note },
    authOptions(context)
  );
}

export function markReconciliationUnmatched(
  clientId: string,
  transactionId: string,
  reviewId: string,
  reason: string,
  context: ReconciliationRequestContext,
  client: ApiClient = defaultApiClient
): Promise<ReconciliationTerminalDecisionResponse> {
  return client.post(
    reviewRoot(clientId, transactionId, reviewId) + "/mark-unmatched",
    { reason },
    authOptions(context)
  );
}

export function getReconciliationHistory(
  clientId: string,
  transactionId: string,
  reviewId: string,
  context: ReconciliationRequestContext,
  client: ApiClient = defaultApiClient
): Promise<ReconciliationReviewHistoryResponse> {
  return client.get(
    reviewRoot(clientId, transactionId, reviewId) + "/history",
    authOptions(context)
  );
}
