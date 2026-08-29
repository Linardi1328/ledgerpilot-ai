import {
  AccountingDecisionRunResponse,
  ContextResponse,
  DocumentMetadataResponse,
  ExtractedFieldResponse,
  ExtractionFieldCorrectionRequest,
  ExtractionRunResponse,
  ReviewCommentResponse,
  ReviewHistoryResponse,
  ReviewInteractionResponse,
  ReviewOutcomeResponse,
  ReviewResolutionResponse,
  ReviewTaskLineage,
  ReviewTaskResponse,
} from "@/types/api";
import {
  Permission,
  Principal,
  ReviewCommentKind,
  ReviewEscalationState,
  ReviewOutcomeType,
  ReviewRiskClass,
  ReviewTaskStatus,
  Role,
} from "@/types/roles";
import {
  ALL_SCENARIOS,
  DEV_USERS,
  SCENARIO_BLOCKED,
  SCENARIO_ORDINARY,
  SCENARIO_SENIOR,
  SYNTHETIC_CLIENT_A_ID,
  SYNTHETIC_CLIENT_B_ID,
  SYNTHETIC_FIRM_ID,
  ScenarioBundle,
} from "./fixtures";
import { ApiError } from "../api/errors";

export class MockDataStore {
  private scenarios: Map<string, ScenarioBundle> = new Map();
  private activePrincipalRole: Role = Role.ACCOUNTANT;

  constructor() {
    this.reset();
  }

  reset() {
    this.scenarios.clear();
    // Deep clone scenarios to allow mutations during testing
    ALL_SCENARIOS.forEach((s) => {
      this.scenarios.set(s.lineage.reviewTaskId, JSON.parse(JSON.stringify(s)));
    });
  }

  setRole(role: Role) {
    this.activePrincipalRole = role;
  }

  getPrincipal(role = this.activePrincipalRole): Principal {
    const user = Object.values(DEV_USERS).find((u) => u.role === role) || DEV_USERS.accountant;
    let permissions: Permission[] = [];

    switch (role) {
      case Role.ACCOUNTANT:
        permissions = [
          Permission.VIEW_CONTEXT,
          Permission.UPLOAD_DOCUMENTS,
          Permission.VIEW_DOCUMENTS,
          Permission.RUN_EXTRACTION,
          Permission.CORRECT_EXTRACTED_INFORMATION,
          Permission.RUN_ACCOUNTING_DECISION,
          Permission.REVIEW_RECOMMENDATIONS,
          Permission.CREATE_REVIEW_TASK,
          Permission.VIEW_REVIEW_TASK,
          Permission.ADD_REVIEW_COMMENT,
          Permission.VIEW_REVIEW_HISTORY,
          Permission.APPROVE_ORDINARY_TRANSACTION,
          Permission.REJECT_TRANSACTION,
          Permission.ESCALATE_TRANSACTION,
          Permission.REQUEST_INFORMATION,
          Permission.VIEW_AUDIT_HISTORY,
        ];
        break;
      case Role.SENIOR_REVIEWER:
        permissions = [
          Permission.VIEW_CONTEXT,
          Permission.UPLOAD_DOCUMENTS,
          Permission.VIEW_DOCUMENTS,
          Permission.RUN_EXTRACTION,
          Permission.CORRECT_EXTRACTED_INFORMATION,
          Permission.RUN_ACCOUNTING_DECISION,
          Permission.REVIEW_RECOMMENDATIONS,
          Permission.CREATE_REVIEW_TASK,
          Permission.VIEW_REVIEW_TASK,
          Permission.ADD_REVIEW_COMMENT,
          Permission.VIEW_REVIEW_HISTORY,
          Permission.APPROVE_ORDINARY_TRANSACTION,
          Permission.APPROVE_HIGH_RISK_TRANSACTION,
          Permission.REJECT_TRANSACTION,
          Permission.ESCALATE_TRANSACTION,
          Permission.REQUEST_INFORMATION,
          Permission.VIEW_AUDIT_HISTORY,
          Permission.CORRECT_APPROVED_RECORDS,
        ];
        break;
      case Role.CLIENT_SUBMITTER:
        permissions = [
          Permission.VIEW_CONTEXT,
          Permission.UPLOAD_DOCUMENTS,
          Permission.VIEW_DOCUMENTS,
          Permission.VIEW_INFORMATION_REQUEST,
          Permission.RESPOND_TO_INFORMATION_REQUEST,
        ];
        break;
      case Role.AUDITOR:
        permissions = [
          Permission.VIEW_CONTEXT,
          Permission.VIEW_DOCUMENTS,
          Permission.REVIEW_RECOMMENDATIONS,
          Permission.VIEW_REVIEW_TASK,
          Permission.VIEW_REVIEW_HISTORY,
          Permission.VIEW_AUDIT_HISTORY,
        ];
        break;
      case Role.FIRM_ADMIN:
        permissions = [
          Permission.VIEW_CONTEXT,
          Permission.MANAGE_USERS,
          Permission.MANAGE_CONFIGURATION,
          Permission.MANAGE_INTEGRATIONS,
          Permission.VIEW_AUDIT_HISTORY,
        ];
        break;
    }

    return {
      user_id: user.user_id,
      firm_id: SYNTHETIC_FIRM_ID,
      membership_id: user.membership_id,
      role,
      permissions,
      authorized_client_ids: [SYNTHETIC_CLIENT_A_ID, SYNTHETIC_CLIENT_B_ID],
    };
  }

