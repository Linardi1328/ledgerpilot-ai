from __future__ import annotations

import pytest

from ledgerpilot.accounting.states import (
    AccountingDecisionRunStatus,
    InvalidAccountingDecisionTransition,
    transition_accounting_decision_status,
)


def test_accounting_decision_lifecycle_allows_success_path() -> None:
    assert (
        transition_accounting_decision_status(
            AccountingDecisionRunStatus.PENDING,
            AccountingDecisionRunStatus.RUNNING,
        )
        is AccountingDecisionRunStatus.RUNNING
    )
    assert (
        transition_accounting_decision_status(
            AccountingDecisionRunStatus.RUNNING,
            AccountingDecisionRunStatus.SUCCEEDED,
        )
        is AccountingDecisionRunStatus.SUCCEEDED
    )


def test_accounting_decision_lifecycle_allows_failure_path() -> None:
    assert (
        transition_accounting_decision_status(
            AccountingDecisionRunStatus.RUNNING,
            AccountingDecisionRunStatus.FAILED,
        )
        is AccountingDecisionRunStatus.FAILED
    )


def test_terminal_accounting_decision_run_cannot_restart() -> None:
    with pytest.raises(InvalidAccountingDecisionTransition):
        transition_accounting_decision_status(
            AccountingDecisionRunStatus.SUCCEEDED,
            AccountingDecisionRunStatus.RUNNING,
        )
    with pytest.raises(InvalidAccountingDecisionTransition):
        transition_accounting_decision_status(
            AccountingDecisionRunStatus.FAILED,
            AccountingDecisionRunStatus.RUNNING,
        )
