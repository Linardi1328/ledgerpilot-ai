from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from uuid import UUID

from ledgerpilot.accounting.rules import AccountingDecisionPolicy, SupplierDirectoryEntry
from ledgerpilot.accounting.types import (
    AccountingDecisionOutput,
    AccountingFindingCode,
    AccountingFindingDecision,
    AccountingFindingSeverity,
    AccountingRecommendationDecision,
    AccountingRecommendationType,
    DuplicateCandidateDecision,
    EffectiveExtractionValue,
    JournalBalanceStatus,
    PriorDecisionSnapshot,
    ProposedJournalDecision,
    ProposedJournalLineDecision,
    SupplierMatchCandidateDecision,
    SupplierMatchDecision,
    SupplierMatchStatus,
)

_ZERO = Decimal("0")
_DUPLICATE_SCORE_DENOMINATOR = Decimal("5")
_DUPLICATE_THRESHOLD = Decimal("0.8000")
_SUPPORTED_ACCOUNTING_DOCUMENT_TYPES = frozenset({"purchase_invoice"})
_ACCOUNTING_MONEY_PRECISION = 18
_ACCOUNTING_MONEY_SCALE = 4
_MAX_ACCOUNTING_MONEY = Decimal("99999999999999.9999")


class AccountingDecisionEngine:
    def __init__(self, policy: AccountingDecisionPolicy) -> None:
        self._policy = policy

    def decide(
        self,
        *,
        firm_id: UUID,
        client_id: UUID,
        document_id: UUID,
        extraction_run_id: UUID,
        source_sha256: str,
        effective_values: dict[str, EffectiveExtractionValue],
        prior_snapshots: tuple[PriorDecisionSnapshot, ...],
    ) -> AccountingDecisionOutput:
        del extraction_run_id
        findings: list[AccountingFindingDecision] = []
        document_type = _field_text(effective_values, "document.type")
        is_supported_document_type = document_type in _SUPPORTED_ACCOUNTING_DOCUMENT_TYPES
        required_fields = self._policy.required_fields_for(document_type)

        findings.extend(_required_field_findings(effective_values, required_fields))
        if document_type is not None and not is_supported_document_type:
            findings.append(_unsupported_document_type_finding(document_type))
        findings.extend(
            _low_confidence_findings(
                effective_values,
                self._policy.decision_relevant_fields_for(document_type),
                self._policy.low_confidence_threshold,
            )
        )

        monetary_values: dict[str, Decimal] = {}
        monetary_findings: tuple[AccountingFindingDecision, ...] = ()
        journal_currency: str | None = None
        currency_finding: AccountingFindingDecision | None = None
        if is_supported_document_type:
            monetary_values, monetary_findings = _accounting_monetary_values(effective_values)
            findings.extend(monetary_findings)
            journal_currency, currency_finding = _accounting_currency_value(effective_values)
            if currency_finding is not None:
                findings.append(currency_finding)
            findings.extend(_arithmetic_findings(effective_values, monetary_values))

        supplier_match = SupplierMatchDecision(status=SupplierMatchStatus.NO_MATCH, candidates=())
        matched_supplier: SupplierDirectoryEntry | None = None
        if is_supported_document_type:
            supplier_match = self._supplier_match(
                firm_id=firm_id,
                client_id=client_id,
                effective_values=effective_values,
            )
            matched_supplier = self._matched_supplier_entry(
                firm_id=firm_id,
                client_id=client_id,
                supplier_match=supplier_match,
            )
            if _field_text(effective_values, "supplier.name") and supplier_match.status == (
                SupplierMatchStatus.NO_MATCH
            ):
                findings.append(
                    AccountingFindingDecision(
                        code=AccountingFindingCode.NEW_SUPPLIER,
                        severity=AccountingFindingSeverity.WARNING,
                        field_path="supplier.name",
                        description="Supplier was not matched to the synthetic directory.",
                        evidence={"field_path": "supplier.name"},
                    )
                )

        duplicate_candidates: tuple[DuplicateCandidateDecision, ...] = ()
        if is_supported_document_type:
            duplicate_candidates = _duplicate_candidates(
                document_id=document_id,
                source_sha256=source_sha256,
                effective_values=effective_values,
                prior_snapshots=prior_snapshots,
                engine_name=self._policy.engine_name,
                engine_version=self._policy.engine_version,
            )
        if duplicate_candidates:
            findings.append(
                AccountingFindingDecision(
                    code=AccountingFindingCode.POSSIBLE_DUPLICATE,
                    severity=AccountingFindingSeverity.WARNING,
                    description="Possible duplicate document or invoice candidates were found.",
                    evidence={"candidate_count": len(duplicate_candidates)},
                )
            )

        recommendations: tuple[AccountingRecommendationDecision, ...] = ()
        if is_supported_document_type:
            recommendations = self._recommendations(matched_supplier)
        if (
            is_supported_document_type
            and matched_supplier is None
            and _field_text(effective_values, "supplier.name")
        ):
            findings.append(
                AccountingFindingDecision(
                    code=AccountingFindingCode.UNKNOWN_ACCOUNT_MAPPING,
                    severity=AccountingFindingSeverity.WARNING,
                    field_path="supplier.name",
                    description="No synthetic account mapping was found for the supplier.",
                    evidence={"field_path": "supplier.name"},
                )
            )
        if is_supported_document_type:
            findings.append(
                AccountingFindingDecision(
                    code=AccountingFindingCode.TAX_REVIEW_REQUIRED,
                    severity=AccountingFindingSeverity.WARNING,
                    description="Synthetic tax recommendation requires practitioner review.",
                    evidence={"basis": "phase_4_synthetic_tax_configuration"},
                )
            )

        proposed_journal: ProposedJournalDecision | None = None
        if is_supported_document_type and not monetary_findings and currency_finding is None:
            proposed_journal = self._proposed_journal(
                recommendations=recommendations,
                total=monetary_values.get("invoice.total"),
                currency=journal_currency,
            )
        if proposed_journal is not None and not proposed_journal.is_balanced:
            findings.append(
                AccountingFindingDecision(
                    code=AccountingFindingCode.UNBALANCED_JOURNAL,
                    severity=AccountingFindingSeverity.ERROR,
                    description="Proposed journal debits and credits do not balance.",
                    evidence={
                        "total_debits": _decimal_to_string(proposed_journal.total_debits),
                        "total_credits": _decimal_to_string(proposed_journal.total_credits),
                    },
                )
            )

        return AccountingDecisionOutput(
            findings=tuple(findings),
            supplier_match=supplier_match,
            duplicate_candidates=duplicate_candidates,
            recommendations=recommendations,
            proposed_journal=proposed_journal,
        )

    def _supplier_match(
        self,
        *,
        firm_id: UUID,
        client_id: UUID,
        effective_values: dict[str, EffectiveExtractionValue],
    ) -> SupplierMatchDecision:
        supplier_name = _field_text(effective_values, "supplier.name")
        if supplier_name is None:
            return SupplierMatchDecision(status=SupplierMatchStatus.NO_MATCH, candidates=())

        candidates: list[SupplierMatchCandidateDecision] = []
        normalized_supplier = _normalize_name(supplier_name)
        supplier_tokens = set(normalized_supplier.split())
        for entry in self._policy.supplier_directory_for(firm_id=firm_id, client_id=client_id):
            names = (entry.supplier_name, *entry.aliases)
            normalized_names = tuple(_normalize_name(name) for name in names)
            if normalized_supplier in normalized_names:
                return SupplierMatchDecision(
                    status=SupplierMatchStatus.CONFIDENT_MATCH,
                    candidates=(
                        _supplier_candidate(
                            entry=entry,
                            confidence=Decimal("0.9500"),
                            explanation=(
                                "Supplier matched exactly against synthetic directory data."
                            ),
                            evidence={"matched_on": "supplier.name", "match_type": "exact"},
                            engine_name=self._policy.engine_name,
                            engine_version=self._policy.engine_version,
                            is_confident=True,
                        ),
                    ),
                )

            entry_tokens = set().union(*(set(name.split()) for name in normalized_names))
            overlap = len(supplier_tokens & entry_tokens)
            if (
                supplier_tokens
                and entry_tokens
                and Decimal(overlap) / Decimal(len(supplier_tokens | entry_tokens))
                >= Decimal("0.5000")
            ):
                candidates.append(
                    _supplier_candidate(
                        entry=entry,
                        confidence=Decimal("0.7000"),
                        explanation=(
                            "Supplier has a partial token match against synthetic directory data."
                        ),
                        evidence={
                            "matched_on": "supplier.name",
                            "match_type": "token_overlap",
                            "overlap_token_count": overlap,
                        },
                        engine_name=self._policy.engine_name,
                        engine_version=self._policy.engine_version,
                        is_confident=False,
                    )
                )

        if candidates:
            return SupplierMatchDecision(
                status=SupplierMatchStatus.CANDIDATE_MATCHES,
                candidates=tuple(candidates),
            )
        return SupplierMatchDecision(status=SupplierMatchStatus.NO_MATCH, candidates=())

    def _recommendations(
        self,
        matched_supplier: SupplierDirectoryEntry | None,
    ) -> tuple[AccountingRecommendationDecision, ...]:
        if matched_supplier is None:
            return ()

        evidence: dict[str, object] = {
            "supplier_reference": matched_supplier.supplier_reference,
            "basis": "synthetic_supplier_directory",
        }
        recommendations = [
            AccountingRecommendationDecision(
                recommendation_type=AccountingRecommendationType.GL_ACCOUNT,
                recommended_value=matched_supplier.default_gl_account_reference,
                confidence=Decimal("0.9000"),
                explanation="Synthetic supplier rule selected the expense account.",
                evidence=evidence,
                rule_name=matched_supplier.rule_name,
                rule_version=matched_supplier.rule_version,
                model_version=None,
            ),
            AccountingRecommendationDecision(
                recommendation_type=AccountingRecommendationType.CATEGORY,
                recommended_value=matched_supplier.default_category_reference,
                confidence=Decimal("0.9000"),
                explanation="Synthetic supplier rule selected the category.",
                evidence=evidence,
                rule_name=matched_supplier.rule_name,
                rule_version=matched_supplier.rule_version,
                model_version=None,
            ),
            AccountingRecommendationDecision(
                recommendation_type=AccountingRecommendationType.TAX_CODE,
                recommended_value=matched_supplier.default_tax_code_reference,
                confidence=Decimal("0.5000"),
                explanation="Synthetic tax code placeholder requires practitioner validation.",
                evidence={"basis": "phase_4_synthetic_tax_configuration"},
                rule_name="synthetic_tax_review_rule",
                rule_version="0.1.0",
                model_version=None,
            ),
        ]
        if matched_supplier.default_cost_centre_reference is not None:
            recommendations.append(
                AccountingRecommendationDecision(
                    recommendation_type=AccountingRecommendationType.COST_CENTRE,
                    recommended_value=matched_supplier.default_cost_centre_reference,
                    confidence=Decimal("0.8500"),
                    explanation="Synthetic supplier rule selected the cost centre.",
                    evidence=evidence,
                    rule_name=matched_supplier.rule_name,
                    rule_version=matched_supplier.rule_version,
                    model_version=None,
                )
            )
        return tuple(recommendations)

    def _matched_supplier_entry(
        self,
        *,
        firm_id: UUID,
        client_id: UUID,
        supplier_match: SupplierMatchDecision,
    ) -> SupplierDirectoryEntry | None:
        if supplier_match.status != SupplierMatchStatus.CONFIDENT_MATCH:
            return None
        candidate = supplier_match.candidates[0]
        for entry in self._policy.supplier_directory_for(firm_id=firm_id, client_id=client_id):
            if entry.supplier_reference == candidate.supplier_reference:
                return entry
        return None

    def _proposed_journal(
        self,
        *,
        recommendations: tuple[AccountingRecommendationDecision, ...],
        total: Decimal | None,
        currency: str | None,
    ) -> ProposedJournalDecision | None:
        expense_account = _recommendation_value(
            recommendations,
            AccountingRecommendationType.GL_ACCOUNT,
        )
        if total is None or currency is None or expense_account is None:
            return None

        tax_code = _recommendation_value(recommendations, AccountingRecommendationType.TAX_CODE)
        cost_centre = _recommendation_value(
            recommendations,
            AccountingRecommendationType.COST_CENTRE,
        )
        credit_amount = total + self._policy.synthetic_journal_credit_adjustment
        lines = (
            ProposedJournalLineDecision(
                line_number=1,
                account_reference=expense_account,
                debit_amount=total,
                credit_amount=_ZERO,
                tax_code_reference=tax_code,
                cost_centre_reference=cost_centre,
                explanation="Synthetic purchase invoice expense line.",
                lineage={
                    "engine_name": self._policy.engine_name,
                    "engine_version": self._policy.engine_version,
                    "source": "invoice.total",
                },
            ),
            ProposedJournalLineDecision(
                line_number=2,
                account_reference=self._policy.payable_account_reference,
                debit_amount=_ZERO,
                credit_amount=credit_amount,
                tax_code_reference=None,
                cost_centre_reference=None,
                explanation="Synthetic accounts payable offset line.",
                lineage={
                    "engine_name": self._policy.engine_name,
                    "engine_version": self._policy.engine_version,
                    "source": "invoice.total",
                },
            ),
        )
        total_debits = sum((line.debit_amount for line in lines), _ZERO)
        total_credits = sum((line.credit_amount for line in lines), _ZERO)
        is_balanced = total_debits == total_credits
        return ProposedJournalDecision(
            currency=currency,
            total_debits=total_debits,
            total_credits=total_credits,
            balance_status=(
                JournalBalanceStatus.BALANCED if is_balanced else JournalBalanceStatus.UNBALANCED
            ),
            is_balanced=is_balanced,
            explanation=(
                "Synthetic proposed journal for future human review; this is not an approval."
            ),
            lines=lines,
        )


