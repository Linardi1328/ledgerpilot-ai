import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { ActionBar } from "../components/workspace/ActionBar";
import { CommentsFeed } from "../components/workspace/CommentsFeed";
import { EvidenceTable } from "../components/workspace/EvidenceTable";
import { RiskStatusBanner } from "../components/workspace/RiskStatusBanner";
import { LineageHeader } from "../components/workspace/LineageHeader";
import { AuditTimeline } from "../components/workspace/AuditTimeline";
import { InfoRequestDialog } from "../components/dialogs/InfoRequestDialog";
import { StaleDecisionDialog } from "../components/dialogs/StaleDecisionDialog";
import { SCENARIO_ORDINARY, SCENARIO_BLOCKED, SCENARIO_SENIOR } from "../lib/mock/fixtures";
import { Permission, ReviewRiskClass, ReviewTaskStatus, Role } from "../types/roles";

const mockAccountantPrincipal = {
  user_id: SCENARIO_ORDINARY.task.owner_user_id,
  firm_id: SCENARIO_ORDINARY.task.firm_id,
  membership_id: SCENARIO_ORDINARY.task.owner_membership_id,
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
  authorized_client_ids: [SCENARIO_ORDINARY.task.client_id],
};

const mockSeniorPrincipal = {
  user_id: SCENARIO_SENIOR.task.owner_user_id,
  firm_id: SCENARIO_SENIOR.task.firm_id,
  membership_id: SCENARIO_SENIOR.task.owner_membership_id,
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
  authorized_client_ids: [SCENARIO_SENIOR.task.client_id],
};

