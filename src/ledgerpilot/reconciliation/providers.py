from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from ledgerpilot.reconciliation.types import BankImportBatch, BankImportRequest


class BankTransactionImportProvider(Protocol):
    provider_name: str
    provider_version: str

    def fetch_transactions(self, request: BankImportRequest) -> BankImportBatch:
        """Return a provider-attributable batch without performing reconciliation decisions."""
        ...


class SyntheticBankTransactionProvider:
    """Development/test-only provider backed by preconstructed synthetic import batches."""

    provider_name = "synthetic_bank_feed"
    provider_version = "1.0"

    def __init__(self, batches: Sequence[BankImportBatch]) -> None:
        self._batches = tuple(batches)

    def fetch_transactions(self, request: BankImportRequest) -> BankImportBatch:
        for batch in self._batches:
            if (
                batch.firm_id == request.firm_id
                and batch.client_id == request.client_id
                and batch.account_reference == request.account_reference
                and batch.period_start == request.period_start
                and batch.period_end == request.period_end
            ):
                return batch
        raise LookupError("synthetic bank import batch not found")