def _required_field_findings(
    effective_values: dict[str, EffectiveExtractionValue],
    required_fields: tuple[str, ...],
) -> tuple[AccountingFindingDecision, ...]:
    findings: list[AccountingFindingDecision] = []
    for field_path in required_fields:
        if _field_text(effective_values, field_path) is None:
            findings.append(
                AccountingFindingDecision(
                    code=AccountingFindingCode.MISSING_REQUIRED_FIELD,
                    severity=AccountingFindingSeverity.ERROR,
                    field_path=field_path,
                    description="Required field is missing from the effective extraction values.",
                    evidence={"field_path": field_path},
                )
            )
    return tuple(findings)


def _unsupported_document_type_finding(document_type: str) -> AccountingFindingDecision:
    return AccountingFindingDecision(
        code=AccountingFindingCode.UNSUPPORTED_DOCUMENT_TYPE,
        severity=AccountingFindingSeverity.WARNING,
        field_path="document.type",
        description="Document type is not supported for Phase 4 accounting decisions.",
        evidence={
            "field_path": "document.type",
            "observed_document_type": document_type,
            "supported_document_types": tuple(sorted(_SUPPORTED_ACCOUNTING_DOCUMENT_TYPES)),
        },
    )


def _low_confidence_findings(
    effective_values: dict[str, EffectiveExtractionValue],
    field_paths: tuple[str, ...],
    threshold: Decimal,
) -> tuple[AccountingFindingDecision, ...]:
    findings: list[AccountingFindingDecision] = []
    for field_path in field_paths:
        value = effective_values.get(field_path)
        if value is None or value.confidence is None:
            continue
        if value.confidence < threshold:
            findings.append(
                AccountingFindingDecision(
                    code=AccountingFindingCode.LOW_EXTRACTION_CONFIDENCE,
                    severity=AccountingFindingSeverity.WARNING,
                    field_path=field_path,
                    description="Extraction confidence is below the synthetic review threshold.",
                    evidence={
                        "field_path": field_path,
                        "confidence": _decimal_to_string(value.confidence),
                        "threshold": _decimal_to_string(threshold),
                    },
                )
            )
    return tuple(findings)


