from __future__ import annotations

import uuid
from decimal import Decimal

from ledgerpilot.accounting.engine import AccountingDecisionEngine
from ledgerpilot.accounting.rules import SupplierDirectoryEntry, SyntheticAccountingDecisionPolicy
from ledgerpilot.accounting.types import (
    AccountingFindingCode,
    AccountingRecommendationType,
    EffectiveExtractionValue,
    JournalBalanceStatus,
    PriorDecisionSnapshot,
    SupplierMatchStatus,
)


def test_complete_purchase_invoice_produces_recommendations_and_balanced_journal() -> None:
    output = AccountingDecisionEngine(SyntheticAccountingDecisionPolicy()).decide(
        firm_id=uuid.uuid4(),
        client_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        extraction_run_id=uuid.uuid4(),
        source_sha256="a" * 64,
        effective_values=_purchase_invoice_values(),
        prior_snapshots=(),
    )

    assert AccountingFindingCode.MISSING_REQUIRED_FIELD not in {
        finding.code for finding in output.findings
    }
    assert output.supplier_match.status == SupplierMatchStatus.CONFIDENT_MATCH
    assert {
        recommendation.recommendation_type: recommendation
        for recommendation in output.recommendations
    }[AccountingRecommendationType.GL_ACCOUNT].recommended_value == "expense:office_supplies"
    assert {
        recommendation.recommendation_type: recommendation
        for recommendation in output.recommendations
    }[AccountingRecommendationType.CATEGORY].recommended_value == "category:office_supplies"
    assert output.proposed_journal is not None
    assert output.proposed_journal.balance_status == JournalBalanceStatus.BALANCED
    assert output.proposed_journal.total_debits == Decimal("100.00")
    assert output.proposed_journal.total_credits == Decimal("100.00")
    assert all(isinstance(line.debit_amount, Decimal) for line in output.proposed_journal.lines)
    assert all(isinstance(line.credit_amount, Decimal) for line in output.proposed_journal.lines)


def test_missing_required_field_creates_structured_finding_without_inventing_value() -> None:
    values = _purchase_invoice_values()
    del values["invoice.number"]

    output = AccountingDecisionEngine(SyntheticAccountingDecisionPolicy()).decide(
        firm_id=uuid.uuid4(),
        client_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        extraction_run_id=uuid.uuid4(),
        source_sha256="a" * 64,
        effective_values=values,
        prior_snapshots=(),
    )

    missing = [
        finding
        for finding in output.findings
        if finding.code == AccountingFindingCode.MISSING_REQUIRED_FIELD
    ]
    assert len(missing) == 1
    assert missing[0].field_path == "invoice.number"
    assert "invoice.number" not in values


def test_arithmetic_validation_uses_decimal_precision() -> None:
    values = _purchase_invoice_values(
        subtotal="0.10",
        tax="0.20",
        total="0.30",
    )

    output = AccountingDecisionEngine(SyntheticAccountingDecisionPolicy()).decide(
        firm_id=uuid.uuid4(),
        client_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        extraction_run_id=uuid.uuid4(),
        source_sha256="a" * 64,
        effective_values=values,
        prior_snapshots=(),
    )

    assert AccountingFindingCode.ARITHMETIC_MISMATCH not in {
        finding.code for finding in output.findings
    }
    assert output.proposed_journal is not None
    assert output.proposed_journal.total_debits == Decimal("0.30")


def test_arithmetic_mismatch_creates_finding_without_changing_values() -> None:
    values = _purchase_invoice_values(subtotal="90.00", tax="10.01", total="100.00")

    output = AccountingDecisionEngine(SyntheticAccountingDecisionPolicy()).decide(
        firm_id=uuid.uuid4(),
        client_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        extraction_run_id=uuid.uuid4(),
        source_sha256="a" * 64,
        effective_values=values,
        prior_snapshots=(),
    )

    mismatch = [
        finding
        for finding in output.findings
        if finding.code == AccountingFindingCode.ARITHMETIC_MISMATCH
    ]
    assert len(mismatch) == 1
    assert mismatch[0].evidence == {
        "formula": "invoice.subtotal + invoice.tax == invoice.total",
        "calculated_total": "100.01",
        "reported_total": "100.00",
    }
    assert values["invoice.total"].value == "100.00"


