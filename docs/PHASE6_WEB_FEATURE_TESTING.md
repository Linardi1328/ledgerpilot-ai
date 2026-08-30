# Phase 6 Web Feature Testing Preparation

## Purpose

Prepare browser feature testing while the Phase 6 reconciliation frontend is being completed. The Phase 6 backend is merged, but this document does not claim that the frontend or an integrated preview is already working.

All testing remains synthetic-only and must preserve `AGENTS.md`: no real client/bank/tax data or secrets, no binary floating point for money, no automatic reconciliation from matcher scores, tenant isolation, attributable human outcomes, and no claims of untested functionality.

Control boundary:

`bank transaction -> deterministic candidate evidence -> human review -> explicit human matched/unmatched outcome`

## Two preview levels

### Level A — synthetic UI preview

Use this as soon as the Phase 6 frontend is buildable.

- Vercel Preview deployment of the Next.js app.
- Vercel project root: `frontend`.
- Node.js 22, matching Frontend CI.
- Mock mode only.
- Synthetic reconciliation fixtures only.
- No remote backend/database required.

Level A verifies UI behavior, navigation, roles, worklist-state presentation, forms, error/empty/loading states, and mock transitions. It is not evidence that live integration works.

### Level B — live integration preview

Use after the test backend is provisioned.

- Same Vercel Preview frontend.
- Dedicated HTTPS FastAPI test deployment.
- Dedicated isolated PostgreSQL test database.
- Migrations upgraded to `head`.
- Deterministic synthetic seed data only.
- Vercel Preview variable `BACKEND_INTERNAL_URL` points to the test backend origin.

Browser requests continue through `/api/backend/...`; `frontend/next.config.mjs` rewrites those requests to `${BACKEND_INTERNAL_URL}/api/v1/...`.

## Vercel project configuration

Create the Vercel project from `Linardi1328/ledgerpilot-ai` with:

- Root Directory: `frontend`
- Framework: Next.js
- Node.js: 22
- Install Command: `npm ci`
- Build Command: `npm run build`
- Git integration enabled for review-branch previews

Keep Preview and Production environments separate. Never point a preview at production infrastructure.

### Frontend preview environment

Live integration currently needs one application-specific server-side frontend value:

```text
BACKEND_INTERNAL_URL=https://<dedicated-test-backend-origin>
```

`frontend/.env.preview.example` contains a non-routable placeholder only. Actual values belong in Vercel environment settings, not Git.

## Test backend contract

The remote feature-test backend must be non-production. Recommended settings:

```text
LEDGERPILOT_ENV=development
LEDGERPILOT_AUTH_MODE=development
LEDGERPILOT_DEV_AUTH_ENABLED=true
LEDGERPILOT_DATABASE_URL=<secret isolated test PostgreSQL URL>
LEDGERPILOT_LOG_LEVEL=INFO
```

The application intentionally rejects development authentication in production.

Before connecting Vercel:

1. provision the isolated test database;
2. configure backend secrets in the hosting platform;
3. run `alembic upgrade head`;
4. load deterministic synthetic feature-test data;
5. start the FastAPI deployment over HTTPS;
6. verify `GET /api/v1/health/live`;
7. verify `GET /api/v1/health/ready` reports database readiness;
8. verify `GET /api/v1/context` with the development principals used by the frontend.

Do not enable real bank connectors, production credentials, payment/settlement behavior, or real client data in this environment.

## Synthetic Level B dataset

The remote database must provide enough lineage to exercise the merged reconciliation contract:

- one synthetic firm;
- two synthetic clients;
- Accountant, Senior Reviewer, Auditor, Firm Admin, and Client Submitter development principals;
- approved Phase 5 review outcomes eligible as reconciliation targets;
- synthetic bank imports/transactions;
- examples that can reach every worklist projection:
  - `not_evaluated`
  - `unmatched`
  - `candidates_available`
  - `in_review`
  - `disputed`
  - `matched`
  - `resolved_unmatched`

A deterministic seed mechanism is required before Level B begins; it must never contain copied real financial data.

## Browser feature matrix

