from __future__ import annotations

from enum import StrEnum


class AccountingDecisionRunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


_ALLOWED_TRANSITIONS: dict[AccountingDecisionRunStatus, frozenset[AccountingDecisionRunStatus]] = {
    AccountingDecisionRunStatus.PENDING: frozenset({AccountingDecisionRunStatus.RUNNING}),
    AccountingDecisionRunStatus.RUNNING: frozenset(
        {
            AccountingDecisionRunStatus.SUCCEEDED,
            AccountingDecisionRunStatus.FAILED,
        }
    ),
    AccountingDecisionRunStatus.SUCCEEDED: frozenset(),
    AccountingDecisionRunStatus.FAILED: frozenset(),
}


class InvalidAccountingDecisionTransition(ValueError):
    pass


def transition_accounting_decision_status(
    current_status: AccountingDecisionRunStatus,
    next_status: AccountingDecisionRunStatus,
) -> AccountingDecisionRunStatus:
    if next_status not in _ALLOWED_TRANSITIONS[current_status]:
        raise InvalidAccountingDecisionTransition(
            f"invalid accounting decision transition: {current_status.value} -> {next_status.value}"
        )
    return next_status
