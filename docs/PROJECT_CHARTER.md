# Project Charter

## Purpose

LedgerPilot AI is intended to reduce repetitive bookkeeping and accounting work through automation, artificial intelligence, deterministic accounting controls, and human-review workflows.

The product assists accountants with invoice and receipt processing, data entry, transaction categorisation, journal preparation, supplier/customer matching, duplicate-document detection, missing-information requests, exception review, bank reconciliation, month-end preparation, supporting-document management, and audit-history maintenance.

LedgerPilot AI must assist accountants rather than replace professional judgement.

## Core Operating Principle

> AI for extraction and recommendations + deterministic accounting controls + human approval for exceptions.

AI output is untrusted input until validated. Deterministic accounting controls and human review determine whether a recommendation is accepted.

## Current Phase

**Current status: Phase 0 — Foundation, Discovery, and Repository Audit**

Phase 0 is documentation-first. It establishes the repository baseline, project rules, MVP scope, risks, conceptual architecture, and minimal Python tooling. It does not build production accounting features.

## Target Users

- Firm administrators who manage workspaces, users, roles, configuration, and integrations.
- Accountants who review documents, correct extraction, review coding, approve ordinary work within authority, request information, and perform reconciliation work.
- Senior reviewers who handle unusual, high-risk, high-value, sensitive, or overridden work.
- Clients or document submitters who provide supporting documents and respond to information requests.
- Auditors or read-only users who review evidence, recommendations, approvals, corrections, and audit history.

## Foundational Safety Rules

LedgerPilot must never allow AI to independently:

- Release payments.
- Change supplier bank details.
- Silently alter approved accounting records.
- Bypass required approval.
- Make complex accounting judgements without human review.
- Provide unsupervised tax advice.
- Provide unsupervised legal advice.
- Hide uncertainty.
- Treat AI-generated output as inherently correct.

Approved accounting information must not be silently overwritten. Corrections should eventually use controlled correction, reversal, or supersession workflows.

All monetary calculations must eventually use decimal arithmetic, never binary floating-point arithmetic.

## Research Status

Accountant interviews are occurring separately and may introduce additional requirements later.

Uncertain requirements are classified using:

- Confirmed
- Provisional
- Requires accountant validation
- Requires accounting/tax expert validation
- Requires technical investigation

Unless otherwise stated, product assumptions in Phase 0 have this status:

**Status: Provisional — requires practitioner validation.**

## Public Repository Safety Policy

This repository is public. Only synthetic development data may be committed.

Never commit real client names, real invoices, real receipts, real statements, real bank information, real supplier bank details, real taxpayer identifiers, real MyInvois identifiers, real employee information, confidential accounting information, production databases, passwords, API keys, tokens, OAuth credentials, private certificates, `.env` files, or production secrets.

All examples must be fictional.

## Phase 0 Completion Standard

Phase 0 is complete only after documentation, tooling, verification, sensitive-data review, branch push, and pull-request creation have succeeded. Completion does not mean the product is production-ready.