  getContext(role = this.activePrincipalRole): ContextResponse {
    const p = this.getPrincipal(role);
    return {
      user_id: p.user_id,
      firm_id: p.firm_id,
      membership_id: p.membership_id,
      role: p.role,
      permissions: p.permissions.map((perm) => perm.toString()),
      authorized_client_ids: p.authorized_client_ids,
    };
  }

  getScenario(reviewTaskId: string): ScenarioBundle {
    const scenario = this.scenarios.get(reviewTaskId);
    if (!scenario) {
      throw new ApiError(404, "not_found", `Review task ${reviewTaskId} not found.`);
    }
    return scenario;
  }

  listTasks(): ReviewTaskResponse[] {
    return Array.from(this.scenarios.values()).map((s) => s.task);
  }

  getTask(lineage: ReviewTaskLineage): ReviewTaskResponse {
    const scenario = this.getScenario(lineage.reviewTaskId);
    return scenario.task;
  }

  getHistory(lineage: ReviewTaskLineage): ReviewHistoryResponse {
    const scenario = this.getScenario(lineage.reviewTaskId);
    return scenario.history;
  }

  getDecision(lineage: ReviewTaskLineage): AccountingDecisionRunResponse {
    const scenario = this.getScenario(lineage.reviewTaskId);
    return scenario.decision;
  }

  getExtraction(lineage: ReviewTaskLineage): ExtractionRunResponse {
    const scenario = this.getScenario(lineage.reviewTaskId);
    return scenario.extraction;
  }

  getDocument(clientId: string, documentId: string): DocumentMetadataResponse {
    const scenario = Array.from(this.scenarios.values()).find(
      (s) => s.document.id === documentId
    );
    if (!scenario) {
      throw new ApiError(404, "not_found", `Document ${documentId} not found.`);
    }
    return scenario.document;
  }

  addCorrection(
    lineage: ReviewTaskLineage,
    fieldId: string,
    req: ExtractionFieldCorrectionRequest
  ): ExtractedFieldResponse {
    const scenario = this.getScenario(lineage.reviewTaskId);
    const field = scenario.extraction.fields.find((f) => f.id === fieldId);
    if (!field) {
      throw new ApiError(404, "not_found", `Field ${fieldId} not found.`);
    }

    const revisionNumber = (field.latest_revision_number || 0) + 1;
    field.effective_raw_value = req.corrected_raw_value;
    field.effective_normalized_value = req.corrected_normalized_value || req.corrected_raw_value;
    field.effective_value_type = req.corrected_value_type;
    field.corrected = true;
    field.latest_revision_number = revisionNumber;
    field.latest_correction_id = `corr-${Date.now()}`;

    return field;
  }

