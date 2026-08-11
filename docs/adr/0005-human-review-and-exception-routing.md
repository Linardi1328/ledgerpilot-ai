# ADR 0005: Human Review and Exception Routing

## Status

Accepted.

## Context

LedgerPilot AI is intended to assist accountants, not replace professional judgement. High-risk, high-value, unusual, uncertain, or complex accounting and tax decisions require human review.

## Decision

Require human review for exceptions and enforce configurable routing to accountants or senior reviewers. AI recommendations cannot approve, export, or bypass controls independently.

## Alternatives

- Allow autonomous approval above a confidence threshold.
- Require senior review for every transaction.
- Avoid AI-assisted recommendations.

## Consequences

- The workflow preserves professional judgement.
- Review queues and authority rules become core product concepts.
- Throughput depends on practical routing thresholds.

## Risks

- Poor routing could overload senior reviewers.
- Users may still over-rely on confidence indicators.

## Follow-up

Validate thresholds, escalation triggers, and approval authority with accountants.
