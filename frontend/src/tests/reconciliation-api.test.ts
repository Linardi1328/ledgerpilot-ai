import { describe, expect, it, vi } from "vitest";
import { ApiClient } from "@/lib/api/client";
import {
  approveReconciliationMatch,
  createReconciliationReview,
  disputeReconciliationReview,
  generateReconciliationMatch,
  getReconciliationHistory,
  listReconciliationCandidates,
  listReconciliationWorklist,
  markReconciliationUnmatched,
  reopenReconciliationReview,
  selectReconciliationCandidate,
} from "@/lib/api/reconciliation";

const context = { devSubject: "dev-accountant", firmId: "firm-1" };

function mockClient() {
  const client = new ApiClient("/api/backend");
  const get = vi.spyOn(client, "get").mockResolvedValue([]);
  const post = vi.spyOn(client, "post").mockResolvedValue({});
  return { client, get, post };
}

describe("reconciliation API client", () => {
  it("builds worklist requests with optional authoritative state filter", async () => {
    const { client, get } = mockClient();
    await listReconciliationWorklist("client a", context, "disputed", client);
    expect(get).toHaveBeenCalledWith("/clients/client%20a/bank-reconciliation/worklist", {
      ...context,
      searchParams: { state: "disputed" },
    });

    await listReconciliationWorklist("client a", context, undefined, client);
    expect(get).toHaveBeenLastCalledWith("/clients/client%20a/bank-reconciliation/worklist", {
      ...context,
      searchParams: undefined,
    });
  });

  it("builds match generation and candidate evidence requests", async () => {
    const { client, get, post } = mockClient();
    await generateReconciliationMatch("client-1", "tx-1", context, client);
    expect(post).toHaveBeenCalledWith(
      "/clients/client-1/bank-reconciliation/transactions/tx-1/match-runs",
      {},
      context
    );

    await listReconciliationCandidates("client-1", "tx-1", "run id", context, client);
    expect(get).toHaveBeenCalledWith(
      "/clients/client-1/bank-reconciliation/transactions/tx-1/match-runs/run%20id/candidates",
      context
    );
  });

  it("builds human review creation and candidate selection requests", async () => {
    const { client, post } = mockClient();
    await createReconciliationReview("client-1", "tx-1", "run-1", context, client);
    expect(post).toHaveBeenCalledWith(
      "/clients/client-1/bank-reconciliation/transactions/tx-1/reviews",
      { match_run_id: "run-1" },
      context
    );

    await selectReconciliationCandidate(
      "client-1",
      "tx-1",
      "review id",
      "outcome-1",
      context,
      client
    );
    expect(post).toHaveBeenLastCalledWith(
      "/clients/client-1/bank-reconciliation/transactions/tx-1/reviews/review%20id/candidate-selection",
      { review_outcome_id: "outcome-1" },
      context
    );
  });

  it("builds dispute, reopen, and terminal decision requests", async () => {
    const { client, post } = mockClient();
    const root = "/clients/client-1/bank-reconciliation/transactions/tx-1/reviews/review-1";

    await disputeReconciliationReview("client-1", "tx-1", "review-1", "reason", context, client);
    expect(post).toHaveBeenLastCalledWith(`${root}/dispute`, { reason: "reason" }, context);

    await reopenReconciliationReview("client-1", "tx-1", "review-1", "reopen", context, client);
    expect(post).toHaveBeenLastCalledWith(`${root}/reopen`, { reason: "reopen" }, context);

    await approveReconciliationMatch("client-1", "tx-1", "review-1", "note", context, client);
    expect(post).toHaveBeenLastCalledWith(`${root}/approve`, { note: "note" }, context);

    await markReconciliationUnmatched(
      "client-1",
      "tx-1",
      "review-1",
      "no match",
      context,
      client
    );
    expect(post).toHaveBeenLastCalledWith(
      `${root}/mark-unmatched`,
      { reason: "no match" },
      context
    );
  });

  it("builds immutable history request", async () => {
    const { client, get } = mockClient();
    await getReconciliationHistory("client-1", "tx-1", "review-1", context, client);
    expect(get).toHaveBeenCalledWith(
      "/clients/client-1/bank-reconciliation/transactions/tx-1/reviews/review-1/history",
      context
    );
  });
});