def _accounting_monetary_values(
    effective_values: dict[str, EffectiveExtractionValue],
) -> tuple[dict[str, Decimal], tuple[AccountingFindingDecision, ...]]:
    values: dict[str, Decimal] = {}
    findings: list[AccountingFindingDecision] = []
    for field_path, require_positive in (
        ("invoice.total", True),
        ("invoice.subtotal", False),
        ("invoice.tax", False),
    ):
        value, finding = _accounting_money_value(
            effective_values,
            field_path,
            require_positive=require_positive,
        )
        if value is not None:
            values[field_path] = value
        if finding is not None:
            findings.append(finding)
    return values, tuple(findings)


def _accounting_money_value(
    effective_values: dict[str, EffectiveExtractionValue],
    field_path: str,
    *,
    require_positive: bool,
) -> tuple[Decimal | None, AccountingFindingDecision | None]:
    text = _field_text(effective_values, field_path)
    if text is None:
        return None, None
    try:
        value = Decimal(text)
    except InvalidOperation:
        return None, _invalid_monetary_value_finding(field_path, "not_a_finite_decimal")
    if not value.is_finite():
        return None, _invalid_monetary_value_finding(field_path, "not_a_finite_decimal")
    exponent = value.as_tuple().exponent
    if not isinstance(exponent, int):
        return None, _invalid_monetary_value_finding(field_path, "not_a_finite_decimal")
    if exponent < -_ACCOUNTING_MONEY_SCALE:
        return None, _invalid_monetary_value_finding(
            field_path,
            "unsupported_fractional_precision",
        )
    if value.copy_abs() > _MAX_ACCOUNTING_MONEY:
        return None, _invalid_monetary_value_finding(field_path, "outside_supported_range")
    if require_positive and value <= _ZERO:
        return None, _invalid_monetary_value_finding(field_path, "must_be_greater_than_zero")
    if not require_positive and value < _ZERO:
        return None, _invalid_monetary_value_finding(field_path, "must_not_be_negative")
    return value, None


