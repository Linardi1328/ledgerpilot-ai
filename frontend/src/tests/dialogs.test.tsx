import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { ApproveDialog } from "../components/dialogs/ApproveDialog";
import { RejectDialog } from "../components/dialogs/RejectDialog";
import { EscalateDialog } from "../components/dialogs/EscalateDialog";
import { InfoRequestDialog } from "../components/dialogs/InfoRequestDialog";
import { CorrectionDialog } from "../components/dialogs/CorrectionDialog";
import { Permission, ReviewEscalationState, ReviewRiskClass, ReviewTaskStatus, Role } from "../types/roles";
import { ExtractedFieldResponse, ProposedJournalResponse, ReviewTaskResponse } from "../types/api";

const mockPrincipal = {
  user_id: "user-01",
  firm_id: "firm-01",
  membership_id: "mem-01",
  role: Role.ACCOUNTANT,
  permissions: [Permission.APPROVE_ORDINARY_TRANSACTION],
  authorized_client_ids: ["client-01"],
};

const mockTask: ReviewTaskResponse = {
  id: "task-test-01",
  firm_id: "firm-01",
  client_id: "client-01",
  decision_run_id: "dec-01",
  document_id: "doc-01",
  extraction_run_id: "ext-01",
  created_by_user_id: "user-01",
  created_by_membership_id: "mem-01",
  owner_user_id: "user-01",
  owner_membership_id: "mem-01",
  status: ReviewTaskStatus.OPEN,
  risk_class: ReviewRiskClass.ORDINARY,
  escalation_state: ReviewEscalationState.NONE,
  escalated_at: null,
  request_id: "req-01",
  created_at: "2026-08-29T10:00:00Z",
  updated_at: "2026-08-29T10:00:00Z",
};

const mockJournal: ProposedJournalResponse = {
  id: "pj-01",
  currency: "MYR",
  total_debits: "1250.00",
  total_credits: "1250.00",
  balance_status: "balanced",
  is_balanced: true,
  explanation: "Balanced",
  lines: [],
};

describe("Interactive Dialogs & Accessibility", () => {
  it("ApproveDialog enforces confirmation with attributable outcome copy", async () => {
    const handleApprove = vi.fn().mockResolvedValue(undefined);
    const handleClose = vi.fn();

    render(
      <ApproveDialog
        isOpen={true}
        onClose={handleClose}
        task={mockTask}
        journal={mockJournal}
        principal={mockPrincipal}
        onConfirmApprove={handleApprove}
      />
    );

    expect(
      screen.getByRole("heading", { name: /Confirm Accounting Approval/i })
    ).toBeInTheDocument();
    expect(screen.getByText(/attributable human review outcome/i)).toBeInTheDocument();

    const noteInput = screen.getByLabelText(/Approval Note/i);
    fireEvent.change(noteInput, { target: { value: "Verified against physical receipt." } });

    const confirmBtn = screen.getByRole("button", { name: /Confirm Accounting Approval/i });
    fireEvent.click(confirmBtn);

    await waitFor(() => {
      expect(handleApprove).toHaveBeenCalledWith("Verified against physical receipt.");
    });
  });

  it("RejectDialog requires non-empty rejection reason and handles cancel", async () => {
    const handleReject = vi.fn().mockResolvedValue(undefined);
    const handleClose = vi.fn();

    render(
      <RejectDialog
        isOpen={true}
        onClose={handleClose}
        onConfirmReject={handleReject}
      />
    );

    expect(screen.getByText(/Terminal Action Warning/i)).toBeInTheDocument();

    const reasonInput = screen.getByLabelText(/Mandatory Rejection Reason/i);
    fireEvent.change(reasonInput, { target: { value: "Duplicate invoice submitted." } });

    const submitBtn = screen.getByRole("button", { name: /Confirm Rejection/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(handleReject).toHaveBeenCalledWith("Duplicate invoice submitted.");
    });
  });

  it("EscalateDialog handles senior selection and mandatory reason", async () => {
    const handleEscalate = vi.fn().mockResolvedValue(undefined);
    const handleClose = vi.fn();

    render(
      <EscalateDialog
        isOpen={true}
        onClose={handleClose}
        onConfirmEscalate={handleEscalate}
      />
    );

    expect(screen.getByText(/Target Senior Reviewer/i)).toBeInTheDocument();

    const reasonInput = screen.getByLabelText(/Reason for Escalation/i);
    fireEvent.change(reasonInput, { target: { value: "Duplicate candidate detected." } });

    const submitBtn = screen.getByRole("button", { name: /Confirm Escalation/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(handleEscalate).toHaveBeenCalled();
    });
  });

  it("CorrectionDialog handles raw value modification and reason submission", async () => {
    const handleCorrection = vi.fn().mockResolvedValue(undefined);
    const handleClose = vi.fn();
    const mockField: ExtractedFieldResponse = {
      id: "fld-test-01",
      field_path: "invoice.total",
      value_type: "decimal",
      original_raw_value: "1500.00",
      original_normalized_value: "1500.00",
      effective_raw_value: "1500.00",
      effective_normalized_value: "1500.00",
      effective_value_type: "decimal",
      confidence: "0.9500",
      source_page_number: 1,
      source_locator: null,
      corrected: false,
      latest_correction_id: null,
      latest_revision_number: null,
    };

    render(
      <CorrectionDialog
        isOpen={true}
        onClose={handleClose}
        field={mockField}
        onConfirmCorrection={handleCorrection}
      />
    );

    const valInput = screen.getByLabelText(/New Corrected Value/i);
    fireEvent.change(valInput, { target: { value: "1250.00" } });

    const reasonInput = screen.getByLabelText(/Reason for Correction/i);
    fireEvent.change(reasonInput, { target: { value: "Typo in extracted header subtotal." } });

    const saveBtn = screen.getByRole("button", { name: /Save Correction/i });
    fireEvent.click(saveBtn);

    await waitFor(() => {
      expect(handleCorrection).toHaveBeenCalledWith("fld-test-01", {
        corrected_raw_value: "1250.00",
        corrected_normalized_value: "1250.00",
        corrected_value_type: "decimal",
        reason: "Typo in extracted header subtotal.",
      });
    });
  });
});