def test_unknown_supplier_creates_new_supplier_and_unknown_mapping_flags() -> None:
    values = _purchase_invoice_values(supplier_name="Synthetic Unknown Supplier Sdn. Bhd.")

    output = AccountingDecisionEngine(SyntheticAccountingDecisionPolicy()).decide(
        firm_id=uuid.uuid4(),
        client_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        extraction_run_id=uuid.uuid4(),
        source_sha256="a" * 64,
        effective_values=values,
        prior_snapshots=(),
    )

    assert output.supplier_match.status == SupplierMatchStatus.NO_MATCH
    assert output.recommendations == ()
    assert {finding.code for finding in output.findings} >= {
        AccountingFindingCode.NEW_SUPPLIER,
        AccountingFindingCode.UNKNOWN_ACCOUNT_MAPPING,
    }


def test_supplier_matching_respects_client_scoped_synthetic_directory() -> None:
    firm_id = uuid.uuid4()
    client_a = uuid.uuid4()
    client_b = uuid.uuid4()
    policy = SyntheticAccountingDecisionPolicy(
        supplier_directory=(
            SupplierDirectoryEntry(
                supplier_reference="supplier:client-a-only",
                supplier_name="Synthetic Client Scoped Supplier",
                aliases=(),
                default_gl_account_reference="expense:client_a",
                default_category_reference="category:client_a",
                default_tax_code_reference="tax:review_required",
                default_cost_centre_reference=None,
                rule_name="synthetic_client_scoped_rule",
                rule_version="0.1.0",
                firm_id=firm_id,
                client_id=client_a,
            ),
        )
    )
    values = _purchase_invoice_values(supplier_name="Synthetic Client Scoped Supplier")

    allowed = AccountingDecisionEngine(policy).decide(
        firm_id=firm_id,
        client_id=client_a,
        document_id=uuid.uuid4(),
        extraction_run_id=uuid.uuid4(),
        source_sha256="a" * 64,
        effective_values=values,
        prior_snapshots=(),
    )
    isolated = AccountingDecisionEngine(policy).decide(
        firm_id=firm_id,
        client_id=client_b,
        document_id=uuid.uuid4(),
        extraction_run_id=uuid.uuid4(),
        source_sha256="a" * 64,
        effective_values=values,
        prior_snapshots=(),
    )

    assert allowed.supplier_match.status == SupplierMatchStatus.CONFIDENT_MATCH
    assert isolated.supplier_match.status == SupplierMatchStatus.NO_MATCH


def test_duplicate_detection_returns_explainable_candidate_without_auto_rejection() -> None:
    prior_document_id = uuid.uuid4()
    prior_extraction_run_id = uuid.uuid4()
    prior_decision_run_id = uuid.uuid4()
    prior_snapshot = PriorDecisionSnapshot(
        decision_run_id=prior_decision_run_id,
        document_id=prior_document_id,
        extraction_run_id=prior_extraction_run_id,
        source_sha256="b" * 64,
        effective_values=_purchase_invoice_values(),
    )

    output = AccountingDecisionEngine(SyntheticAccountingDecisionPolicy()).decide(
        firm_id=uuid.uuid4(),
        client_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        extraction_run_id=uuid.uuid4(),
        source_sha256="c" * 64,
        effective_values=_purchase_invoice_values(),
        prior_snapshots=(prior_snapshot,),
    )

    assert len(output.duplicate_candidates) == 1
    assert output.duplicate_candidates[0].candidate_document_id == prior_document_id
    assert "invoice.number" in output.duplicate_candidates[0].evidence["matched_signals"]
    assert output.duplicate_candidates[0].confidence == Decimal("1")
    assert AccountingFindingCode.POSSIBLE_DUPLICATE in {finding.code for finding in output.findings}