def _invalid_monetary_value_finding(field_path: str, reason: str) -> AccountingFindingDecision:
    return AccountingFindingDecision(
        code=AccountingFindingCode.INVALID_MONETARY_VALUE,
        severity=AccountingFindingSeverity.ERROR,
        field_path=field_path,
        description="Extracted monetary value is outside the supported accounting domain.",
        evidence={
            "field_path": field_path,
            "reason": reason,
            "numeric_precision": _ACCOUNTING_MONEY_PRECISION,
            "numeric_scale": _ACCOUNTING_MONEY_SCALE,
            "maximum_absolute_value": _decimal_to_string(_MAX_ACCOUNTING_MONEY),
        },
    )


def _accounting_currency_value(
    effective_values: dict[str, EffectiveExtractionValue],
) -> tuple[str | None, AccountingFindingDecision | None]:
    currency = _field_text(effective_values, "invoice.currency")
    if currency is None:
        return None, None
    if len(currency) != 3 or not currency.isascii() or not currency.isalpha():
        return None, AccountingFindingDecision(
            code=AccountingFindingCode.INVALID_CURRENCY,
            severity=AccountingFindingSeverity.ERROR,
            field_path="invoice.currency",
            description="Extracted currency is outside the supported accounting format.",
            evidence={
                "field_path": "invoice.currency",
                "reason": "must_be_three_ascii_letters",
                "expected_format": "AAA",
            },
        )
    return currency.upper(), None


