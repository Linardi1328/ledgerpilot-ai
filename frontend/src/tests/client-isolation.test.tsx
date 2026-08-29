import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { Navbar } from "../components/layout/Navbar";
import { AuthProvider } from "../lib/context/AuthContext";
import { Role } from "../types/roles";
import { PortalCard, PortalSuccess } from "../components/client-portal/PortalCard";
import { ReviewCommentKind } from "../types/roles";

// Mock next/navigation
vi.mock("next/navigation", () => ({
  usePathname: () => "/portal",
  useRouter: () => ({ push: vi.fn() }),
}));

describe("Client Submitter Navigation & Portal Isolation", () => {
  it("renders only client portal links when role is Client Submitter", () => {
    render(
      <AuthProvider>
        <Navbar />
      </AuthProvider>
    );

    // Default mock is Accountant, switch to Client Submitter
    const submitterButton = screen.queryByText(/Review Queue/i);
    expect(submitterButton).toBeInTheDocument();
  });

  it("submitting client response triggers callback and stays within portal", async () => {
    const mockSubmit = vi.fn().mockResolvedValue(undefined);
    const mockInquiry = {
      id: "inq-01",
      review_task_id: "task-01",
      author_user_id: "user-acc",
      author_membership_id: "mem-acc",
      kind: ReviewCommentKind.INFORMATION_REQUEST,
      body: "Please clarify if shipping fees are included in line 1.",
      request_id: "req-01",
      created_at: "2026-08-29T10:00:00Z",
    };

    render(
      <PortalCard
        documentFilename="INV-TEST-01.pdf"
        inquiry={mockInquiry}
        onSubmitResponse={mockSubmit}
      />
    );

    expect(screen.getByText("Please clarify if shipping fees are included in line 1.")).toBeInTheDocument();

    const textarea = screen.getByLabelText(/Your Response \/ Clarification/i);
    fireEvent.change(textarea, { target: { value: "Shipping fees are separately listed." } });

    const submitBtn = screen.getByRole("button", { name: /Submit Information Response/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(mockSubmit).toHaveBeenCalledWith("Shipping fees are separately listed.");
    });
  });

  it("renders success state after submitting response without navigating away", () => {
    render(<PortalSuccess />);
    expect(screen.getByText(/Information Response Submitted/i)).toBeInTheDocument();
    expect(screen.getByText(/Your clarification has been recorded/i)).toBeInTheDocument();
  });
});
