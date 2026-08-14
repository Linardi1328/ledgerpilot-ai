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


def test_unsupported_document_type_produces_no_purchase_invoice_accounting() -> None:
    output = AccountingDecisionEngine(SyntheticAccountingDecisionPolicy()).decide(
        firm_id=uuid.uuid4(),
        client_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        extraction_run_id=uuid.uuid4(),
        source_sha256="a" * 64,
        effective_values=_purchase_invoice_values(document_type="receipt"),
        prior_snapshots=(),
    )

    assert output.supplier_match.status == SupplierMatchStatus.NO_MATCH
    assert output.recommendations == ()
    assert output.proposed_journal is None
    assert AccountingFindingCode.UNSUPPORTED_DOCUMENT_TYPE in _finding_codes(output)
    assert AccountingFindingCode.TAX_REVIEW_REQUIRED not in _finding_codes(output)


def test_missing_document_type_produces_no_purchase_invoice_accounting() -> None:
    output = AccountingDecisionEngine(SyntheticAccountingDecisionPolicy()).decide(
        firm_id=uuid.uuid4(),
        client_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        extraction_run_id=uuid.uuid4(),
        source_sha256="a" * 64,
        effective_values=_purchase_invoice_values(document_type=None),
        prior_snapshots=(),
    )

    assert output.supplier_match.status == SupplierMatchStatus.NO_MATCH
    assert output.recommendations == ()
    assert output.proposed_journal is None
    assert AccountingFindingCode.MISSING_REQUIRED_FIELD in _finding_codes(output)


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


def test_uppercase_currency_is_accepted_for_journal_output() -> None:
    output = _decide_for_currency("MYR")

    assert AccountingFindingCode.INVALID_CURRENCY not in _finding_codes(output)
    assert output.proposed_journal is not None
    assert output.proposed_journal.currency == "MYR"


def test_lowercase_currency_is_normalized_without_mutating_effective_value() -> None:
    values = _purchase_invoice_values(currency="myr")

    output = AccountingDecisionEngine(SyntheticAccountingDecisionPolicy()).decide(
        firm_id=uuid.uuid4(),
        client_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        extraction_run_id=uuid.uuid4(),
        source_sha256="a" * 64,
        effective_values=values,
        prior_snapshots=(),
    )

    assert AccountingFindingCode.INVALID_CURRENCY not in _finding_codes(output)
    assert output.proposed_journal is not None
    assert output.proposed_journal.currency == "MYR"
    assert values["invoice.currency"].value == "myr"


def test_usd_currency_is_accepted_for_journal_output() -> None:
    output = _decide_for_currency("USD")

    assert AccountingFindingCode.INVALID_CURRENCY not in _finding_codes(output)
    assert output.proposed_journal is not None
    assert output.proposed_journal.currency == "USD"


def test_invalid_long_currency_creates_finding_and_no_journal() -> None:
    output = _decide_for_currency("MYR_LONG")

    invalid = _invalid_currency_findings(output)
    assert len(invalid) == 1
    assert invalid[0].field_path == "invoice.currency"
    assert invalid[0].evidence == {
        "field_path": "invoice.currency",
        "reason": "must_be_three_ascii_letters",
        "expected_format": "AAA",
    }
    assert output.proposed_journal is None


def test_invalid_short_currency_creates_finding_and_no_journal() -> None:
    output = _decide_for_currency("US")

    assert len(_invalid_currency_findings(output)) == 1
    assert output.proposed_journal is None


def test_invalid_alphanumeric_currency_creates_finding_and_no_journal() -> None:
    output = _decide_for_currency("US12")

    assert len(_invalid_currency_findings(output)) == 1
    assert output.proposed_journal is None


def test_invalid_numeric_currency_creates_finding_and_no_journal() -> None:
    output = _decide_for_currency("123")

    assert len(_invalid_currency_findings(output)) == 1
    assert output.proposed_journal is None


def test_missing_currency_keeps_required_field_finding_and_no_journal() -> None:
    output = _decide_for_currency(None)

    assert AccountingFindingCode.MISSING_REQUIRED_FIELD in _finding_codes(output)
    assert AccountingFindingCode.INVALID_CURRENCY not in _finding_codes(output)
    assert output.proposed_journal is None


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


def test_invalid_zero_invoice_total_creates_finding_and_no_journal() -> None:
    output = _decide_for_total("0")

    assert AccountingFindingCode.INVALID_MONETARY_VALUE in _finding_codes(output)
    assert output.proposed_journal is None


def test_invalid_negative_invoice_total_creates_finding_and_no_journal() -> None:
    output = _decide_for_total("-100.00")

    assert AccountingFindingCode.INVALID_MONETARY_VALUE in _finding_codes(output)
    assert output.proposed_journal is None


def test_invalid_fractional_precision_creates_finding_and_no_journal() -> None:
    output = _decide_for_total("100.12345")

    invalid = [
        finding
        for finding in output.findings
        if finding.code == AccountingFindingCode.INVALID_MONETARY_VALUE
    ]
    assert len(invalid) == 1
    assert invalid[0].evidence is not None
    assert invalid[0].evidence["reason"] == "unsupported_fractional_precision"
    assert output.proposed_journal is None


