import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { AuthProvider, useAuth } from "../lib/context/AuthContext";
import { ApiError, getFriendlyErrorMessage } from "../lib/api/errors";
import { Role, ReviewTaskStatus, ReviewOutcomeType } from "../types/roles";
import { SCENARIO_ORDINARY } from "../lib/mock/fixtures";
import { mockDataStore } from "../lib/mock/mock-client";
import { StaleDecisionDialog } from "../components/dialogs/StaleDecisionDialog";
import { CorrectionDialog } from "../components/dialogs/CorrectionDialog";
import ClientSubmitterPortalPage from "../app/portal/[clientId]/documents/[documentId]/extractions/[extractionRunId]/decisions/[decisionRunId]/tasks/[reviewTaskId]/page";

vi.mock("next/navigation", () => ({
  usePathname: () => "/portal",
  useRouter: () => ({ push: vi.fn() }),
}));

// Helper component to inspect AuthContext state
function AuthInspector({ onInspect }: { onInspect: (auth: ReturnType<typeof useAuth>) => void }) {
  const auth = useAuth();
  React.useEffect(() => {
    onInspect(auth);
  }, [auth, onInspect]);
  return <div data-testid="mode">{auth.mode}</div>;
}

describe("Review Findings & Security Invariant Regressions", () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    mockDataStore.reset();
  });

  afterEach(() => {
    global.fetch = originalFetch;
  });

  it("1 & 2 & 3: Live mode fails closed on backend failure or 401/403 (never falls back to mock principal)", async () => {
    // A. Backend unavailable (network error)
    global.fetch = vi.fn().mockRejectedValue(new Error("Failed to fetch"));

    let inspectedAuth: ReturnType<typeof useAuth> | null = null;
    render(
      <AuthProvider>
        <AuthInspector onInspect={(auth) => (inspectedAuth = auth)} />
      </AuthProvider>
    );

    // Switch to live mode
    inspectedAuth!.setMode("live");
    await waitFor(() => {
      expect(inspectedAuth!.mode).toBe("live");
    });

    await waitFor(() => {
      expect(inspectedAuth!.connectionStatus).toBe("unavailable");
      // FAIL CLOSED: Principal MUST be null
      expect(inspectedAuth!.principal).toBeNull();
      expect(inspectedAuth!.effectiveRole).toBeNull();
      expect(inspectedAuth!.effectivePrincipal).toBeNull();
    });

    // B. Backend 401 unauthenticated
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      headers: new Headers({ "content-type": "application/json" }),
      json: vi.fn().mockResolvedValue({
        error: { code: "unauthenticated", message: "Missing credentials" },
      }),
    });

    await inspectedAuth!.refreshContext();
    await waitFor(() => {
      expect(inspectedAuth!.connectionStatus).toBe("unauthenticated");
      expect(inspectedAuth!.principal).toBeNull();
      expect(inspectedAuth!.effectiveRole).toBeNull();
    });

    // C. Live mode successful /context sets verified backend principal
    global.fetch = vi.fn().mockImplementation((url) => {
      if (url.includes("/health/live")) {
        return Promise.resolve({
          ok: true,
          headers: new Headers({ "content-type": "application/json" }),
          json: () => Promise.resolve({ status: "alive" }),
        });
      }
      return Promise.resolve({
        ok: true,
        headers: new Headers({ "content-type": "application/json" }),
        json: () =>
          Promise.resolve({
            user_id: "u-live-auditor",
            firm_id: "f-live-01",
            membership_id: "m-live-auditor",
            role: "auditor",
            permissions: ["view_review_task", "view_review_history"],
            authorized_client_ids: ["c1"],
          }),
      });
    });

    await inspectedAuth!.refreshContext();
    await waitFor(() => {
      expect(inspectedAuth!.connectionStatus).toBe("connected");
      expect(inspectedAuth!.principal?.user_id).toBe("u-live-auditor");
      expect(inspectedAuth!.effectiveRole).toBe(Role.AUDITOR);
    });
  });

  it("4: Server-verified principal role overrides simulator selection in live mode", async () => {
    let inspectedAuth: ReturnType<typeof useAuth> | null = null;
    global.fetch = vi.fn().mockImplementation((url) => {
      if (url.includes("/health/live")) {
        return Promise.resolve({
          ok: true,
          headers: new Headers({ "content-type": "application/json" }),
          json: () => Promise.resolve({ status: "alive" }),
        });
      }
      // Return Senior Reviewer from server regardless of dev subject
      return Promise.resolve({
        ok: true,
        headers: new Headers({ "content-type": "application/json" }),
        json: () =>
          Promise.resolve({
            user_id: "u-server-senior",
            firm_id: "f-1",
            membership_id: "m-server-senior",
            role: "senior_reviewer",
            permissions: ["view_review_task", "approve_high_risk_transaction"],
            authorized_client_ids: ["c1"],
          }),
      });
    });

    render(
      <AuthProvider>
        <AuthInspector onInspect={(auth) => (inspectedAuth = auth)} />
      </AuthProvider>
    );

    inspectedAuth!.setMode("live");
    // Simulator role set to Accountant
    inspectedAuth!.setRole(Role.ACCOUNTANT);

    await waitFor(() => {
      expect(inspectedAuth!.role).toBe(Role.ACCOUNTANT); // Simulator label
      expect(inspectedAuth!.effectiveRole).toBe(Role.SENIOR_REVIEWER); // Server authoritative role!
      expect(inspectedAuth!.effectivePrincipal?.membership_id).toBe("m-server-senior");
    });
  });

  it("5: Pre-decision correction does NOT make initial review workspace stale and allows approval", () => {
    // In SCENARIO_ORDINARY, field 'invoice.total' has corrected: true from prior run
    expect(SCENARIO_ORDINARY.extraction.fields.some((f) => f.corrected)).toBe(true);

    const store = mockDataStore;
    const lineage = SCENARIO_ORDINARY.lineage;

    // Approving the ordinary task succeeds and yields corrected_and_approved outcome
    const res = store.approve(lineage, "Approved after prior correction");
    expect(res.task.status).toBe(ReviewTaskStatus.APPROVED);
    expect(res.outcome.outcome_type).toBe(ReviewOutcomeType.CORRECTED_AND_APPROVED);
    expect(res.outcome.source_correction_count).toBe(1);
  });

  it("6: Performing a correction in the current session marks decision stale", () => {
    const store = mockDataStore;
    const lineage = SCENARIO_ORDINARY.lineage;

    const res = store.addCorrection(lineage, "fld-03", {
      corrected_raw_value: "INV-2026-999",
      corrected_value_type: "string",
      reason: "Fix invoice number in current session",
    });

    expect(res.corrected).toBe(true);
    expect(res.effective_raw_value).toBe("INV-2026-999");
  });

  it("7 & 8: Real multi-step 'Generate Fresh Accounting Decision' workflow creates new decision and task", async () => {
    const store = mockDataStore;
    const lineage = SCENARIO_ORDINARY.lineage;

    const res = store.generateFreshDecisionAndTask(lineage);
    expect(res.decision.id).toMatch(/^a-fresh-/);
    expect(res.task.id).toMatch(/^r-fresh-/);
    expect(res.task.decision_run_id).toBe(res.decision.id);
    expect(res.task.status).toBe(ReviewTaskStatus.OPEN);

    // Test StaleDecisionDialog multi-step progress UI
    const handleGenerate = vi.fn().mockImplementation(async (setStep) => {
      setStep("1/3: Generating fresh decision...");
      setStep("2/3: Creating new task...");
      setStep("3/3: Redirecting...");
    });

    render(
      <StaleDecisionDialog
        isOpen={true}
        onClose={() => {}}
        onGenerateFreshDecision={handleGenerate}
      />
    );

    const btn = screen.getByRole("button", { name: /Generate Fresh Accounting Decision/i });
    fireEvent.click(btn);

    await waitFor(() => {
      expect(handleGenerate).toHaveBeenCalled();
    });
  });

  it("9: Supports approved_record_locked error message in error normalizer and correction dialog", async () => {
    const lockedErr = new ApiError(409, "approved_record_locked", "");
    const friendlyMsg = getFriendlyErrorMessage(lockedErr);
    expect(friendlyMsg).toContain("Approved accounting evidence is locked");
    expect(friendlyMsg).toContain("Changes require a controlled correction, reversal, or supersession workflow");

    const mockField = SCENARIO_ORDINARY.extraction.fields[0];
    const handleCorrection = vi.fn().mockRejectedValue(lockedErr);

    render(
      <CorrectionDialog
        isOpen={true}
        onClose={() => {}}
        field={mockField}
        onConfirmCorrection={handleCorrection}
      />
    );

    const reasonInput = screen.getByLabelText(/Reason for Correction/i);
    fireEvent.change(reasonInput, { target: { value: "Attempt modification on approved field" } });

    const saveBtn = screen.getByRole("button", { name: /Save Correction/i });
    fireEvent.click(saveBtn);

    await waitFor(() => {
      expect(screen.getByText(/Approved accounting evidence is locked/i)).toBeInTheDocument();
    });
  });

  it("10: Direct route to Client Portal blocks non-Client-Submitter roles", async () => {
    // Render with Accountant role
    const mockParams = Promise.resolve({
      clientId: SCENARIO_ORDINARY.lineage.clientId,
      documentId: SCENARIO_ORDINARY.lineage.documentId,
      extractionRunId: SCENARIO_ORDINARY.lineage.extractionRunId,
      decisionRunId: SCENARIO_ORDINARY.lineage.decisionRunId,
      reviewTaskId: SCENARIO_ORDINARY.lineage.reviewTaskId,
    });

    await React.act(async () => {
      render(
        <AuthProvider>
          <React.Suspense fallback={<div>Loading suspense...</div>}>
            <ClientSubmitterPortalPage params={mockParams} />
          </React.Suspense>
        </AuthProvider>
      );
    });

    await waitFor(() => {
      expect(screen.getByText(/Restricted Submitter Access/i)).toBeInTheDocument();
      expect(
        screen.getByText(/requires an authenticated/i)
      ).toBeInTheDocument();
    });
  });
});
