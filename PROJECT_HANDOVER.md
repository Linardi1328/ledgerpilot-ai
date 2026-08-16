# Project Handover

## Current Status

**Current status: Phase 5 — Human Review, first slice (review branch)**

`main` contains the merged Phase 4 accounting-decision foundation through PR #5. The Phase 4 merge adds versioned accounting decision runs, deterministic validation findings, supplier-match candidates, duplicate candidates, configurable synthetic recommendations, proposed journals, source lineage, journal-balance controls, scoped RBAC, audit events, and PostgreSQL accounting constraints.

Phase 4 outputs are recommendations only. They are not approvals, postings, payment instructions, professional accounting/tax advice, SQL Account exports, or MyInvois submissions.

The current Phase 5 review branch adds the smallest coherent human-review foundation: scoped review-task creation/read boundaries, accountant/senior-reviewer ownership, deterministic senior escalation state, audit events, and database constraints linking review ownership and source decision scope.

## Handover Summary

The project has established:

- Product purpose and safety principles.
- Prototype 1 MVP scope.
- User roles and conceptual permissions.
- Domain model documentation plus implemented identity, document, audit, extraction, accounting-decision, and first-slice review-task primitives.
- Functional and non-functional requirements.
- Accounting-control principles, security/privacy requirements, risk register, architecture direction, and ADRs.
- FastAPI, typed settings, SQLAlchemy, Alembic, PostgreSQL development configuration, RBAC, tenant/client scoping, audit events, secure document intake, structured extraction, and accounting-decision foundations.
- Phase 4 accounting decision persistence, synthetic configurable rules, deterministic Decimal validation, recommendation lineage, journal-balance controls, and safe accounting-decision audit events.
- Phase 5 first-slice review tasks with explicit source linkage, reviewer ownership, `open -> escalated` lifecycle, senior-review escalation, and append-only audit evidence.

## Human-Review Safety Boundary

The Phase 5 first slice does not implement approval, rejection, posting, correction of approved records, payment execution, supplier bank-detail changes, SQL Account export, production MyInvois integration, production OCR/auth/storage, or autonomous accounting judgement.

Creating or escalating a review task never changes the underlying Phase 4 decision run or converts any recommendation into an approval.

## Owner-Tested Baseline

Phase 0 through Phase 3 have completed owner testing with synthetic data only. Phase 4 has been merged to `main` after its PR review/CI process. This Phase 5 branch still requires its own complete CI and independent review before merge.

## Review Notes

- Accountant interviews are occurring separately.
- The planned Phase 4 accountant interview was postponed.
- Requirements marked provisional require practitioner validation.
- Malaysian accounting, taxation, privacy, and MyInvois rules require independent expert validation before production use.
- All repository examples are synthetic.
- No real client data or credentials should be committed to this public repository.

## Next Recommended Action

Run the complete Phase 5 quality gate, inspect the public diff, and independently review the Phase 5 pull request before merge. Do not merge without review.
