import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { Header } from "../components/layout/Header";
import { Navbar } from "../components/layout/Navbar";
import { DisclaimerBanner } from "../components/layout/DisclaimerBanner";
import { AppShell } from "../components/layout/AppShell";
import { AuthProvider, useAuth } from "../lib/context/AuthContext";
import { ClientProvider, useClientContext } from "../lib/context/ClientContext";
import { Alert, Card } from "../components/ui/Alert";
import { Button } from "../components/ui/Button";
import { RiskBadge, StatusBadge } from "../components/ui/Badge";
import { ReviewRiskClass, ReviewTaskStatus, Role, ReviewOutcomeType } from "../types/roles";
import { TerminalBanner } from "../components/workspace/TerminalBanner";
import { FindingsList } from "../components/workspace/FindingsList";
import { SupplierMatchCard } from "../components/workspace/SupplierMatchCard";
import { RecommendationsCard } from "../components/workspace/RecommendationsCard";
import { SCENARIO_ORDINARY } from "../lib/mock/fixtures";
import { formatMoney } from "../lib/decimal/money";

vi.mock("next/navigation", () => ({
  usePathname: () => "/reviews",
  useRouter: () => ({ push: vi.fn() }),
}));

function ClientSelectorTestComponent() {
  const { activeClient, availableClients, setActiveClientId } = useClientContext();
  return (
    <div>
      <span data-testid="active-client">{activeClient.name}</span>
      <button onClick={() => setActiveClientId(availableClients[1].id)}>
        Switch Client
      </button>
    </div>
  );
}

function RoleSwitcherTestComponent({ targetRole }: { targetRole: Role }) {
  const { setRole } = useAuth();
  return (
    <div>
      <button onClick={() => setRole(targetRole)}>Switch to {targetRole}</button>
      <Navbar />
    </div>
  );
}