def test_nonduplicate_is_not_flagged_as_duplicate() -> None:
    prior_snapshot = PriorDecisionSnapshot(
        decision_run_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        extraction_run_id=uuid.uuid4(),
        source_sha256="b" * 64,
        effective_values=_purchase_invoice_values(
            supplier_name="Synthetic Different Supplier Sdn. Bhd.",
            invoice_number="SYN-OTHER-001",
            total="101.00",
        ),
    )

    output = AccountingDecisionEngine(SyntheticAccountingDecisionPolicy()).decide(
        firm_id=uuid.uuid4(),
        client_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        extraction_run_id=uuid.uuid4(),
        source_sha256="c" * 64,
        effective_values=_purchase_invoice_values(),
        prior_snapshots=(prior_snapshot,),
    )

    assert output.duplicate_candidates == ()
    assert AccountingFindingCode.POSSIBLE_DUPLICATE not in {
        finding.code for finding in output.findings
    }


def test_unbalanced_journal_is_flagged_independently_from_recommendation_confidence() -> None:
    output = AccountingDecisionEngine(
        SyntheticAccountingDecisionPolicy(
            synthetic_journal_credit_adjustment=Decimal("0.01"),
        )
    ).decide(
        firm_id=uuid.uuid4(),
        client_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        extraction_run_id=uuid.uuid4(),
        source_sha256="a" * 64,
        effective_values=_purchase_invoice_values(),
        prior_snapshots=(),
    )

    assert output.proposed_journal is not None
    assert output.proposed_journal.is_balanced is False
    assert output.proposed_journal.total_debits == Decimal("100.00")
    assert output.proposed_journal.total_credits == Decimal("100.01")
    assert AccountingFindingCode.UNBALANCED_JOURNAL in {finding.code for finding in output.findings}


def _purchase_invoice_values(
    *,
    supplier_name: str = "Synthetic Office Supplies Sdn. Bhd.",
    invoice_number: str = "SYN-INV-001",
    subtotal: str | None = None,
    tax: str | None = None,
    total: str = "100.00",
) -> dict[str, EffectiveExtractionValue]:
    values = {
        "document.type": _value(
            "document.type",
            "synthetic_purchase_invoice",
            normalized_value="purchase_invoice",
        ),
        "supplier.name": _value("supplier.name", supplier_name),
        "invoice.number": _value(
            "invoice.number",
            invoice_number,
            normalized_value=invoice_number,
        ),
        "invoice.date": _value("invoice.date", "2026-08-11", normalized_value="2026-08-11"),
        "invoice.currency": _value("invoice.currency", "MYR", normalized_value="MYR"),
        "invoice.total": _value(
            "invoice.total",
            total,
            normalized_value=total,
            value_type="decimal",
        ),
    }
    if subtotal is not None:
        values["invoice.subtotal"] = _value(
            "invoice.subtotal",
            subtotal,
            normalized_value=subtotal,
            value_type="decimal",
        )
    if tax is not None:
        values["invoice.tax"] = _value(
            "invoice.tax",
            tax,
            normalized_value=tax,
            value_type="decimal",
        )
    return values


def _value(
    field_path: str,
    raw_value: str,
    *,
    normalized_value: str | None = None,
    value_type: str = "text",
    confidence: Decimal = Decimal("0.9000"),
) -> EffectiveExtractionValue:
    return EffectiveExtractionValue(
        field_id=uuid.uuid4(),
        field_path=field_path,
        value_type=value_type,
        raw_value=raw_value,
        normalized_value=normalized_value,
        confidence=confidence,
        source_page_number=1,
        corrected=False,
        latest_correction_id=None,
        latest_revision_number=None,
    )
