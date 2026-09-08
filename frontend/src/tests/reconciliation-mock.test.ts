import { beforeEach, describe, expect, it } from "vitest";
import { MockReconciliationStore } from "@/lib/mock/reconciliation";
import { SYNTHETIC_CLIENT_A_ID, SYNTHETIC_CLIENT_B_ID } from "@/lib/mock/fixtures";

let store: MockReconciliationStore;

beforeEach(() => {
  store = new MockReconciliationStore();
});

describe("mock reconciliation store", () => {
  it("exposes all seven Phase 6 workflow states for UI feature testing", () => {
    const items = store.listWorklist(SYNTHETIC_CLIENT_A_ID);
    expect(new Set(items.map((item) => item.workflow_state))).toEqual(
      new Set([
        "not_evaluated",
        "unmatched",
        "candidates_available",
        "in_review",
        "disputed",
        "matched",
        "resolved_unmatched",
      ])
    );
    expect(store.listWorklist(SYNTHETIC_CLIENT_A_ID, "matched")).toHaveLength(1);
    expect(store.listWorklist(SYNTHETIC_CLIENT_B_ID)).toHaveLength(1);
  });

  it("drives deterministic candidate generation into human review and match approval", () => {
    const initial = store.listWorklist(SYNTHETIC_CLIENT_A_ID, "not_evaluated")[0];
    const generated = store.generateMatch(SYNTHETIC_CLIENT_A_ID, initial.transaction.id);
    expect(generated.run.status).toBe("candidates_available");
    expect(generated.candidates).toHaveLength(1);
    expect(generated.candidates[0].score).toBe("1.0000");

    const created = store.createReview(SYNTHETIC_CLIENT_A_ID, initial.transaction.id);
    expect(created.status).toBe("open");
    const selected = store.selectCandidate(
      SYNTHETIC_CLIENT_A_ID,
      initial.transaction.id,
      created.id,
      generated.candidates[0].review_outcome_id
    );
    expect(selected.selected_review_outcome_id).toBe(generated.candidates[0].review_outcome_id);

    const disputed = store.dispute(
      SYNTHETIC_CLIENT_A_ID,
      initial.transaction.id,
      created.id,
      "Synthetic discrepancy."
    );
    expect(disputed.status).toBe("disputed");
    const reopened = store.reopen(
      SYNTHETIC_CLIENT_A_ID,
      initial.transaction.id,
      created.id,
      "Synthetic evidence verified."
    );
    expect(reopened.status).toBe("open");

    const terminal = store.approve(
      SYNTHETIC_CLIENT_A_ID,
      initial.transaction.id,
      created.id,
      "Human approved synthetic match."
    );
    expect(terminal.review.status).toBe("matched");
    expect(terminal.outcome.outcome_type).toBe("matched");
    expect(terminal.outcome.matched_review_outcome_id).toBe(
      generated.candidates[0].review_outcome_id
    );

    const history = store.history(created.id);
    expect(history?.actions.map((entry) => entry.action_type)).toEqual([
      "candidate_selected",
      "disputed",
      "reopened",
      "approved_match",
    ]);
    expect(history?.outcome?.outcome_type).toBe("matched");
  });

  it("drives deterministic no-match evidence into an explicit human unmatched outcome", () => {
    const unmatched = store.listWorklist(SYNTHETIC_CLIENT_A_ID, "unmatched")[0];
    expect(unmatched.latest_match_run?.status).toBe("unmatched");
    expect(store.listCandidates(unmatched.latest_match_run!.id)).toEqual([]);

    const created = store.createReview(SYNTHETIC_CLIENT_A_ID, unmatched.transaction.id);
    const terminal = store.markUnmatched(
      SYNTHETIC_CLIENT_A_ID,
      unmatched.transaction.id,
      created.id,
      "No approved accounting evidence matches this synthetic bank transaction."
    );
    expect(terminal.review.status).toBe("unmatched");
    expect(terminal.outcome.outcome_type).toBe("unmatched");
    expect(store.listWorklist(SYNTHETIC_CLIENT_A_ID, "resolved_unmatched")).toHaveLength(2);
  });

  it("returns cloned values so callers cannot mutate stored evidence accidentally", () => {
    const first = store.listWorklist(SYNTHETIC_CLIENT_A_ID);
    first[0].workflow_state = "matched";
    const second = store.listWorklist(SYNTHETIC_CLIENT_A_ID);
    expect(second[0].workflow_state).toBe("not_evaluated");
  });

  it("rejects invalid mock human-review transitions", () => {
    const item = store.listWorklist(SYNTHETIC_CLIENT_A_ID, "not_evaluated")[0];
    expect(() => store.createReview(SYNTHETIC_CLIENT_A_ID, item.transaction.id)).toThrow();
    expect(store.history("missing-review")).toBeNull();
    expect(() => store.generateMatch(SYNTHETIC_CLIENT_A_ID, "missing-tx")).toThrow();
  });
});
