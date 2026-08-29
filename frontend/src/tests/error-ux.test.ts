import { describe, it, expect } from "vitest";
import { ApiError, getFriendlyErrorMessage } from "../lib/api/errors";

describe("Error Normalization & UX Messages", () => {
  it("normalizes API error response objects into ApiError instances", () => {
    const payload = {
      error: {
        code: "review_task_not_owned",
        message: "Action requires ownership.",
        request_id: "req-123",
      },
    };
    const err = ApiError.fromResponse(403, payload);
    expect(err.status).toBe(403);
    expect(err.code).toBe("review_task_not_owned");
    expect(err.requestId).toBe("req-123");

    const fallbackErr = ApiError.fromResponse(500, null, "Default fallback");
    expect(fallbackErr.code).toBe("http_error");
    expect(fallbackErr.message).toBe("Default fallback");
  });

  it("provides helpful actionable messages for all known Phase 5 error codes", () => {
    expect(getFriendlyErrorMessage(new ApiError(401, "unauthenticated", ""))).toContain(
      "Authentication required"
    );
    expect(getFriendlyErrorMessage(new ApiError(403, "forbidden", ""))).toContain(
      "Access denied"
    );
    expect(getFriendlyErrorMessage(new ApiError(404, "not_found", ""))).toContain(
      "The requested record could not be found"
    );
    expect(getFriendlyErrorMessage(new ApiError(409, "review_task_exists", ""))).toContain(
      "A review task already exists"
    );
    expect(getFriendlyErrorMessage(new ApiError(422, "invalid_review_owner", ""))).toContain(
      "Review owner must be an active accountant"
    );
    expect(getFriendlyErrorMessage(new ApiError(403, "review_task_not_owned", ""))).toContain(
      "requires current task ownership"
    );
    expect(getFriendlyErrorMessage(new ApiError(409, "invalid_review_task_state", ""))).toContain(
      "not in an appropriate state"
    );
    expect(getFriendlyErrorMessage(new ApiError(409, "review_task_terminal", ""))).toContain(
      "Review task is already resolved"
    );
    expect(getFriendlyErrorMessage(new ApiError(403, "senior_review_required", ""))).toContain(
      "requires review and approval by an authorized Senior Reviewer"
    );
    expect(getFriendlyErrorMessage(new ApiError(409, "review_approval_blocked", ""))).toContain(
      "Deterministic controls block approval"
    );
    expect(getFriendlyErrorMessage(new ApiError(409, "information_response_required", ""))).toContain(
      "An information request is outstanding"
    );
    expect(getFriendlyErrorMessage(new ApiError(409, "information_not_requested", ""))).toContain(
      "No information request is currently pending"
    );
    expect(getFriendlyErrorMessage(new ApiError(404, "information_request_missing", ""))).toContain(
      "No outstanding information request found"
    );
    expect(getFriendlyErrorMessage(new ApiError(409, "decision_stale_after_correction", ""))).toContain(
      "Source information changed after this accounting decision was generated"
    );
    expect(getFriendlyErrorMessage(new ApiError(409, "review_risk_changed", ""))).toContain(
      "Review risk classification no longer matches"
    );
    expect(getFriendlyErrorMessage(new ApiError(409, "review_outcome_exists", ""))).toContain(
      "A terminal outcome has already been recorded"
    );
    expect(getFriendlyErrorMessage(new ApiError(500, "review_persistence_failed", ""))).toContain(
      "Review state could not be persisted"
    );
    expect(getFriendlyErrorMessage(new ApiError(422, "rejection_reason_required", ""))).toContain(
      "A non-empty rejection reason is required"
    );
    expect(getFriendlyErrorMessage(new ApiError(422, "review_comment_required", ""))).toContain(
      "Review comment text is required"
    );
    expect(getFriendlyErrorMessage(new ApiError(500, "custom_unmapped_code", "Custom message"))).toBe(
      "Custom message"
    );
    expect(getFriendlyErrorMessage(new Error("Standard generic error"))).toBe(
      "Standard generic error"
    );
    expect(getFriendlyErrorMessage("Non-error string")).toBe(
      "An unexpected error occurred."
    );
  });
});
