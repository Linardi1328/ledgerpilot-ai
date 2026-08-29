import { describe, it, expect } from "vitest";
import {
  canApproveOrdinary,
  canApproveSenior,
  canComment,
  canCorrectField,
  canEscalate,
  canReject,
  canRequestInformation,
  canViewClientPortal,
  canViewReviewWorkspace,
  isTerminalTask,
} from "../lib/policy/action-policy";
import {
  Permission,
  Principal,
  ReviewEscalationState,
  ReviewRiskClass,
  ReviewTaskStatus,
  Role,
} from "../types/roles";
import { ProposedJournalResponse, ReviewTaskResponse } from "../types/api";

const mockAccountantPrincipal: Principal = {
  user_id: "user-acc-01",
  firm_id: "firm-01",
  membership_id: "mem-acc-01",
  role: Role.ACCOUNTANT,
  permissions: [
    Permission.VIEW_REVIEW_TASK,
    Permission.APPROVE_ORDINARY_TRANSACTION,
    Permission.ESCALATE_TRANSACTION,
    Permission.REQUEST_INFORMATION,
    Permission.REJECT_TRANSACTION,
    Permission.ADD_REVIEW_COMMENT,
    Permission.CORRECT_EXTRACTED_INFORMATION,
  ],
  authorized_client_ids: ["client-01"],
};

const mockSeniorPrincipal: Principal = {
  user_id: "user-sen-01",
  firm_id: "firm-01",
  membership_id: "mem-sen-01",
  role: Role.SENIOR_REVIEWER,
  permissions: [
    Permission.VIEW_REVIEW_TASK,
    Permission.APPROVE_ORDINARY_TRANSACTION,
    Permission.APPROVE_HIGH_RISK_TRANSACTION,
    Permission.ESCALATE_TRANSACTION,
    Permission.REQUEST_INFORMATION,
    Permission.REJECT_TRANSACTION,
    Permission.ADD_REVIEW_COMMENT,
    Permission.CORRECT_EXTRACTED_INFORMATION,
  ],
  authorized_client_ids: ["client-01"],
};

const mockAuditorPrincipal: Principal = {
  user_id: "user-aud-01",
  firm_id: "firm-01",
  membership_id: "mem-aud-01",
  role: Role.AUDITOR,
  permissions: [Permission.VIEW_REVIEW_TASK, Permission.VIEW_REVIEW_HISTORY],
  authorized_client_ids: ["client-01"],
};

const mockFirmAdminPrincipal: Principal = {
  user_id: "user-adm-01",
  firm_id: "firm-01",
  membership_id: "mem-adm-01",
  role: Role.FIRM_ADMIN,
  permissions: [Permission.MANAGE_USERS, Permission.VIEW_AUDIT_HISTORY],
  authorized_client_ids: ["client-01"],
};

const mockClientSubmitterPrincipal: Principal = {
  user_id: "user-sub-01",
  firm_id: "firm-01",
  membership_id: "mem-sub-01",
  role: Role.CLIENT_SUBMITTER,
  permissions: [Permission.VIEW_INFORMATION_REQUEST, Permission.RESPOND_TO_INFORMATION_REQUEST],
  authorized_client_ids: ["client-01"],
};

const mockBalancedJournal: ProposedJournalResponse = {
  id: "pj-01",
  currency: "MYR",
  total_debits: "1250.00",
  total_credits: "1250.00",
  balance_status: "balanced",
  is_balanced: true,
  explanation: "Balanced",
  lines: [],
};

const mockUnbalancedJournal: ProposedJournalResponse = {
  id: "pj-02",
  currency: "MYR",
  total_debits: "1250.00",
  total_credits: "1240.00",
  balance_status: "unbalanced",
  is_balanced: false,
  explanation: "Unbalanced",
  lines: [],
};

const mockOrdinaryTask: ReviewTaskResponse = {
  id: "task-01",
  firm_id: "firm-01",
  client_id: "client-01",
  decision_run_id: "dec-01",
  document_id: "doc-01",
  extraction_run_id: "ext-01",
  created_by_user_id: "user-acc-01",
  created_by_membership_id: "mem-acc-01",
  owner_user_id: "user-acc-01",
  owner_membership_id: "mem-acc-01",
  status: ReviewTaskStatus.OPEN,
  risk_class: ReviewRiskClass.ORDINARY,
  escalation_state: ReviewEscalationState.NONE,
  escalated_at: null,
  request_id: "req-01",
  created_at: "2026-08-29T10:00:00Z",
  updated_at: "2026-08-29T10:00:00Z",
};