  addComment(lineage: ReviewTaskLineage, body: string, principal?: Principal): ReviewCommentResponse {
    const p = principal || this.getPrincipal();
    const scenario = this.getScenario(lineage.reviewTaskId);

    if (scenario.task.status === ReviewTaskStatus.APPROVED || scenario.task.status === ReviewTaskStatus.REJECTED) {
      throw new ApiError(409, "review_task_terminal", "Review task is already resolved.");
    }

    const comment: ReviewCommentResponse = {
      id: `com-${Date.now()}`,
      review_task_id: scenario.task.id,
      author_user_id: p.user_id,
      author_membership_id: p.membership_id,
      kind: ReviewCommentKind.COMMENT,
      body: body.trim(),
      request_id: `req-${Date.now()}`,
      created_at: new Date().toISOString(),
    };

    scenario.history.comments.push(comment);
    return comment;
  }

  escalate(
    lineage: ReviewTaskLineage,
    seniorMembershipId: string,
    reason: string,
    principal?: Principal
  ): ReviewTaskResponse {
    const p = principal || this.getPrincipal();
    const scenario = this.getScenario(lineage.reviewTaskId);

    if (scenario.task.owner_membership_id !== p.membership_id) {
      throw new ApiError(403, "review_task_not_owned", "Review action requires current task ownership.");
    }

    if (scenario.task.status !== ReviewTaskStatus.OPEN) {
      throw new ApiError(409, "invalid_review_task_state", "Task cannot be escalated from current state.");
    }

    scenario.task.status = ReviewTaskStatus.ESCALATED;
    scenario.task.escalation_state = ReviewEscalationState.SENIOR_REVIEW;
    scenario.task.owner_membership_id = seniorMembershipId;
    scenario.task.escalated_at = new Date().toISOString();

    scenario.history.task = { ...scenario.task };
    scenario.history.comments.push({
      id: `esc-${Date.now()}`,
      review_task_id: scenario.task.id,
      author_user_id: p.user_id,
      author_membership_id: p.membership_id,
      kind: ReviewCommentKind.ESCALATION_REASON,
      body: reason.trim(),
      request_id: `req-${Date.now()}`,
      created_at: new Date().toISOString(),
    });

    scenario.history.audit_events.push({
      id: `evt-${Date.now()}`,
      actor_user_id: p.user_id,
      event_type: "review_task_escalated",
      target_type: "review_task",
      target_id: scenario.task.id,
      occurred_at: new Date().toISOString(),
      request_id: `req-${Date.now()}`,
      metadata: { senior_membership_id: seniorMembershipId },
    });

    return scenario.task;
  }

  requestInfo(lineage: ReviewTaskLineage, body: string, principal?: Principal): ReviewInteractionResponse {
    const p = principal || this.getPrincipal();
    const scenario = this.getScenario(lineage.reviewTaskId);

    if (scenario.task.owner_membership_id !== p.membership_id) {
      throw new ApiError(403, "review_task_not_owned", "Review action requires current task ownership.");
    }

    scenario.task.status = ReviewTaskStatus.INFORMATION_REQUESTED;
    scenario.history.task.status = ReviewTaskStatus.INFORMATION_REQUESTED;

    const comment: ReviewCommentResponse = {
      id: `inforeq-${Date.now()}`,
      review_task_id: scenario.task.id,
      author_user_id: p.user_id,
      author_membership_id: p.membership_id,
      kind: ReviewCommentKind.INFORMATION_REQUEST,
      body: body.trim(),
      request_id: `req-${Date.now()}`,
      created_at: new Date().toISOString(),
    };

    scenario.history.comments.push(comment);
    scenario.history.audit_events.push({
      id: `evt-${Date.now()}`,
      actor_user_id: p.user_id,
      event_type: "review_information_requested",
      target_type: "review_task",
      target_id: scenario.task.id,
      occurred_at: new Date().toISOString(),
      request_id: `req-${Date.now()}`,
      metadata: {},
    });

    return { task: scenario.task, comment };
  }

