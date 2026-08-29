import { ApiClient, defaultApiClient, RequestOptions } from "./client";
import {
  ReviewCommentResponse,
  ReviewHistoryResponse,
  ReviewInteractionResponse,
  ReviewResolutionResponse,
  ReviewTaskLineage,
  ReviewTaskResponse,
} from "@/types/api";

function buildBasePath(lineage: Omit<ReviewTaskLineage, "reviewTaskId">): string {
  return `/clients/${lineage.clientId}/documents/${lineage.documentId}/extractions/${lineage.extractionRunId}/accounting-decisions/${lineage.decisionRunId}/review-tasks`;
}

function buildTaskPath(lineage: ReviewTaskLineage): string {
  return `${buildBasePath(lineage)}/${lineage.reviewTaskId}`;
}

export async function createReviewTask(
  lineage: Omit<ReviewTaskLineage, "reviewTaskId">,
  ownerMembershipId?: string,
  client: ApiClient = defaultApiClient,
  options?: RequestOptions
): Promise<ReviewTaskResponse> {
  return client.post<ReviewTaskResponse>(
    buildBasePath(lineage),
    { owner_membership_id: ownerMembershipId },
    options
  );
}

export async function listReviewTasks(
  lineage: Omit<ReviewTaskLineage, "reviewTaskId">,
  client: ApiClient = defaultApiClient,
  options?: RequestOptions
): Promise<ReviewTaskResponse[]> {
  return client.get<ReviewTaskResponse[]>(buildBasePath(lineage), options);
}

export async function fetchReviewTask(
  lineage: ReviewTaskLineage,
  client: ApiClient = defaultApiClient,
  options?: RequestOptions
): Promise<ReviewTaskResponse> {
  return client.get<ReviewTaskResponse>(buildTaskPath(lineage), options);
}

export async function escalateReviewTask(
  lineage: ReviewTaskLineage,
  seniorMembershipId: string,
  reason: string,
  client: ApiClient = defaultApiClient,
  options?: RequestOptions
): Promise<ReviewTaskResponse> {
  return client.post<ReviewTaskResponse>(
    `${buildTaskPath(lineage)}/escalations`,
    {
      senior_membership_id: seniorMembershipId,
      reason,
    },
    options
  );
}

export async function addReviewComment(
  lineage: ReviewTaskLineage,
  body: string,
  client: ApiClient = defaultApiClient,
  options?: RequestOptions
): Promise<ReviewCommentResponse> {
  return client.post<ReviewCommentResponse>(
    `${buildTaskPath(lineage)}/comments`,
    { body },
    options
  );
}

export async function requestInformation(
  lineage: ReviewTaskLineage,
  body: string,
  client: ApiClient = defaultApiClient,
  options?: RequestOptions
): Promise<ReviewInteractionResponse> {
  return client.post<ReviewInteractionResponse>(
    `${buildTaskPath(lineage)}/information-requests`,
    { body },
    options
  );
}

export async function getOutstandingInformationRequest(
  lineage: ReviewTaskLineage,
  client: ApiClient = defaultApiClient,
  options?: RequestOptions
): Promise<ReviewCommentResponse> {
  return client.get<ReviewCommentResponse>(
    `${buildTaskPath(lineage)}/information-request`,
    options
  );
}

export async function respondToInformationRequest(
  lineage: ReviewTaskLineage,
  body: string,
  client: ApiClient = defaultApiClient,
  options?: RequestOptions
): Promise<ReviewInteractionResponse> {
  return client.post<ReviewInteractionResponse>(
    `${buildTaskPath(lineage)}/information-responses`,
    { body },
    options
  );
}

export async function approveReviewTask(
  lineage: ReviewTaskLineage,
  note?: string | null,
  client: ApiClient = defaultApiClient,
  options?: RequestOptions
): Promise<ReviewResolutionResponse> {
  return client.post<ReviewResolutionResponse>(
    `${buildTaskPath(lineage)}/approve`,
    { note },
    options
  );
}

export async function rejectReviewTask(
  lineage: ReviewTaskLineage,
  reason: string,
  client: ApiClient = defaultApiClient,
  options?: RequestOptions
): Promise<ReviewResolutionResponse> {
  return client.post<ReviewResolutionResponse>(
    `${buildTaskPath(lineage)}/reject`,
    { reason },
    options
  );
}

export async function fetchReviewHistory(
  lineage: ReviewTaskLineage,
  client: ApiClient = defaultApiClient,
  options?: RequestOptions
): Promise<ReviewHistoryResponse> {
  return client.get<ReviewHistoryResponse>(
    `${buildTaskPath(lineage)}/history`,
    options
  );
}