describe("Extended Workspace Components & Handlers", () => {
  it("renders LineageHeader with document filename and SHA-256 slice", () => {
    render(
      <LineageHeader
        lineage={SCENARIO_ORDINARY.lineage}
        submittedFilename="INV-2026-104.pdf"
        sha256="8f4a21e49b8a3e71d3c52a06bfec349a1d56e927c34b2203ef18037190d72c91"
      />
    );
    expect(screen.getByText("INV-2026-104.pdf")).toBeInTheDocument();
    expect(screen.getByText(/8f4a21e49b8a/i)).toBeInTheDocument();
  });

  it("renders RiskStatusBanner with correct risk class title and owner", () => {
    const { rerender } = render(<RiskStatusBanner task={SCENARIO_ORDINARY.task} />);
    expect(screen.getByText("ORDINARY REVIEW")).toBeInTheDocument();

    rerender(<RiskStatusBanner task={SCENARIO_BLOCKED.task} />);
    expect(screen.getByText("APPROVAL BLOCKED BY CONTROLS")).toBeInTheDocument();

    rerender(<RiskStatusBanner task={SCENARIO_SENIOR.task} />);
    expect(screen.getByText("SENIOR REVIEW REQUIRED")).toBeInTheDocument();

    const infoReqTask = { ...SCENARIO_ORDINARY.task, status: ReviewTaskStatus.INFORMATION_REQUESTED };
    rerender(<RiskStatusBanner task={infoReqTask} />);
    expect(screen.getByText("INFORMATION REQUESTED")).toBeInTheDocument();
  });

  it("renders EvidenceTable and triggers correction modal opener", () => {
    const handleOpenCorrection = vi.fn();
    render(
      <EvidenceTable
        fields={SCENARIO_ORDINARY.extraction.fields}
        canCorrect={true}
        onOpenCorrection={handleOpenCorrection}
      />
    );
    expect(screen.getByText("supplier.name")).toBeInTheDocument();
    expect(screen.getByText("Office Supplies Direct Sdn Bhd")).toBeInTheDocument();

    const editBtns = screen.getAllByTitle(/Correct extracted field/i);
    expect(editBtns.length).toBeGreaterThan(0);
    fireEvent.click(editBtns[0]);
    expect(handleOpenCorrection).toHaveBeenCalled();
  });

  it("renders CommentsFeed and posts a comment", async () => {
    const handleAddComment = vi.fn().mockResolvedValue(undefined);
    render(
      <CommentsFeed
        comments={SCENARIO_ORDINARY.history.comments}
        canAddComment={true}
        onAddComment={handleAddComment}
      />
    );

    expect(screen.getByText(/Verified against supplier physical receipt/i)).toBeInTheDocument();

    const input = screen.getByLabelText(/Internal Review Note/i);
    fireEvent.change(input, { target: { value: "Followed up with supplier." } });

    const postBtn = screen.getByRole("button", { name: /Post/i });
    fireEvent.click(postBtn);

    await waitFor(() => {
      expect(handleAddComment).toHaveBeenCalledWith("Followed up with supplier.");
    });
  });

  it("renders AuditTimeline with event stream and metadata toggle", () => {
    render(<AuditTimeline events={SCENARIO_ORDINARY.history.audit_events} />);
    expect(screen.getByText("review_task_created")).toBeInTheDocument();
    expect(screen.getByText(/Inspect Metadata/i)).toBeInTheDocument();
    fireEvent.click(screen.getByText(/Inspect Metadata/i));
    expect(screen.getByText(/initial_risk/i)).toBeInTheDocument();
  });

  it("renders ActionBar and tests all disabled tooltip branches", () => {
    const handleApprove = vi.fn();
    const handleEscalate = vi.fn();
    const handleInfoReq = vi.fn();
    const handleReject = vi.fn();

    // 1. Ordinary active
    const { rerender } = render(
      <ActionBar
        task={SCENARIO_ORDINARY.task}
        journal={SCENARIO_ORDINARY.decision.proposed_journal}
        principal={mockAccountantPrincipal}
        onOpenApprove={handleApprove}
        onOpenEscalate={handleEscalate}
        onOpenInfoRequest={handleInfoReq}
        onOpenReject={handleReject}
      />
    );

    const approveBtn = screen.getByRole("button", { name: /Confirm & Authorize Approval/i });
    expect(approveBtn).toBeEnabled();
    fireEvent.click(approveBtn);
    expect(handleApprove).toHaveBeenCalled();

    // 2. Senior active
    rerender(
      <ActionBar
        task={SCENARIO_SENIOR.task}
        journal={SCENARIO_SENIOR.decision.proposed_journal}
        principal={mockSeniorPrincipal}
        onOpenApprove={handleApprove}
        onOpenEscalate={handleEscalate}
        onOpenInfoRequest={handleInfoReq}
        onOpenReject={handleReject}
      />
    );
    const seniorApproveBtn = screen.getByRole("button", { name: /Authorize Senior Approval/i });
    expect(seniorApproveBtn).toBeEnabled();

    // 3. Stale decision branch
    rerender(
      <ActionBar
        task={SCENARIO_ORDINARY.task}
        journal={SCENARIO_ORDINARY.decision.proposed_journal}
        principal={mockAccountantPrincipal}
        isStale={true}
        onOpenApprove={handleApprove}
        onOpenEscalate={handleEscalate}
        onOpenInfoRequest={handleInfoReq}
        onOpenReject={handleReject}
      />
    );
    expect(screen.getByRole("button", { name: /Confirm & Authorize Approval/i })).toBeDisabled();

    // 4. Blocked branch
    rerender(
      <ActionBar
        task={SCENARIO_BLOCKED.task}
        journal={SCENARIO_BLOCKED.decision.proposed_journal}
        principal={mockAccountantPrincipal}
        onOpenApprove={handleApprove}
        onOpenEscalate={handleEscalate}
        onOpenInfoRequest={handleInfoReq}
        onOpenReject={handleReject}
      />
    );
    expect(screen.getByRole("button", { name: /Confirm & Authorize Approval/i })).toBeDisabled();

    // 5. Senior risk viewed by Accountant branch
    rerender(
      <ActionBar
        task={SCENARIO_SENIOR.task}
        journal={SCENARIO_SENIOR.decision.proposed_journal}
        principal={mockAccountantPrincipal}
        onOpenApprove={handleApprove}
        onOpenEscalate={handleEscalate}
        onOpenInfoRequest={handleInfoReq}
        onOpenReject={handleReject}
      />
    );
    expect(screen.getByRole("button", { name: /Confirm & Authorize Approval/i })).toBeDisabled();

    // 6. Information requested branch
    const infoReqTask = { ...SCENARIO_ORDINARY.task, status: ReviewTaskStatus.INFORMATION_REQUESTED };
    rerender(
      <ActionBar
        task={infoReqTask}
        journal={SCENARIO_ORDINARY.decision.proposed_journal}
        principal={mockAccountantPrincipal}
        onOpenApprove={handleApprove}
        onOpenEscalate={handleEscalate}
        onOpenInfoRequest={handleInfoReq}
        onOpenReject={handleReject}
      />
    );
    expect(screen.getByRole("button", { name: /Confirm & Authorize Approval/i })).toBeDisabled();

    // 7. Non-owner branch
    const nonOwner = { ...mockAccountantPrincipal, membership_id: "other" };
    rerender(
      <ActionBar
        task={SCENARIO_ORDINARY.task}
        journal={SCENARIO_ORDINARY.decision.proposed_journal}
        principal={nonOwner}
        onOpenApprove={handleApprove}
        onOpenEscalate={handleEscalate}
        onOpenInfoRequest={handleInfoReq}
        onOpenReject={handleReject}
      />
    );
    expect(screen.getByRole("button", { name: /Confirm & Authorize Approval/i })).toBeDisabled();
  });

  it("handles InfoRequestDialog submit", async () => {
    const handleConfirm = vi.fn().mockResolvedValue(undefined);
    const handleClose = vi.fn();

    render(
      <InfoRequestDialog
        isOpen={true}
        onClose={handleClose}
        onConfirmRequest={handleConfirm}
      />
    );

    const questionInput = screen.getByLabelText(/Question for Submitter/i);
    fireEvent.change(questionInput, { target: { value: "Is this purchase tax exempt?" } });

    const sendBtn = screen.getByRole("button", { name: /Send Request to Client/i });
    fireEvent.click(sendBtn);

    await waitFor(() => {
      expect(handleConfirm).toHaveBeenCalledWith("Is this purchase tax exempt?");
    });
  });

  it("handles StaleDecisionDialog generate fresh decision", async () => {
    const handleRegen = vi.fn().mockResolvedValue(undefined);
    const handleClose = vi.fn();

    render(
      <StaleDecisionDialog
        isOpen={true}
        onClose={handleClose}
        onGenerateFreshDecision={handleRegen}
      />
    );

    const regenBtn = screen.getByRole("button", { name: /Generate Fresh Accounting Decision/i });
    fireEvent.click(regenBtn);

    await waitFor(() => {
      expect(handleRegen).toHaveBeenCalled();
    });
  });
});