def _arithmetic_findings(
    effective_values: dict[str, EffectiveExtractionValue],
    monetary_values: dict[str, Decimal],
) -> tuple[AccountingFindingDecision, ...]:
    arithmetic_fields = ("invoice.subtotal", "invoice.tax", "invoice.total")
    if any(_field_text(effective_values, field_path) is None for field_path in arithmetic_fields):
        return ()
    if any(field_path not in monetary_values for field_path in arithmetic_fields):
        return ()
    subtotal = monetary_values["invoice.subtotal"]
    tax = monetary_values["invoice.tax"]
    total = monetary_values["invoice.total"]
    calculated_total = subtotal + tax
    if calculated_total == total:
        return ()
    return (
        AccountingFindingDecision(
            code=AccountingFindingCode.ARITHMETIC_MISMATCH,
            severity=AccountingFindingSeverity.ERROR,
            description="Invoice subtotal plus tax does not equal invoice total.",
            evidence={
                "formula": "invoice.subtotal + invoice.tax == invoice.total",
                "calculated_total": _decimal_to_string(calculated_total),
                "reported_total": _decimal_to_string(total),
            },
        ),
    )


def _duplicate_candidates(
    *,
    document_id: UUID,
    source_sha256: str,
    effective_values: dict[str, EffectiveExtractionValue],
    prior_snapshots: tuple[PriorDecisionSnapshot, ...],
    engine_name: str,
    engine_version: str,
) -> tuple[DuplicateCandidateDecision, ...]:
    candidates: list[DuplicateCandidateDecision] = []
    for snapshot in prior_snapshots:
        if snapshot.document_id == document_id:
            continue
        signals = _duplicate_signals(
            source_sha256=source_sha256,
            effective_values=effective_values,
            prior_snapshot=snapshot,
        )
        if not signals:
            continue
        confidence = (
            Decimal("0.9900")
            if "source_sha256" in signals
            else (Decimal(len(signals)) / _DUPLICATE_SCORE_DENOMINATOR)
        )
        if confidence < _DUPLICATE_THRESHOLD:
            continue
        candidates.append(
            DuplicateCandidateDecision(
                candidate_document_id=snapshot.document_id,
                candidate_extraction_run_id=snapshot.extraction_run_id,
                candidate_decision_run_id=snapshot.decision_run_id,
                confidence=confidence,
                explanation="Possible duplicate based on matching synthetic invoice signals.",
                evidence={"matched_signals": signals},
                detector_name=engine_name,
                detector_version=engine_version,
                model_version=None,
            )
        )
    return tuple(candidates)


