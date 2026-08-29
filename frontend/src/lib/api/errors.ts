import { ApiErrorResponse } from "@/types/api";

export class ApiError extends Error {
  public readonly code: string;
  public readonly status: number;
  public readonly requestId?: string | null;

  constructor(status: number, code: string, message: string, requestId?: string | null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.requestId = requestId;
  }

  static fromResponse(status: number, payload: unknown, defaultMessage = "Request failed"): ApiError {
    if (payload && typeof payload === "object" && "error" in payload) {
      const errorObj = (payload as ApiErrorResponse).error;
      return new ApiError(
        status,
        errorObj.code || "unknown_error",
        errorObj.message || defaultMessage,
        errorObj.request_id
      );
    }
    return new ApiError(status, "http_error", defaultMessage);
  }
}

/**
 * Returns a human-friendly, actionable description for known Phase 5 API error codes.
 */
export function getFriendlyErrorMessage(error: unknown): string {
  if (!(error instanceof ApiError)) {
    return error instanceof Error ? error.message : "An unexpected error occurred.";
  }

  switch (error.code) {
    case "unauthenticated":
      return "Authentication required. Please check development credentials.";
    case "forbidden":
      return "Access denied. You do not have permission for this client or action.";
    case "not_found":
      return "The requested record could not be found.";
    case "review_task_exists":
      return "A review task already exists for this accounting decision run.";
    case "invalid_review_owner":
      return "Review owner must be an active accountant or senior reviewer authorized for this client.";
    case "review_task_not_owned":
      return "This action requires current task ownership.";
    case "invalid_review_task_state":
      return "The task is not in an appropriate state for this action.";
    case "review_task_terminal":
      return "Review task is already resolved (Approved or Rejected) and cannot be modified.";
    case "senior_review_required":
      return "This high-risk task requires review and approval by an authorized Senior Reviewer.";
    case "review_approval_blocked":
      return "Deterministic controls block approval. Ensure the proposed journal is balanced and free of errors.";
    case "information_response_required":
      return "An information request is outstanding. Approval is blocked until the client responds.";
    case "information_not_requested":
      return "No information request is currently pending for this task.";
    case "information_request_missing":
      return "No outstanding information request found.";
    case "decision_stale_after_correction":
      return "Source information changed after this accounting decision was generated. Create a fresh accounting decision before approval.";
    case "review_risk_changed":
      return "Review risk classification no longer matches the source decision. Re-evaluate task.";
    case "review_outcome_exists":
      return "A terminal outcome has already been recorded for this review task.";
    case "review_persistence_failed":
      return "Review state could not be persisted to storage. Please retry.";
    case "rejection_reason_required":
      return "A non-empty rejection reason is required.";
    case "review_comment_required":
      return "Review comment text is required.";
    default:
      return error.message || `Request failed with code: ${error.code}`;
  }
}
