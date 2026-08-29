# LedgerPilot AI — Frontend Application

This directory contains the Next.js / TypeScript frontend application for **LedgerPilot AI**, implementing the **Phase 5 Human Review Workspace** and **Client Submitter Information Portal**.

---

## Operating Modes

LedgerPilot AI frontend supports two distinct operating modes selectable via the UI header:

1. **Mock Demo Mode (`mock`)**:
   - Uses synthetic Malaysian accounting fixtures (`ordinary`, `senior_review_required`, `blocked`).
   - Demonstrates the complete multi-tenant Review Queue worklist, senior reviewer directory mappings, client inbox, and real-time interaction state machine.
   - All tax codes (e.g. `SYN-TAX-06`) and company accounts are clearly marked synthetic demo configurations.

2. **Live Development Mode (`live`)**:
   - Integrates with the live FastAPI backend via typed API clients in `src/lib/api/`.
   - Uses canonical full-lineage URLs (`/reviews/[clientId]/documents/[documentId]/extractions/[extractionRunId]/decisions/[decisionRunId]/tasks/[reviewTaskId]`).
   - Development auth uses `X-LedgerPilot-Dev-Subject` and `X-LedgerPilot-Firm` headers, validating permissions from `/api/v1/context`.

---

## Monetary & Accounting Invariants

- **Zero Floating-Point Calculations**: Monetary amounts are formatted and validated using exact decimal strings and scaled `BigInt` (10,000 scale / 4 decimal places) arithmetic (`src/lib/decimal/money.ts`).
- **Server Primacy**: Backend `is_balanced` status and deterministic risk classification remain authoritative. Local diagnostic calculations verify balance independently; if a mismatch occurs, the UI displays a **Journal verification mismatch** warning and disables approval.
- **Human Supervision Boundary**: AI recommendations and extraction fields are untrusted input until reviewed and confirmed by an authorized human accountant.
- **Attributable Outcome**: Approvals and rejections record an attributable human review outcome.

---

## Role-Based Access & Route Isolation

- **Client Submitter**: Navigation strips internal review queues and workspaces; submitter is confined to `/portal` with single-question inquiry and response cards. Submitting responses remains in the portal with a confirmation state.
- **Auditor**: Read-only compliance view; all mutation surfaces (field correction, comments, escalation, info requests, approve, reject) are removed.
- **Firm Admin**: Phase 5 review task endpoints are unavailable to Firm Admin under the RBAC model; workspace renders an informative access limitation banner.
- **Accountant**: Authorized for ordinary review approvals, field corrections, escalation to senior, information requests, and rejections.
- **Senior Reviewer**: Authorized for high-risk / senior review task approvals.

---

## Quickstart

```bash
# 1. Install dependencies
npm ci

# 2. Run TypeScript strict typecheck
npm run typecheck

# 3. Run ESLint
npm run lint

# 4. Run Vitest with coverage
npm run test:coverage

# 5. Build for production
npm run build

# 6. Start development server
npm run dev
```
