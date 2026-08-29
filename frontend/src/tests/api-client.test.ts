import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { ApiClient } from "../lib/api/client";
import { ApiError } from "../lib/api/errors";
import {
  buildDecisionApiPath,
  buildDocumentApiPath,
  buildExtractionApiPath,
  buildLivePortalUrl,
  buildLiveReviewTaskUrl,
  buildReviewTaskApiPath,
} from "../lib/api/lineage";
import { checkLiveness, fetchContext } from "../lib/api/context";
import { uploadDocument, fetchDocumentMetadata } from "../lib/api/documents";
import { createExtractionRun, fetchExtractionRun, addFieldCorrection } from "../lib/api/extractions";
import { createAccountingDecisionRun, fetchAccountingDecisionRun } from "../lib/api/accounting";
import {
  createReviewTask,
  fetchReviewTask,
  listReviewTasks,
  escalateReviewTask,
  addReviewComment,
  requestInformation,
  getOutstandingInformationRequest,
  respondToInformationRequest,
  approveReviewTask,
  rejectReviewTask,
  fetchReviewHistory,
} from "../lib/api/reviews";

describe("API Client & Lineage Helpers", () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    global.fetch = vi.fn();
  });

  afterEach(() => {
    global.fetch = originalFetch;
  });

  it("builds correct canonical lineage URLs and API paths", () => {
    const lineage = {
      clientId: "client-1",
      documentId: "doc-1",
      extractionRunId: "ext-1",
      decisionRunId: "dec-1",
      reviewTaskId: "task-1",
    };

    expect(buildLiveReviewTaskUrl(lineage)).toBe(
      "/reviews/client-1/documents/doc-1/extractions/ext-1/decisions/dec-1/tasks/task-1"
    );
    expect(buildLivePortalUrl(lineage)).toBe(
      "/portal/client-1/documents/doc-1/extractions/ext-1/decisions/dec-1/tasks/task-1"
    );
    expect(buildReviewTaskApiPath(lineage)).toBe(
      "/clients/client-1/documents/doc-1/extractions/ext-1/accounting-decisions/dec-1/review-tasks/task-1"
    );
    expect(buildDecisionApiPath("c1", "d1", "e1", "dec1")).toBe(
      "/clients/c1/documents/d1/extractions/e1/accounting-decisions/dec1"
    );
    expect(buildExtractionApiPath("c1", "d1", "e1")).toBe(
      "/clients/c1/documents/d1/extractions/e1"
    );
    expect(buildDocumentApiPath("c1", "d1")).toBe(
      "/clients/c1/documents/d1"
    );
  });

  it("sends appropriate development auth headers and request IDs", async () => {
    const mockResponse = {
      ok: true,
      headers: new Headers({ "content-type": "application/json" }),
      json: vi.fn().mockResolvedValue({ success: true }),
    };
    (global.fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(mockResponse);

    const client = new ApiClient("http://127.0.0.1:8000/api/v1");
    const res = await client.get<{ success: boolean }>("/test", {
      devSubject: "dev-accountant",
      firmId: "firm-1",
      requestId: "req-custom-99",
      searchParams: { filter: "active" },
    });

    expect(res).toEqual({ success: true });
    expect(global.fetch).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/api/v1/test?filter=active",
      expect.objectContaining({
        headers: expect.any(Headers),
      })
    );

    const calledHeaders = (global.fetch as unknown as ReturnType<typeof vi.fn>).mock.calls[0][1].headers as Headers;
    expect(calledHeaders.get("X-LedgerPilot-Dev-Subject")).toBe("dev-accountant");
    expect(calledHeaders.get("X-LedgerPilot-Firm")).toBe("firm-1");
    expect(calledHeaders.get("X-Request-ID")).toBe("req-custom-99");
  });

  it("handles network failure and raises typed backend_unavailable error", async () => {
    (global.fetch as unknown as ReturnType<typeof vi.fn>).mockRejectedValue(new Error("Network connection dropped"));

    const client = new ApiClient("http://127.0.0.1:8000/api/v1");
    await expect(client.get("/health")).rejects.toThrow(ApiError);
    await expect(client.get("/health")).rejects.toMatchObject({
      code: "backend_unavailable",
    });
  });

  it("calls API service endpoints with expected HTTP methods", async () => {
    const mockJson = vi.fn().mockResolvedValue({ id: "mock-res" });
    (global.fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      headers: new Headers({ "content-type": "application/json" }),
      json: mockJson,
    });

    const client = new ApiClient("http://127.0.0.1:8000/api/v1");
    const lineage = {
      clientId: "c1",
      documentId: "d1",
      extractionRunId: "e1",
      decisionRunId: "a1",
      reviewTaskId: "r1",
    };

    await fetchContext(client);
    await checkLiveness(client);
    await uploadDocument("c1", new File(["test"], "test.pdf"), client);
    await fetchDocumentMetadata("c1", "d1", client);
    await createExtractionRun("c1", "d1", client);
    await fetchExtractionRun("c1", "d1", "e1", client);
    await addFieldCorrection("c1", "d1", "e1", "f1", { corrected_raw_value: "100", corrected_value_type: "decimal", reason: "Fix" }, client);
    await createAccountingDecisionRun("c1", "d1", "e1", client);
    await fetchAccountingDecisionRun("c1", "d1", "e1", "a1", client);
    await createReviewTask({ clientId: "c1", documentId: "d1", extractionRunId: "e1", decisionRunId: "a1" }, "mem-1", client);
    await listReviewTasks({ clientId: "c1", documentId: "d1", extractionRunId: "e1", decisionRunId: "a1" }, client);
    await fetchReviewTask(lineage, client);
    await escalateReviewTask(lineage, "mem-sen", "Reason", client);
    await addReviewComment(lineage, "Comment", client);
    await requestInformation(lineage, "Question", client);
    await getOutstandingInformationRequest(lineage, client);
    await respondToInformationRequest(lineage, "Answer", client);
    await approveReviewTask(lineage, "Note", client);
    await rejectReviewTask(lineage, "Reason", client);
    await fetchReviewHistory(lineage, client);

    expect(global.fetch).toHaveBeenCalledTimes(20);
  });
});