describe("Action Policy Matrix", () => {
  describe("Null / Undefined checks", () => {
    it("handles null and undefined arguments gracefully", () => {
      expect(isTerminalTask(null)).toBe(false);
      expect(canViewReviewWorkspace(null)).toBe(false);
      expect(canViewClientPortal(null)).toBe(false);
      expect(canApproveOrdinary(null, null, null)).toBe(false);
      expect(canApproveSenior(null, null, null)).toBe(false);
      expect(canEscalate(null, null)).toBe(false);
      expect(canRequestInformation(null, null)).toBe(false);
      expect(canReject(null, null)).toBe(false);
      expect(canComment(null, null)).toBe(false);
      expect(canCorrectField(null, null)).toBe(false);
    });
  });

  describe("Ordinary Approval (canApproveOrdinary)", () => {
    it("allows owner Accountant to approve balanced ordinary task", () => {
      expect(
        canApproveOrdinary(mockAccountantPrincipal, mockOrdinaryTask, mockBalancedJournal)
      ).toBe(true);
    });

    it("denies if principal lacks APPROVE_ORDINARY_TRANSACTION permission", () => {
      const p = { ...mockAccountantPrincipal, permissions: [] };
      expect(canApproveOrdinary(p, mockOrdinaryTask, mockBalancedJournal)).toBe(false);
    });

    it("denies if role is not accountant or senior reviewer", () => {
      expect(canApproveOrdinary(mockAuditorPrincipal, mockOrdinaryTask, mockBalancedJournal)).toBe(false);
    });

    it("denies non-owner Accountant from approving", () => {
      const nonOwnerPrincipal = { ...mockAccountantPrincipal, membership_id: "mem-other" };
      expect(
        canApproveOrdinary(nonOwnerPrincipal, mockOrdinaryTask, mockBalancedJournal)
      ).toBe(false);
    });

    it("denies approval if journal is unbalanced or null", () => {
      expect(
        canApproveOrdinary(mockAccountantPrincipal, mockOrdinaryTask, mockUnbalancedJournal)
      ).toBe(false);
      expect(
        canApproveOrdinary(mockAccountantPrincipal, mockOrdinaryTask, null)
      ).toBe(false);
    });

    it("denies approval if decision is stale", () => {
      expect(
        canApproveOrdinary(mockAccountantPrincipal, mockOrdinaryTask, mockBalancedJournal, true)
      ).toBe(false);
    });

    it("denies approval for senior_review_required risk task under ordinary flow", () => {
      const seniorRiskTask = {
        ...mockOrdinaryTask,
        risk_class: ReviewRiskClass.SENIOR_REVIEW_REQUIRED,
      };
      expect(
        canApproveOrdinary(mockAccountantPrincipal, seniorRiskTask, mockBalancedJournal)
      ).toBe(false);
    });

    it("denies approval if task status is information_requested", () => {
      const infoReqTask = {
        ...mockOrdinaryTask,
        status: ReviewTaskStatus.INFORMATION_REQUESTED,
      };
      expect(
        canApproveOrdinary(mockAccountantPrincipal, infoReqTask, mockBalancedJournal)
      ).toBe(false);
    });
  });

  describe("Senior Approval (canApproveSenior)", () => {
    const mockEscalatedSeniorTask: ReviewTaskResponse = {
      ...mockOrdinaryTask,
      owner_membership_id: mockSeniorPrincipal.membership_id,
      status: ReviewTaskStatus.ESCALATED,
      risk_class: ReviewRiskClass.SENIOR_REVIEW_REQUIRED,
      escalation_state: ReviewEscalationState.SENIOR_REVIEW,
    };

    it("allows assigned Senior Reviewer to approve escalated high-risk task", () => {
      expect(
        canApproveSenior(mockSeniorPrincipal, mockEscalatedSeniorTask, mockBalancedJournal)
      ).toBe(true);
    });

    it("denies if senior reviewer lacks permission", () => {
      const p = { ...mockSeniorPrincipal, permissions: [] };
      expect(canApproveSenior(p, mockEscalatedSeniorTask, mockBalancedJournal)).toBe(false);
    });

    it("denies Accountant from senior approval even if assigned", () => {
      const assignedAccountant = {
        ...mockAccountantPrincipal,
        membership_id: mockEscalatedSeniorTask.owner_membership_id,
      };
      expect(
        canApproveSenior(assignedAccountant, mockEscalatedSeniorTask, mockBalancedJournal)
      ).toBe(false);
    });

    it("denies Senior approval if task is not escalated", () => {
      const openSeniorTask = {
        ...mockEscalatedSeniorTask,
        status: ReviewTaskStatus.OPEN,
      };
      expect(
        canApproveSenior(mockSeniorPrincipal, openSeniorTask, mockBalancedJournal)
      ).toBe(false);
    });

    it("denies Senior approval if escalation state is not senior_review", () => {
      const wrongEscStateTask = {
        ...mockEscalatedSeniorTask,
        escalation_state: ReviewEscalationState.NONE,
      };
      expect(
        canApproveSenior(mockSeniorPrincipal, wrongEscStateTask, mockBalancedJournal)
      ).toBe(false);
    });

    it("denies Senior approval if risk class is not senior_review_required", () => {
      const ordinaryRiskTask = {
        ...mockEscalatedSeniorTask,
        risk_class: ReviewRiskClass.ORDINARY,
      };
      expect(
        canApproveSenior(mockSeniorPrincipal, ordinaryRiskTask, mockBalancedJournal)
      ).toBe(false);
    });

    it("denies Senior approval if journal is unbalanced or null", () => {
      expect(
        canApproveSenior(mockSeniorPrincipal, mockEscalatedSeniorTask, mockUnbalancedJournal)
      ).toBe(false);
      expect(
        canApproveSenior(mockSeniorPrincipal, mockEscalatedSeniorTask, null)
      ).toBe(false);
    });
  });

  describe("Escalation (canEscalate)", () => {
    it("allows owner accountant to escalate open task", () => {
      expect(canEscalate(mockAccountantPrincipal, mockOrdinaryTask)).toBe(true);
    });

    it("denies escalation if user lacks ESCALATE_TRANSACTION", () => {
      const p = { ...mockAccountantPrincipal, permissions: [] };
      expect(canEscalate(p, mockOrdinaryTask)).toBe(false);
    });

    it("denies escalation if task is already escalated or not open", () => {
      const escalatedTask = { ...mockOrdinaryTask, status: ReviewTaskStatus.ESCALATED };
      expect(canEscalate(mockAccountantPrincipal, escalatedTask)).toBe(false);
    });
  });

  describe("Request Information (canRequestInformation)", () => {
    it("allows owner to request info for open and escalated tasks", () => {
      expect(canRequestInformation(mockAccountantPrincipal, mockOrdinaryTask)).toBe(true);
      const escalatedTask = { ...mockOrdinaryTask, status: ReviewTaskStatus.ESCALATED };
      expect(canRequestInformation(mockAccountantPrincipal, escalatedTask)).toBe(true);
    });

    it("denies if user lacks REQUEST_INFORMATION", () => {
      const p = { ...mockAccountantPrincipal, permissions: [] };
      expect(canRequestInformation(p, mockOrdinaryTask)).toBe(false);
    });
  });

  describe("Rejection (canReject)", () => {
    it("allows owner to reject open, escalated, and info_requested tasks", () => {
      expect(canReject(mockAccountantPrincipal, mockOrdinaryTask)).toBe(true);
      const escalatedTask = { ...mockOrdinaryTask, status: ReviewTaskStatus.ESCALATED };
      expect(canReject(mockAccountantPrincipal, escalatedTask)).toBe(true);
      const infoReqTask = { ...mockOrdinaryTask, status: ReviewTaskStatus.INFORMATION_REQUESTED };
      expect(canReject(mockAccountantPrincipal, infoReqTask)).toBe(true);
    });

    it("denies non-owner from rejecting", () => {
      const nonOwner = { ...mockAccountantPrincipal, membership_id: "other" };
      expect(canReject(nonOwner, mockOrdinaryTask)).toBe(false);
    });
  });

  describe("Comments & Corrections Ownership Rules", () => {
    it("allows non-owner reviewer to add internal comment", () => {
      const nonOwner = { ...mockAccountantPrincipal, membership_id: "other" };
      expect(canComment(nonOwner, mockOrdinaryTask)).toBe(true);
    });

    it("denies comment if principal lacks permission or is not reviewer", () => {
      expect(canComment(mockAuditorPrincipal, mockOrdinaryTask)).toBe(false);
      const p = { ...mockAccountantPrincipal, permissions: [] };
      expect(canComment(p, mockOrdinaryTask)).toBe(false);
    });

    it("allows correction without review task ownership", () => {
      const nonOwner = { ...mockAccountantPrincipal, membership_id: "other" };
      expect(canCorrectField(nonOwner, mockOrdinaryTask)).toBe(true);
    });

    it("denies correction if principal lacks permission or is not reviewer", () => {
      expect(canCorrectField(mockAuditorPrincipal, mockOrdinaryTask)).toBe(false);
      const p = { ...mockAccountantPrincipal, permissions: [] };
      expect(canCorrectField(p, mockOrdinaryTask)).toBe(false);
    });

    it("suppresses corrections and comments for terminal tasks", () => {
      const approvedTask = {
        ...mockOrdinaryTask,
        status: ReviewTaskStatus.APPROVED,
      };
      expect(isTerminalTask(approvedTask)).toBe(true);
      expect(canComment(mockAccountantPrincipal, approvedTask)).toBe(false);
      expect(canCorrectField(mockAccountantPrincipal, approvedTask)).toBe(false);
    });
  });

  describe("Role Route & Workspace Isolation", () => {
    it("denies Firm Admin from viewing Review Workspace", () => {
      expect(canViewReviewWorkspace(mockFirmAdminPrincipal)).toBe(false);
    });

    it("denies Client Submitter from viewing Review Workspace", () => {
      expect(canViewReviewWorkspace(mockClientSubmitterPrincipal)).toBe(false);
    });

    it("allows Accountant, Senior, and Auditor to view Review Workspace", () => {
      expect(canViewReviewWorkspace(mockAccountantPrincipal)).toBe(true);
      expect(canViewReviewWorkspace(mockSeniorPrincipal)).toBe(true);
      expect(canViewReviewWorkspace(mockAuditorPrincipal)).toBe(true);
    });

    it("allows Client Submitter to view Client Portal", () => {
      expect(canViewClientPortal(mockClientSubmitterPrincipal)).toBe(true);
    });
  });
});