  getOutstandingInfoRequest(lineage: ReviewTaskLineage): ReviewCommentResponse {
    const scenario = this.getScenario(lineage.reviewTaskId);
    const req = scenario.history.comments
      .slice()
      .reverse()
      .find((c) => c.kind === ReviewCommentKind.INFORMATION_REQUEST);

    if (!req) {
      throw new ApiError(404, "information_not_requested", "No outstanding information request.");
    }
    return req;
  }

  respondToInfo(lineage: ReviewTaskLineage, body: string, principal?: Principal): ReviewInteractionResponse {
    const p = principal || this.getPrincipal(Role.CLIENT_SUBMITTER);
    const scenario = this.getScenario(lineage.reviewTaskId);

    if (scenario.task.status !== ReviewTaskStatus.INFORMATION_REQUESTED) {
      throw new ApiError(409, "information_not_requested", "Task is not waiting for an information response.");
    }

    // Returns task to open or escalated depending on escalation_state
    const newStatus =
      scenario.task.escalation_state === ReviewEscalationState.SENIOR_REVIEW
        ? ReviewTaskStatus.ESCALATED
        : ReviewTaskStatus.OPEN;

    scenario.task.status = newStatus;
    scenario.history.task.status = newStatus;

    const comment: ReviewCommentResponse = {
      id: `inforesp-${Date.now()}`,
      review_task_id: scenario.task.id,
      author_user_id: p.user_id,
      author_membership_id: p.membership_id,
      kind: ReviewCommentKind.INFORMATION_RESPONSE,
      body: body.trim(),
      request_id: `req-${Date.now()}`,
      created_at: new Date().toISOString(),
    };

    scenario.history.comments.push(comment);
    scenario.history.audit_events.push({
      id: `evt-${Date.now()}`,
      actor_user_id: p.user_id,
      event_type: "review_information_responded",
      target_type: "review_task",
      target_id: scenario.task.id,
      occurred_at: new Date().toISOString(),
      request_id: `req-${Date.now()}`,
      metadata: {},
    });

    return { task: scenario.task, comment };
  }

  approve(lineage: ReviewTaskLineage, note?: string | null, principal?: Principal): ReviewResolutionResponse {
    const p = principal || this.getPrincipal();
    const scenario = this.getScenario(lineage.reviewTaskId);

    if (scenario.task.owner_membership_id !== p.membership_id) {
      throw new ApiError(403, "review_task_not_owned", "Review action requires current task ownership.");
    }

    if (scenario.task.risk_class === ReviewRiskClass.BLOCKED) {
      throw new ApiError(409, "review_approval_blocked", "Deterministic controls block approval.");
    }

    if (scenario.task.risk_class === ReviewRiskClass.SENIOR_REVIEW_REQUIRED) {
      if (p.role !== Role.SENIOR_REVIEWER || scenario.task.status !== ReviewTaskStatus.ESCALATED) {
        throw new ApiError(403, "senior_review_required", "This review requires approval by an assigned senior reviewer.");
      }
    }

    if (scenario.decision.proposed_journal && !scenario.decision.proposed_journal.is_balanced) {
      throw new ApiError(409, "review_approval_blocked", "A balanced proposed journal is required for approval.");
    }

    const hasCorrections = scenario.extraction.fields.some((f) => f.corrected);
    const outcomeType = hasCorrections
      ? ReviewOutcomeType.CORRECTED_AND_APPROVED
      : ReviewOutcomeType.APPROVED;

    const outcome: ReviewOutcomeResponse = {
      id: `out-${Date.now()}`,
      review_task_id: scenario.task.id,
      actor_user_id: p.user_id,
      actor_membership_id: p.membership_id,
      outcome_type: outcomeType,
      proposed_journal_id: scenario.decision.proposed_journal?.id || null,
      source_correction_count: hasCorrections ? 1 : 0,
      reason: note || null,
      request_id: `req-${Date.now()}`,
      created_at: new Date().toISOString(),
    };

    scenario.task.status = ReviewTaskStatus.APPROVED;
    scenario.history.task.status = ReviewTaskStatus.APPROVED;
    scenario.history.outcome = outcome;

    scenario.history.audit_events.push({
      id: `evt-${Date.now()}`,
      actor_user_id: p.user_id,
      event_type: "review_task_approved",
      target_type: "review_task",
      target_id: scenario.task.id,
      occurred_at: new Date().toISOString(),
      request_id: `req-${Date.now()}`,
      metadata: {
        outcome_id: outcome.id,
        outcome_type: outcome.outcome_type,
      },
    });

    return { task: scenario.task, outcome };
  }

