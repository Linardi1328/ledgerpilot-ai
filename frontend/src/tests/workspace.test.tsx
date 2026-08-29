import React from "react";
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { JournalTable } from "../components/workspace/JournalTable";
import { FindingsList } from "../components/workspace/FindingsList";
import { SupplierMatchCard } from "../components/workspace/SupplierMatchCard";
import { DuplicateCard } from "../components/workspace/DuplicateCard";
import { RecommendationsCard } from "../components/workspace/RecommendationsCard";
import { TerminalBanner } from "../components/workspace/TerminalBanner";
import {
  SCENARIO_BLOCKED,
  SCENARIO_ORDINARY,
  SCENARIO_SENIOR,
} from "../lib/mock/fixtures";
import { ReviewOutcomeType } from "../types/roles";

describe("Workspace Components", () => {
  it("renders balanced Proposed Journal table with exact decimal totals", () => {
    render(<JournalTable journal={SCENARIO_ORDINARY.decision.proposed_journal} />);
    expect(screen.getByText(/BALANCED \(Server Authoritative\)/i)).toBeInTheDocument();
    expect(screen.getByText("SYN-6000-010 Printing & Stationery")).toBeInTheDocument();
    expect(screen.getByText("1,179.25")).toBeInTheDocument();
    expect(screen.getAllByText("1,250.00").length).toBeGreaterThanOrEqual(1);
  });

  it("renders unbalanced warning banner for unbalanced journal", () => {
    render(<JournalTable journal={SCENARIO_BLOCKED.decision.proposed_journal} />);
    expect(screen.getByText(/UNBALANCED \(Approval Blocked\)/i)).toBeInTheDocument();
    expect(
      screen.getByText(/Deterministic Control Failure: Unbalanced Proposed Journal/i)
    ).toBeInTheDocument();
  });

  it("renders deterministic findings with error badges and evidence toggle", () => {
    render(<FindingsList findings={SCENARIO_BLOCKED.decision.findings} />);
    expect(screen.getByText("unbalanced_journal")).toBeInTheDocument();
    expect(screen.getByText(/Total debits \(3,500.00\) do not equal total credits/i)).toBeInTheDocument();
  });

  it("renders suggested supplier match card with confidence percentage", () => {
    render(<SupplierMatchCard match={SCENARIO_ORDINARY.decision.supplier_match} />);
    expect(screen.getByText("Office Supplies Direct Sdn Bhd")).toBeInTheDocument();
    expect(screen.getByText("94.5% Confidence")).toBeInTheDocument();
    expect(screen.getByText(/Suggested Supplier Match/i)).toBeInTheDocument();
  });

  it("renders duplicate candidate warning card for senior review required", () => {
    render(<DuplicateCard candidates={SCENARIO_SENIOR.decision.duplicate_candidates} />);
    expect(screen.getByText(/Possible Duplicate Detection/i)).toBeInTheDocument();
    expect(screen.getByText(/Senior Review Required Trigger/i)).toBeInTheDocument();
    expect(screen.getByText(/Same supplier, same invoice number/i)).toBeInTheDocument();
  });

  it("renders accounting coding recommendations with synthetic lineage", () => {
    render(
      <RecommendationsCard
        recommendations={SCENARIO_ORDINARY.decision.recommendations}
      />
    );
    expect(screen.getByText("SYN-6000-010 Printing & Stationery")).toBeInTheDocument();
    expect(screen.getByText("Recommended GL Account")).toBeInTheDocument();
    expect(screen.getByText(/SYN-TAX-06/i)).toBeInTheDocument();
  });

  it("renders immutable outcome certificate for approved terminal task", () => {
    const mockOutcome = {
      id: "out-01",
      review_task_id: "task-01",
      actor_user_id: "user-acc-01",
      actor_membership_id: "mem-acc-01",
      outcome_type: ReviewOutcomeType.APPROVED,
      proposed_journal_id: "pj-01",
      source_correction_count: 0,
      reason: "Verified against physical receipt.",
      request_id: "req-01",
      created_at: "2026-08-29T16:00:00Z",
    };

    render(<TerminalBanner task={SCENARIO_ORDINARY.task} outcome={mockOutcome} />);
    expect(
      screen.getByText("Attributable Accounting Review Outcome: Approved")
    ).toBeInTheDocument();
    expect(screen.getByText(/Verified against physical receipt/i)).toBeInTheDocument();
  });
});