describe("Layout and Core UI Primitives", () => {
  it("renders Header with role switcher, mode toggle, and client selector", () => {
    render(
      <AuthProvider>
        <ClientProvider>
          <Header />
        </ClientProvider>
      </AuthProvider>
    );

    expect(screen.getByText("LedgerPilot AI")).toBeInTheDocument();
    expect(screen.getByText("Mock Demo")).toBeInTheDocument();
    expect(screen.getByText("Live API")).toBeInTheDocument();
    expect(screen.getByText(/Accountant/i)).toBeInTheDocument();
    expect(screen.getByText(/Senior/i)).toBeInTheDocument();
    expect(screen.getByText(/Submitter/i)).toBeInTheDocument();
  });

  it("renders Navbar for Firm Admin and Client Submitter roles", () => {
    const { rerender } = render(
      <AuthProvider>
        <RoleSwitcherTestComponent targetRole={Role.FIRM_ADMIN} />
      </AuthProvider>
    );
    fireEvent.click(screen.getByText(/Switch to firm_admin/i));
    expect(screen.getByText(/Firm Administration \(Phase 5 Review Access Not Granted\)/i)).toBeInTheDocument();

    rerender(
      <AuthProvider>
        <RoleSwitcherTestComponent targetRole={Role.CLIENT_SUBMITTER} />
      </AuthProvider>
    );
    fireEvent.click(screen.getByText(/Switch to client_submitter/i));
    expect(screen.getByText(/Client Information Portal/i)).toBeInTheDocument();
  });

  it("renders DisclaimerBanner with synthetic notice", () => {
    render(<DisclaimerBanner />);
    expect(screen.getByText(/Synthetic Accounting & Tax Configuration/i)).toBeInTheDocument();
    expect(screen.getByText(/SYN-TAX-06/i)).toBeInTheDocument();
  });

  it("renders AppShell wrapping children with footer notice", () => {
    render(
      <AuthProvider>
        <ClientProvider>
          <AppShell>
            <div>Test Child Content</div>
          </AppShell>
        </ClientProvider>
      </AuthProvider>
    );
    expect(screen.getByText("Test Child Content")).toBeInTheDocument();
    expect(screen.getByText(/AI Recommendations assist the accountant/i)).toBeInTheDocument();
  });

  it("renders Alert component with various severities", () => {
    const { rerender } = render(<Alert variant="error" title="Error Title">Error message</Alert>);
    expect(screen.getByText("Error Title")).toBeInTheDocument();
    expect(screen.getByText("Error message")).toBeInTheDocument();

    rerender(<Alert variant="warning" title="Warning Title">Warning message</Alert>);
    expect(screen.getByText("Warning Title")).toBeInTheDocument();

    rerender(<Alert variant="success" title="Success Title">Success message</Alert>);
    expect(screen.getByText("Success Title")).toBeInTheDocument();

    rerender(<Alert variant="info" title="Info Title">Info message</Alert>);
    expect(screen.getByText("Info Title")).toBeInTheDocument();
  });

  it("renders Card component with title and actions", () => {
    render(
      <Card title="Card Title" subtitle="Subtitle" action={<button>Action</button>}>
        <div>Card Content</div>
      </Card>
    );
    expect(screen.getByText("Card Title")).toBeInTheDocument();
    expect(screen.getByText("Subtitle")).toBeInTheDocument();
    expect(screen.getByText("Card Content")).toBeInTheDocument();
  });

  it("renders Button component with variant styles and loading state", () => {
    const handleClick = vi.fn();
    const { rerender } = render(
      <Button variant="primary" size="md" onClick={handleClick}>
        Click Me
      </Button>
    );
    const btn = screen.getByRole("button", { name: "Click Me" });
    fireEvent.click(btn);
    expect(handleClick).toHaveBeenCalled();

    rerender(<Button isLoading>Loading...</Button>);
    expect(screen.getByRole("button")).toBeDisabled();
  });

  it("renders RiskBadge and StatusBadge for all statuses and classes", () => {
    const { rerender } = render(<RiskBadge riskClass={ReviewRiskClass.ORDINARY} />);
    expect(screen.getByText(/Ordinary Review/i)).toBeInTheDocument();

    rerender(<RiskBadge riskClass={ReviewRiskClass.SENIOR_REVIEW_REQUIRED} />);
    expect(screen.getByText(/Senior Review Required/i)).toBeInTheDocument();

    rerender(<RiskBadge riskClass={ReviewRiskClass.BLOCKED} />);
    expect(screen.getByText(/Approval Blocked/i)).toBeInTheDocument();

    rerender(<RiskBadge riskClass="custom_unknown_risk" />);
    expect(screen.getByText("custom_unknown_risk")).toBeInTheDocument();

    rerender(<StatusBadge status={ReviewTaskStatus.OPEN} />);
    expect(screen.getByText("Open")).toBeInTheDocument();

    rerender(<StatusBadge status={ReviewTaskStatus.ESCALATED} />);
    expect(screen.getByText("Escalated")).toBeInTheDocument();

    rerender(<StatusBadge status={ReviewTaskStatus.INFORMATION_REQUESTED} />);
    expect(screen.getByText("Info Requested")).toBeInTheDocument();

    rerender(<StatusBadge status={ReviewTaskStatus.APPROVED} />);
    expect(screen.getByText("✓ Approved")).toBeInTheDocument();

    rerender(<StatusBadge status={ReviewTaskStatus.REJECTED} />);
    expect(screen.getByText("✕ Rejected")).toBeInTheDocument();

    rerender(<StatusBadge status="custom_unknown_status" />);
    expect(screen.getByText("custom_unknown_status")).toBeInTheDocument();
  });

  it("renders TerminalBanner for corrected_and_approved and rejected outcomes", () => {
    const correctedOutcome = {
      id: "out-corr",
      review_task_id: "task-01",
      actor_user_id: "user-acc",
      actor_membership_id: "mem-acc",
      outcome_type: ReviewOutcomeType.CORRECTED_AND_APPROVED,
      proposed_journal_id: "pj-01",
      source_correction_count: 2,
      reason: "Corrected subtotal and tax",
      request_id: "req-01",
      created_at: "2026-08-29T16:00:00Z",
    };

    const { rerender } = render(
      <TerminalBanner task={SCENARIO_ORDINARY.task} outcome={correctedOutcome} />
    );
    expect(
      screen.getByText(/Attributable Accounting Review Outcome: Corrected and Approved/i)
    ).toBeInTheDocument();

    const rejectedOutcome = {
      ...correctedOutcome,
      outcome_type: ReviewOutcomeType.REJECTED,
      reason: "Invalid supplier tax invoice",
    };
    rerender(<TerminalBanner task={SCENARIO_ORDINARY.task} outcome={rejectedOutcome} />);
    expect(
      screen.getByText(/Attributable Accounting Review Outcome: Rejected/i)
    ).toBeInTheDocument();
  });

  it("renders empty states for findings, recommendations, and supplier match", () => {
    const { rerender } = render(<FindingsList findings={[]} />);
    expect(screen.getByText(/No deterministic findings recorded/i)).toBeInTheDocument();

    rerender(<RecommendationsCard recommendations={[]} />);
    expect(screen.getByText(/No coding recommendations generated/i)).toBeInTheDocument();

    rerender(<SupplierMatchCard match={{ status: "no_match", candidates: [] }} />);
    expect(screen.getByText(/No supplier directory match candidates found/i)).toBeInTheDocument();
  });

  it("formats money helper with fallback strings", () => {
    expect(formatMoney(null)).toBe("MYR 0.00");
    expect(formatMoney("")).toBe("MYR 0.00");
    expect(formatMoney("-")).toBe("MYR 0.00");
    expect(formatMoney("invalid_amount")).toBe("MYR invalid_amount");
  });

  it("switches client context accurately", () => {
    render(
      <ClientProvider>
        <ClientSelectorTestComponent />
      </ClientProvider>
    );
    expect(screen.getByTestId("active-client")).toHaveTextContent("Alpha Trading Sdn Bhd [Demo]");
    fireEvent.click(screen.getByRole("button", { name: "Switch Client" }));
    expect(screen.getByTestId("active-client")).toHaveTextContent("Beta Logistics Bhd [Demo]");
  });
});