  reject(lineage: ReviewTaskLineage, reason: string, principal?: Principal): ReviewResolutionResponse {
    const p = principal || this.getPrincipal();
    const scenario = this.getScenario(lineage.reviewTaskId);

    if (!reason || !reason.trim()) {
      throw new ApiError(422, "rejection_reason_required", "A rejection reason is required.");
    }

    if (scenario.task.owner_membership_id !== p.membership_id) {
      throw new ApiError(403, "review_task_not_owned", "Review action requires current task ownership.");
    }

    const outcome: ReviewOutcomeResponse = {
      id: `out-${Date.now()}`,
      review_task_id: scenario.task.id,
      actor_user_id: p.user_id,
      actor_membership_id: p.membership_id,
      outcome_type: ReviewOutcomeType.REJECTED,
      proposed_journal_id: null,
      source_correction_count: 0,
      reason: reason.trim(),
      request_id: `req-${Date.now()}`,
      created_at: new Date().toISOString(),
    };

    scenario.task.status = ReviewTaskStatus.REJECTED;
    scenario.history.task.status = ReviewTaskStatus.REJECTED;
    scenario.history.outcome = outcome;

    scenario.history.audit_events.push({
      id: `evt-${Date.now()}`,
      actor_user_id: p.user_id,
      event_type: "review_task_rejected",
      target_type: "review_task",
      target_id: scenario.task.id,
      occurred_at: new Date().toISOString(),
      request_id: `req-${Date.now()}`,
      metadata: {
        outcome_id: outcome.id,
        outcome_type: outcome.outcome_type,
      },
    });

    return { task: scenario.task, outcome };
  }

  generateFreshDecisionAndTask(
    lineage: ReviewTaskLineage,
    principal?: Principal
  ): { decision: AccountingDecisionRunResponse; task: ReviewTaskResponse; newLineage: ReviewTaskLineage } {
    const p = principal || this.getPrincipal();
    const scenario = this.getScenario(lineage.reviewTaskId);

    const newDecId = `a-fresh-${Date.now()}`;
    const newTaskId = `r-fresh-${Date.now()}`;

    const newDecision: AccountingDecisionRunResponse = {
      ...JSON.parse(JSON.stringify(scenario.decision)),
      id: newDecId,
      created_at: new Date().toISOString(),
    };

    const newTask: ReviewTaskResponse = {
      ...JSON.parse(JSON.stringify(scenario.task)),
      id: newTaskId,
      decision_run_id: newDecId,
      status: ReviewTaskStatus.OPEN,
      owner_user_id: p.user_id,
      owner_membership_id: p.membership_id,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    const newLineage: ReviewTaskLineage = {
      clientId: lineage.clientId,
      documentId: lineage.documentId,
      extractionRunId: lineage.extractionRunId,
      decisionRunId: newDecId,
      reviewTaskId: newTaskId,
    };

    const newScenario: ScenarioBundle = {
      key: `fresh-${Date.now()}`,
      title: `${scenario.title} (Fresh Decision)`,
      lineage: newLineage,
      document: JSON.parse(JSON.stringify(scenario.document)),
      extraction: JSON.parse(JSON.stringify(scenario.extraction)),
      decision: newDecision,
      task: newTask,
      history: {
        task: newTask,
        comments: [],
        outcome: null,
        audit_events: [
          {
            id: `evt-${Date.now()}`,
            actor_user_id: p.user_id,
            event_type: "review_task_created",
            target_type: "review_task",
            target_id: newTaskId,
            occurred_at: new Date().toISOString(),
            request_id: `req-${Date.now()}`,
            metadata: { fresh_decision_for: lineage.decisionRunId },
          },
        ],
      },
    };

    this.scenarios.set(newTaskId, newScenario);

    return { decision: newDecision, task: newTask, newLineage };
  }
}

export const mockDataStore = new MockDataStore();