def _duplicate_signals(
    *,
    source_sha256: str,
    effective_values: dict[str, EffectiveExtractionValue],
    prior_snapshot: PriorDecisionSnapshot,
) -> tuple[str, ...]:
    signals: list[str] = []
    if source_sha256 == prior_snapshot.source_sha256:
        signals.append("source_sha256")
    for field_path in (
        "supplier.name",
        "invoice.number",
        "invoice.date",
        "invoice.currency",
        "invoice.total",
    ):
        current = _field_text(effective_values, field_path)
        prior = _field_text(prior_snapshot.effective_values, field_path)
        if (
            current is not None
            and prior is not None
            and _comparison_value(field_path, current) == (_comparison_value(field_path, prior))
        ):
            signals.append(field_path)
    return tuple(signals)


def _supplier_candidate(
    *,
    entry: SupplierDirectoryEntry,
    confidence: Decimal,
    explanation: str,
    evidence: dict[str, object],
    engine_name: str,
    engine_version: str,
    is_confident: bool,
) -> SupplierMatchCandidateDecision:
    return SupplierMatchCandidateDecision(
        supplier_reference=entry.supplier_reference,
        supplier_name=entry.supplier_name,
        confidence=confidence,
        explanation=explanation,
        evidence=evidence,
        matcher_name=engine_name,
        matcher_version=engine_version,
        model_version=None,
        is_confident=is_confident,
    )


def _field_text(
    effective_values: dict[str, EffectiveExtractionValue],
    field_path: str,
) -> str | None:
    value = effective_values.get(field_path)
    if value is None:
        return None
    text = value.value.strip()
    return text or None


def _field_decimal(
    effective_values: dict[str, EffectiveExtractionValue],
    field_path: str,
) -> Decimal | None:
    text = _field_text(effective_values, field_path)
    if text is None:
        return None
    try:
        value = Decimal(text)
    except InvalidOperation:
        return None
    if not value.is_finite():
        return None
    return value


def _recommendation_value(
    recommendations: tuple[AccountingRecommendationDecision, ...],
    recommendation_type: AccountingRecommendationType,
) -> str | None:
    for recommendation in recommendations:
        if recommendation.recommendation_type == recommendation_type:
            return recommendation.recommended_value
    return None


def _normalize_name(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", " ", value.casefold())
    return " ".join(normalized.split())


def _comparison_value(field_path: str, value: str) -> str:
    if field_path == "supplier.name":
        return _normalize_name(value)
    return value.casefold().strip()


def _decimal_to_string(value: Decimal) -> str:
    return format(value, "f")