def test_maximum_supported_monetary_boundary_is_valid() -> None:
    output = _decide_for_total("99999999999999.9999")

    assert AccountingFindingCode.INVALID_MONETARY_VALUE not in _finding_codes(output)
    assert output.proposed_journal is not None
    assert output.proposed_journal.total_debits == Decimal("99999999999999.9999")
    assert output.proposed_journal.total_credits == Decimal("99999999999999.9999")


def test_outside_supported_monetary_magnitude_creates_finding_and_no_journal() -> None:
    output = _decide_for_total("100000000000000.0000")

    invalid = [
        finding
        for finding in output.findings
        if finding.code == AccountingFindingCode.INVALID_MONETARY_VALUE
    ]
    assert len(invalid) == 1
    assert invalid[0].evidence is not None
    assert invalid[0].evidence["reason"] == "outside_supported_range"
    assert output.proposed_journal is None


def test_invalid_arithmetic_operand_creates_finding_without_arithmetic_crash() -> None:
    output = AccountingDecisionEngine(SyntheticAccountingDecisionPolicy()).decide(
        firm_id=uuid.uuid4(),
        client_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        extraction_run_id=uuid.uuid4(),
        source_sha256="a" * 64,
        effective_values=_purchase_invoice_values(
            subtotal="90.12345",
            tax="10.00",
            total="100.00",
        ),
        prior_snapshots=(),
    )

    assert AccountingFindingCode.INVALID_MONETARY_VALUE in _finding_codes(output)
    assert AccountingFindingCode.ARITHMETIC_MISMATCH not in _finding_codes(output)
    assert output.proposed_journal is None


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


def test_synthetic_policy_supplier_directory_configuration_semantics() -> None:
    firm_id = uuid.uuid4()
    client_id = uuid.uuid4()
    explicit_entry = SupplierDirectoryEntry(
        supplier_reference="supplier:explicit",
        supplier_name="Synthetic Explicit Supplier",
        aliases=(),
        default_gl_account_reference="expense:explicit",
        default_category_reference="category:explicit",
        default_tax_code_reference="tax:review_required",
        default_cost_centre_reference=None,
        rule_name="synthetic_explicit_rule",
        rule_version="0.1.0",
    )

    default_directory = SyntheticAccountingDecisionPolicy().supplier_directory_for(
        firm_id=firm_id,
        client_id=client_id,
    )
    empty_directory = SyntheticAccountingDecisionPolicy(
        supplier_directory=(),
    ).supplier_directory_for(firm_id=firm_id, client_id=client_id)
    explicit_directory = SyntheticAccountingDecisionPolicy(
        supplier_directory=(explicit_entry,),
    ).supplier_directory_for(firm_id=firm_id, client_id=client_id)

    assert [entry.supplier_reference for entry in default_directory] == [
        "supplier:synthetic-office-supplies"
    ]
    assert empty_directory == ()
    assert explicit_directory == (explicit_entry,)


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
    document_type: str | None = "purchase_invoice",
    currency: str | None = "MYR",
    supplier_name: str = "Synthetic Office Supplies Sdn. Bhd.",
    invoice_number: str = "SYN-INV-001",
    subtotal: str | None = None,
    tax: str | None = None,
    total: str = "100.00",
) -> dict[str, EffectiveExtractionValue]:
    values = {
        "supplier.name": _value("supplier.name", supplier_name),
        "invoice.number": _value(
            "invoice.number",
            invoice_number,
            normalized_value=invoice_number,
        ),
        "invoice.date": _value("invoice.date", "2026-08-11", normalized_value="2026-08-11"),
        "invoice.total": _value(
            "invoice.total",
            total,
            normalized_value=total,
            value_type="decimal",
        ),
    }
    if currency is not None:
        values["invoice.currency"] = _value(
            "invoice.currency",
            currency,
            normalized_value=currency,
        )
    if document_type is not None:
        values["document.type"] = _value(
            "document.type",
            f"synthetic_{document_type}",
            normalized_value=document_type,
        )
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


def _decide_for_total(total: str):
    return AccountingDecisionEngine(SyntheticAccountingDecisionPolicy()).decide(
        firm_id=uuid.uuid4(),
        client_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        extraction_run_id=uuid.uuid4(),
        source_sha256="a" * 64,
        effective_values=_purchase_invoice_values(total=total),
        prior_snapshots=(),
    )


def _decide_for_currency(currency: str | None):
    return AccountingDecisionEngine(SyntheticAccountingDecisionPolicy()).decide(
        firm_id=uuid.uuid4(),
        client_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        extraction_run_id=uuid.uuid4(),
        source_sha256="a" * 64,
        effective_values=_purchase_invoice_values(currency=currency),
        prior_snapshots=(),
    )


def _finding_codes(output) -> set[AccountingFindingCode]:
    return {finding.code for finding in output.findings}


def _invalid_currency_findings(output):
    return [
        finding
        for finding in output.findings
        if finding.code == AccountingFindingCode.INVALID_CURRENCY
    ]


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
