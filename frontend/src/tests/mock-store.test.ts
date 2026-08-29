import { describe, it, expect, beforeEach } from "vitest";
import { MockDataStore } from "../lib/mock/mock-client";
import { Role, ReviewTaskStatus, ReviewRiskClass, ReviewOutcomeType, ReviewCommentKind } from "../types/roles";
import { SCENARIO_ORDINARY, SCENARIO_SENIOR, SCENARIO_BLOCKED, DEV_USERS } from "../lib/mock/fixtures";
import { ApiError } from "../lib/api/errors";

describe("Mock Data Store & State Engine", () => {
  let store: MockDataStore;

  beforeEach(() => {
    store = new MockDataStore();
  });

  it("initializes scenarios and retrieves principals for all roles", () => {
    expect(store.listTasks().length).toBe(3);

    const accountantPrincipal = store.getPrincipal(Role.ACCOUNTANT);
    expect(accountantPrincipal.role).toBe(Role.ACCOUNTANT);
    expect(accountantPrincipal.membership_id).toBe(DEV_USERS.accountant.membership_id);

    const seniorPrincipal = store.getPrincipal(Role.SENIOR_REVIEWER);
    expect(seniorPrincipal.role).toBe(Role.SENIOR_REVIEWER);

    const clientPrincipal = store.getPrincipal(Role.CLIENT_SUBMITTER);
    expect(clientPrincipal.role).toBe(Role.CLIENT_SUBMITTER);

    const auditorPrincipal = store.getPrincipal(Role.AUDITOR);
    expect(auditorPrincipal.role).toBe(Role.AUDITOR);

    const adminPrincipal = store.getPrincipal(Role.FIRM_ADMIN);
    expect(adminPrincipal.role).toBe(Role.FIRM_ADMIN);

    const context = store.getContext();
    expect(context.firm_id).toBe(accountantPrincipal.firm_id);
  });

  it("handles field corrections on extracted fields non-destructively", () => {
    const lineage = SCENARIO_ORDINARY.lineage;
    const res = store.addCorrection(lineage, "fld-08", {
      corrected_raw_value: "1250.00",
      corrected_value_type: "decimal",
      reason: "Corrected subtotal",
    });

    expect(res.corrected).toBe(true);
    expect(res.effective_raw_value).toBe("1250.00");
    expect(res.latest_revision_number).toBe(2);
  });

  it("handles internal reviewer comments and prevents comments on terminal tasks", () => {
    const lineage = SCENARIO_ORDINARY.lineage;
    const comment = store.addComment(lineage, "Internal validation note");
    expect(comment.body).toBe("Internal validation note");
    expect(comment.kind).toBe(ReviewCommentKind.COMMENT);

    // Approve the task to make it terminal
    store.approve(lineage, "Approved note");

    // Attempting to comment on terminal task throws error
    expect(() => store.addComment(lineage, "Should fail")).toThrow(ApiError);
  });

  it("escalates open task to senior reviewer and records escalation comment", () => {
    const lineage = SCENARIO_ORDINARY.lineage;
    const seniorMemId = DEV_USERS.senior.membership_id;
    const updatedTask = store.escalate(lineage, seniorMemId, "Escalating for senior check");

    expect(updatedTask.status).toBe(ReviewTaskStatus.ESCALATED);
    expect(updatedTask.owner_membership_id).toBe(seniorMemId);

    const history = store.getHistory(lineage);
    const escComment = history.comments.find((c) => c.kind === ReviewCommentKind.ESCALATION_REASON);
    expect(escComment?.body).toBe("Escalating for senior check");
  });

  it("handles information request and client response workflow", () => {
    const lineage = SCENARIO_ORDINARY.lineage;
    const inforeq = store.requestInfo(lineage, "Please clarify line 2");
    expect(inforeq.task.status).toBe(ReviewTaskStatus.INFORMATION_REQUESTED);

    const outstanding = store.getOutstandingInfoRequest(lineage);
    expect(outstanding.body).toBe("Please clarify line 2");

    const inforesp = store.respondToInfo(lineage, "Line 2 is SST input tax");
    expect(inforesp.task.status).toBe(ReviewTaskStatus.OPEN);

    const history = store.getHistory(lineage);
    const respComment = history.comments.find((c) => c.kind === ReviewCommentKind.INFORMATION_RESPONSE);
    expect(respComment?.body).toBe("Line 2 is SST input tax");
  });

  it("rejects task and records immutable outcome", () => {
    const lineage = SCENARIO_ORDINARY.lineage;
    const res = store.reject(lineage, "Invalid supplier billing invoice");

    expect(res.task.status).toBe(ReviewTaskStatus.REJECTED);
    expect(res.outcome.outcome_type).toBe(ReviewOutcomeType.REJECTED);
    expect(res.outcome.reason).toBe("Invalid supplier billing invoice");
  });

  it("blocks approval if journal is unbalanced or risk is blocked", () => {
    const lineage = SCENARIO_BLOCKED.lineage;
    expect(() => store.approve(lineage)).toThrow(ApiError);
  });
});
