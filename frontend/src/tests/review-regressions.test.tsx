import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { AuthProvider, useAuth } from "../lib/context/AuthContext";
import { validateContextResponse } from "../lib/api/context";
import { ApiError, getFriendlyErrorMessage } from "../lib/api/errors";
import { Role, Permission, ReviewTaskStatus, ReviewOutcomeType } from "../types/roles";
import { SCENARIO_ORDINARY } from "../lib/mock/fixtures";
import { mockDataStore } from "../lib/mock/mock-client";
import { StaleDecisionDialog } from "../components/dialogs/StaleDecisionDialog";
import { CorrectionDialog } from "../components/dialogs/CorrectionDialog";
import ClientSubmitterPortalPage from "../app/portal/[clientId]/documents/[documentId]/extractions/[extractionRunId]/decisions/[decisionRunId]/tasks/[reviewTaskId]/page";

const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  usePathname: () => "/portal",
  useRouter: () => ({ push: mockPush }),
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
    mockPush.mockReset();
  });

  afterEach(() => {
    global.fetch = originalFetch;
  });

  describe("1, 2, 3: Live Mode Fail-Closed & Runtime Schema Validation", () => {
    it("fails closed on network failure or 401/403 (principal is null)", async () => {
      global.fetch = vi.fn().mockRejectedValue(new Error("Network Error"));

      let inspectedAuth: ReturnType<typeof useAuth> | null = null;
      render(
        <AuthProvider>
          <AuthInspector onInspect={(auth) => (inspectedAuth = auth)} />
        </AuthProvider>
      );

      inspectedAuth!.setMode("live");
      await waitFor(() => {
        expect(inspectedAuth!.mode).toBe("live");
      });

      await waitFor(() => {
        expect(inspectedAuth!.connectionStatus).toBe("unavailable");
        expect(inspectedAuth!.principal).toBeNull();
        expect(inspectedAuth!.effectiveRole).toBeNull();
        expect(inspectedAuth!.effectivePrincipal).toBeNull();
      });
    });

    it("runtime validator rejects invalid context responses (unknown role, malformed perms, missing membership, invalid client IDs)", () => {
      // 1. Null / non-object
      expect(() => validateContextResponse(null)).toThrowError(/not an object/);
      expect(() => validateContextResponse("primitive")).toThrowError(/not an object/);

      // 2. Missing user_id
      expect(() =>
        validateContextResponse({
          firm_id: "f1",
          membership_id: "m1",
          role: "accountant",
          permissions: [],
          authorized_client_ids: [],
        })
      ).toThrowError(/Context missing valid user_id/);

      // 3. Missing firm_id
      expect(() =>
        validateContextResponse({
          user_id: "u1",
          membership_id: "m1",
          role: "accountant",
          permissions: [],
          authorized_client_ids: [],
        })
      ).toThrowError(/Context missing valid firm_id/);

      // 4. Missing membership_id
      expect(() =>
        validateContextResponse({
          user_id: "u1",
          firm_id: "f1",
          membership_id: "",
          role: "accountant",
          permissions: [],
          authorized_client_ids: [],
        })
      ).toThrowError(/Context missing valid membership_id/);

      // 5. Unknown or non-string role
      expect(() =>
        validateContextResponse({
          user_id: "u1",
          firm_id: "f1",
          membership_id: "m1",
          role: 123,
          permissions: [],
          authorized_client_ids: [],
        })
      ).toThrowError(/Unknown role in context/);

      expect(() =>
        validateContextResponse({
          user_id: "u1",
          firm_id: "f1",
          membership_id: "m1",
          role: "super_admin",
          permissions: [],
          authorized_client_ids: [],
        })
      ).toThrowError(/Unknown role in context/);

      // 6. Permissions not array or invalid items
      expect(() =>
        validateContextResponse({
          user_id: "u1",
          firm_id: "f1",
          membership_id: "m1",
          role: "accountant",
          permissions: "not-an-array",
          authorized_client_ids: [],
        })
      ).toThrowError(/permissions must be an array/);

      expect(() =>
        validateContextResponse({
          user_id: "u1",
          firm_id: "f1",
          membership_id: "m1",
          role: "accountant",
          permissions: [123],
          authorized_client_ids: [],
        })
      ).toThrowError(/Unknown permission in context/);

      expect(() =>
        validateContextResponse({
          user_id: "u1",
          firm_id: "f1",
          membership_id: "m1",
          role: "accountant",
          permissions: ["invalid_fake_permission"],
          authorized_client_ids: [],
        })
      ).toThrowError(/Unknown permission in context/);

      // 7. Invalid client ID collection
      expect(() =>
        validateContextResponse({
          user_id: "u1",
          firm_id: "f1",
          membership_id: "m1",
          role: "accountant",
          permissions: [],
          authorized_client_ids: "not-an-array",
        })
      ).toThrowError(/authorized_client_ids must be an array/);

      expect(() =>
        validateContextResponse({
          user_id: "u1",
          firm_id: "f1",
          membership_id: "m1",
          role: "accountant",
          permissions: [],
          authorized_client_ids: [123],
        })
      ).toThrowError(/Invalid client ID format/);
    });

    it("live mode sets connectionStatus to invalid_context when backend returns malformed payload", async () => {
      let inspectedAuth: ReturnType<typeof useAuth> | null = null;
      global.fetch = vi.fn().mockImplementation((url) => {
        if (url.includes("/health/live")) {
          return Promise.resolve({
            ok: true,
            headers: new Headers({ "content-type": "application/json" }),
            json: () => Promise.resolve({ status: "alive" }),
          });
        }
        // Return malformed context
        return Promise.resolve({
          ok: true,
          headers: new Headers({ "content-type": "application/json" }),
          json: () =>
            Promise.resolve({
              user_id: "u1",
              firm_id: "f1",
              membership_id: "m1",
              role: "unknown_fake_role",
              permissions: [],
              authorized_client_ids: [],
            }),
        });
      });

      render(
        <AuthProvider>
          <AuthInspector onInspect={(auth) => (inspectedAuth = auth)} />
        </AuthProvider>
      );

      inspectedAuth!.setMode("live");

      await waitFor(() => {
        expect(inspectedAuth!.connectionStatus).toBe("invalid_context");
        expect(inspectedAuth!.principal).toBeNull();
        expect(inspectedAuth!.effectiveRole).toBeNull();
      });
    });

    it("server-verified principal role overrides simulator selection in live mode", async () => {
      let inspectedAuth: ReturnType<typeof useAuth> | null = null;
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
      inspectedAuth!.setRole(Role.ACCOUNTANT);

      await waitFor(() => {
        expect(inspectedAuth!.role).toBe(Role.ACCOUNTANT); // Simulator selection
        expect(inspectedAuth!.effectiveRole).toBe(Role.SENIOR_REVIEWER); // Authoritative server role
        expect(inspectedAuth!.effectivePrincipal?.membership_id).toBe("m-server-senior");
      });
    });
  });

  describe("Portal Role & Granular Permission Guards", () => {
    const getMockParams = () =>
      Promise.resolve({
        clientId: SCENARIO_ORDINARY.lineage.clientId,
        documentId: SCENARIO_ORDINARY.lineage.documentId,
        extractionRunId: SCENARIO_ORDINARY.lineage.extractionRunId,
        decisionRunId: SCENARIO_ORDINARY.lineage.decisionRunId,
        reviewTaskId: SCENARIO_ORDINARY.lineage.reviewTaskId,
      });

    it("blocks Accountant, Senior Reviewer, Auditor, and Firm Admin from Client Portal", async () => {
      await React.act(async () => {
        render(
          <AuthProvider>
            <React.Suspense fallback={<div>Loading...</div>}>
              <ClientSubmitterPortalPage params={getMockParams()} />
            </React.Suspense>
          </AuthProvider>
        );
      });

      await waitFor(() => {
        expect(screen.getByText(/Restricted Submitter Access/i)).toBeInTheDocument();
      });
    });

    it("renders Permission Required if Client Submitter lacks VIEW_INFORMATION_REQUEST", async () => {
      let inspectedAuth: ReturnType<typeof useAuth> | null = null;
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
              user_id: "u-sub-limited",
              firm_id: "f-1",
              membership_id: "m-sub-limited",
              role: "client_submitter",
              permissions: ["upload_documents"], // Missing VIEW_INFORMATION_REQUEST!
              authorized_client_ids: ["c1"],
            }),
        });
      });

      await React.act(async () => {
        render(
          <AuthProvider>
            <AuthInspector onInspect={(auth) => (inspectedAuth = auth)} />
            <React.Suspense fallback={<div>Loading...</div>}>
              <ClientSubmitterPortalPage params={getMockParams()} />
            </React.Suspense>
          </AuthProvider>
        );
      });

      await React.act(async () => {
        inspectedAuth!.setMode("live");
      });

      await waitFor(() => {
        expect(screen.getByText(/Permission Required/i)).toBeInTheDocument();
        expect(screen.getByText("VIEW_INFORMATION_REQUEST")).toBeInTheDocument();
      });
    });

    it("disables response input if Client Submitter lacks RESPOND_TO_INFORMATION_REQUEST", async () => {
      let inspectedAuth: ReturnType<typeof useAuth> | null = null;
      global.fetch = vi.fn().mockImplementation((url) => {
        if (url.endsWith("/health/live") || url.includes("/health/live")) {
          return Promise.resolve({
            ok: true,
            headers: new Headers({ "content-type": "application/json" }),
            json: () => Promise.resolve({ status: "alive" }),
          });
        }
        if (url.endsWith("/context") || url.includes("/context")) {
          return Promise.resolve({
            ok: true,
            headers: new Headers({ "content-type": "application/json" }),
            json: () =>
              Promise.resolve({
                user_id: "u-sub-readonly",
                firm_id: "f-1",
                membership_id: "m-sub-readonly",
                role: "client_submitter",
                permissions: ["view_information_request"], // Holds view but missing respond
                authorized_client_ids: ["c1"],
              }),
          });
        }
        if (url.includes("/information-request")) {
          return Promise.resolve({
            ok: true,
            headers: new Headers({ "content-type": "application/json" }),
            json: () =>
              Promise.resolve({
                id: "c-req-1",
                review_task_id: "t1",
                author_user_id: "u-acc",
                author_membership_id: "m-acc",
                kind: "information_request",
                body: "Please confirm line item category.",
                request_id: "req-1",
                created_at: new Date().toISOString(),
              }),
          });
        }
        if (url.includes("/documents/")) {
          return Promise.resolve({
            ok: true,
            headers: new Headers({ "content-type": "application/json" }),
            json: () => Promise.resolve(SCENARIO_ORDINARY.document),
          });
        }
        return Promise.reject(new Error(`Unhandled URL: ${url}`));
      });

      await React.act(async () => {
        render(
          <AuthProvider>
            <AuthInspector onInspect={(auth) => (inspectedAuth = auth)} />
            <React.Suspense fallback={<div>Loading...</div>}>
              <ClientSubmitterPortalPage params={getMockParams()} />
            </React.Suspense>
          </AuthProvider>
        );
      });

      await React.act(async () => {
        inspectedAuth!.setMode("live");
      });

      await waitFor(() => {
        expect(screen.getByText("Please confirm line item category.")).toBeInTheDocument();
        expect(
          screen.getByText(/You hold permission to view this inquiry/i)
        ).toBeInTheDocument();
        expect(screen.getByText("RESPOND_TO_INFORMATION_REQUEST")).toBeInTheDocument();
      });

      const submitBtn = screen.getByRole("button", { name: /Submit Information Response/i });
      expect(submitBtn).toBeDisabled();
    });
  });

  describe("Fresh Decision Generation & Partial Failure Handling", () => {
    it("1. Decision creation failure creates no task and displays error", async () => {
      const handleGenerate = vi.fn().mockImplementation(async () => {
        throw new Error("Accounting decision engine execution failed.");
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
        expect(handleGenerate).toHaveBeenCalledWith(expect.any(Function), null);
        expect(
          screen.getByText("Accounting decision engine execution failed.")
        ).toBeInTheDocument();
      });
    });

    it("2 & 3 & 4: Task creation failure retains decision ID and retry reuses it without re-creating decision", async () => {
      let callCount = 0;
      let createdDecisionIdOnServer = "dec-run-fresh-888";

      const handleGenerate = vi.fn().mockImplementation(async (setStep, existingId) => {
        callCount++;
        if (callCount === 1) {
          // Step 1: Decision created, but Step 2 (Task) fails
          setStep("1/3: Decision created");
          const err = new Error("Review task persistence constraint violation.");
          (err as unknown as { createdDecisionId: string }).createdDecisionId = createdDecisionIdOnServer;
          throw err;
        } else {
          // Step 2: Retry using existingId
          expect(existingId).toBe(createdDecisionIdOnServer);
          setStep("2/3: Creating task for existing decision...");
          mockPush("/reviews/c1/documents/d1/extractions/e1/decisions/dec-run-fresh-888/tasks/t-new");
        }
      });

      render(
        <StaleDecisionDialog
          isOpen={true}
          onClose={() => {}}
          onGenerateFreshDecision={handleGenerate}
        />
      );

      // First attempt
      const btn = screen.getByRole("button", { name: /Generate Fresh Accounting Decision/i });
      fireEvent.click(btn);

      // Verify partial failure alert displays retained decision ID
      await waitFor(() => {
        expect(screen.getByText("Fresh Decision Run Created:")).toBeInTheDocument();
        expect(screen.getByText("dec-run-fresh-888")).toBeInTheDocument();
        expect(
          screen.getByText("Review task persistence constraint violation.")
        ).toBeInTheDocument();
      });

      // Button updates to Retry Creating Review Task
      const retryBtn = screen.getByRole("button", { name: /Retry Creating Review Task/i });
      fireEvent.click(retryBtn);

      await waitFor(() => {
        expect(handleGenerate).toHaveBeenCalledTimes(2);
        expect(mockPush).toHaveBeenCalledWith(
          "/reviews/c1/documents/d1/extractions/e1/decisions/dec-run-fresh-888/tasks/t-new"
        );
      });
    });

    it("5: Full success creates exactly 1 decision and 1 task and redirects", async () => {
      const handleGenerate = vi.fn().mockImplementation(async (setStep) => {
        setStep("1/3: Generating decision...");
        setStep("2/3: Creating task...");
        setStep("3/3: Redirecting...");
        mockPush("/reviews/c1/documents/d1/extractions/e1/decisions/dec-1/tasks/t-1");
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
        expect(handleGenerate).toHaveBeenCalledTimes(1);
        expect(mockPush).toHaveBeenCalledWith(
          "/reviews/c1/documents/d1/extractions/e1/decisions/dec-1/tasks/t-1"
        );
      });
    });
  });

  describe("Stale Invariants & Approved Record Locking", () => {
    it("pre-decision correction does NOT make initial review workspace stale and allows approval", () => {
      expect(SCENARIO_ORDINARY.extraction.fields.some((f) => f.corrected)).toBe(true);

      const store = mockDataStore;
      const lineage = SCENARIO_ORDINARY.lineage;

      const res = store.approve(lineage, "Approved after prior correction");
      expect(res.task.status).toBe(ReviewTaskStatus.APPROVED);
      expect(res.outcome.outcome_type).toBe(ReviewOutcomeType.CORRECTED_AND_APPROVED);
      expect(res.outcome.source_correction_count).toBe(1);
    });

    it("performing a correction in the current session marks decision stale", () => {
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

    it("supports approved_record_locked error message in error normalizer and correction dialog", async () => {
      const lockedErr = new ApiError(409, "approved_record_locked", "");
      const friendlyMsg = getFriendlyErrorMessage(lockedErr);
      expect(friendlyMsg).toContain("Approved accounting evidence is locked");
      expect(friendlyMsg).toContain(
        "Changes require a controlled correction, reversal, or supersession workflow"
      );

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
  });
});
