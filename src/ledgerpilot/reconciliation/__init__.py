"""Controlled bank-reconciliation domain foundations."""

from ledgerpilot.reconciliation.matching import (
    DeterministicReconciliationMatcher,
    ReconciliationMatchingPolicy,
)
from ledgerpilot.reconciliation.providers import (
    BankTransactionImportProvider,
    SyntheticBankTransactionProvider,
)
from ledgerpilot.reconciliation.types import (
    ApprovedReconciliationTarget,
    BankImportBatch,
    BankImportRequest,
    BankTransactionDirection,
    ImportedBankTransaction,
    ReconciliationCandidateDecision,
    ReconciliationCandidateStatus,
    ReconciliationMatchReason,
    ReconciliationMatchResult,
)

__all__ = [
    "ApprovedReconciliationTarget",
    "BankImportBatch",
    "BankImportRequest",
    "BankTransactionDirection",
    "BankTransactionImportProvider",
    "DeterministicReconciliationMatcher",
    "ImportedBankTransaction",
    "ReconciliationCandidateDecision",
    "ReconciliationCandidateStatus",
    "ReconciliationMatchingPolicy",
    "ReconciliationMatchReason",
    "ReconciliationMatchResult",
    "SyntheticBankTransactionProvider",
]