### Global

- `/` and `/reconciliation` render without a blank page or Next.js error overlay.
- No unexplained browser-console or Vercel runtime errors.
- Active synthetic client is visible.
- Client switching reloads authoritative client-specific state.
- Exact money strings render without JavaScript floating-point calculations.
- Loading, empty, validation, conflict, forbidden, and backend-unavailable states are visible.
- Cold refresh preserves server-authoritative state.
- Live mode never falls back to mock authority after context/backend failure.
- An active client outside `principal.authorized_client_ids` fails closed.

### Accountant / Senior Reviewer

Where backend permissions allow, verify:

- worklist and state filtering;
- transaction details;
- deterministic candidate generation;
- starting a review pinned to match evidence;
- explicit candidate selection;
- dispute with reason;
- reopen with reason;
- approving only the explicitly selected candidate;
- marking unmatched with a required reason;
- immutable reconciliation history.

### Auditor

- Can view only the history/worklist surfaces authorized by the backend.
- Has no reconciliation mutation controls.

### Firm Admin

- Does not receive reconciliation mutation authority merely because the role is administrative.

### Client Submitter

- Does not receive internal reconciliation navigation/workspace access.

### Candidate evidence boundary

- Score/reasons are evidence and ranking only.
- A high score never auto-selects or auto-matches.
- Approval is unavailable until explicit human candidate selection exists.
- `matched` appears only after the approval API succeeds.

### Dispute, locking, terminal states

- Dispute/reopen are explicit and attributable.
- Match evidence is not silently regenerated after human review freezes it.
- `matched` and `resolved_unmatched` are terminal/read-only in the UI.
- Duplicate matching of the same approved Phase 5 review outcome is surfaced as a rejection/conflict, not hidden.

### Tenant isolation

- Unauthorized client IDs fail closed.
- Switching authorized clients never leaks the previous client's transactions/history.
- Direct URL/API manipulation cannot bypass the active principal's client scope.

## Browser verification procedure

For each exact preview deployment head:

1. require frontend CI/build to be green;
2. wait for Vercel status `READY`;
3. open the preview and wait for network idle;
4. capture `/` and `/reconciliation` screenshots;
5. check for framework error overlays and non-empty body content;
6. inspect browser console/network failures;
7. snapshot interactive elements;
8. execute the role/state scenarios applicable to Level A or Level B;
9. correlate live failures with Vercel and backend logs;
10. record pass/fail evidence before fixing or accepting a defect.

## Frontend quality gate

Run from `frontend/` before deploying an exact head for feature testing:

```bash
npm ci
npm run typecheck
npm run lint
npm run test:coverage
npm run build
```

Repository Frontend CI uses Node.js 22 and runs the same stages.

## Entry criteria

### Level A

- Phase 6 frontend workspace implemented.
- Interactive synthetic reconciliation fixtures implemented.
- Typecheck/lint/tests/build green.
- Vercel project linked with `frontend` as root.
- Preview deployment `READY`.

### Level B

All Level A criteria plus:

- remote test FastAPI deployment ready;
- isolated PostgreSQL test database ready;
- migrations applied;
- deterministic synthetic seed loaded;
- development auth verified;
- `BACKEND_INTERNAL_URL` configured in Vercel Preview only;
- backend live/ready/context checks green.

## Exit criteria

Phase 6 browser testing is complete only after:

- all required roles are exercised;
- every worklist state is exercised;
- live mode is tested against the merged backend contract;
- no live-to-mock fallback occurs;
- tenant/client isolation passes;
- terminal outcomes remain attributable and read-only;
- console/runtime errors are explained or fixed;
- remaining defects are explicitly recorded before merge.

## Current preparation gaps

At the start of this preparation:

- the connected Vercel team has no LedgerPilot project yet;
- the Phase 6 frontend is still being completed;
- the remote test FastAPI deployment is not yet provisioned;
- the isolated remote PostgreSQL database and deterministic live-test seed process are not yet provisioned.

These gaps do not block Antigravity from finishing the frontend or Level A preview readiness. They must be closed before Level B live integration testing begins.
