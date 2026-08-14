from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class SupplierDirectoryEntry:
    supplier_reference: str
    supplier_name: str
    aliases: tuple[str, ...]
    default_gl_account_reference: str
    default_category_reference: str
    default_tax_code_reference: str
    default_cost_centre_reference: str | None
    rule_name: str
    rule_version: str
    firm_id: UUID | None = None
    client_id: UUID | None = None


class AccountingDecisionPolicy(Protocol):
    @property
    def engine_name(self) -> str: ...

    @property
    def engine_version(self) -> str: ...

    @property
    def low_confidence_threshold(self) -> Decimal: ...

    @property
    def payable_account_reference(self) -> str: ...

    @property
    def synthetic_journal_credit_adjustment(self) -> Decimal: ...

    def required_fields_for(self, document_type: str | None) -> tuple[str, ...]: ...

    def decision_relevant_fields_for(self, document_type: str | None) -> tuple[str, ...]: ...

    def supplier_directory_for(
        self,
        *,
        firm_id: UUID,
        client_id: UUID,
    ) -> Sequence[SupplierDirectoryEntry]: ...


class SyntheticAccountingDecisionPolicy:
    """Synthetic configurable policy for Phase 4 development and tests.

    These defaults are fixture data, not professional accounting or tax advice.
    """

    def __init__(
        self,
        *,
        supplier_directory: Sequence[SupplierDirectoryEntry] | None = None,
        synthetic_journal_credit_adjustment: Decimal = Decimal("0"),
    ) -> None:
        self._supplier_directory = (
            _default_supplier_directory()
            if supplier_directory is None
            else tuple(supplier_directory)
        )
        self._synthetic_journal_credit_adjustment = synthetic_journal_credit_adjustment

    @property
    def engine_name(self) -> str:
        return "synthetic_accounting_decision_engine"

    @property
    def engine_version(self) -> str:
        return "0.1.0"

    @property
    def low_confidence_threshold(self) -> Decimal:
        return Decimal("0.5000")

    @property
    def payable_account_reference(self) -> str:
        return "liability:accounts_payable"

    @property
    def synthetic_journal_credit_adjustment(self) -> Decimal:
        return self._synthetic_journal_credit_adjustment

    def required_fields_for(self, document_type: str | None) -> tuple[str, ...]:
        if document_type == "purchase_invoice":
            return (
                "document.type",
                "supplier.name",
                "invoice.number",
                "invoice.date",
                "invoice.currency",
                "invoice.total",
            )
        return ("document.type",)

    def decision_relevant_fields_for(self, document_type: str | None) -> tuple[str, ...]:
        if document_type == "purchase_invoice":
            return self.required_fields_for(document_type) + (
                "invoice.subtotal",
                "invoice.tax",
            )
        return self.required_fields_for(document_type)

    def supplier_directory_for(
        self,
        *,
        firm_id: UUID,
        client_id: UUID,
    ) -> Sequence[SupplierDirectoryEntry]:
        return tuple(
            entry
            for entry in self._supplier_directory
            if (entry.firm_id is None or entry.firm_id == firm_id)
            and (entry.client_id is None or entry.client_id == client_id)
        )


def _default_supplier_directory() -> tuple[SupplierDirectoryEntry, ...]:
    return (
        SupplierDirectoryEntry(
            supplier_reference="supplier:synthetic-office-supplies",
            supplier_name="Synthetic Office Supplies Sdn. Bhd.",
            aliases=("synthetic office supplies", "synthetic office supplies sdn bhd"),
            default_gl_account_reference="expense:office_supplies",
            default_category_reference="category:office_supplies",
            default_tax_code_reference="tax:review_required",
            default_cost_centre_reference="cost-centre:operations",
            rule_name="synthetic_supplier_default_mapping",
            rule_version="0.1.0",
        ),
    )
