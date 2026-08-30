from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from hashlib import sha256
from uuid import UUID, uuid5

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from ledgerpilot.accounting.states import AccountingDecisionRunStatus
from ledgerpilot.accounting.types import JournalBalanceStatus
from ledgerpilot.core.config import Environment, Settings
from ledgerpilot.documents.states import DocumentStatus
from ledgerpilot.documents.types import DocumentFileArea, DocumentMediaType
from ledgerpilot.extraction.states import ExtractionRunStatus
from ledgerpilot.extraction.types import ExtractionValueType
from ledgerpilot.identity.roles import Role
from ledgerpilot.persistence.models.accounting import (
    AccountingDecisionRun,
    ProposedJournal,
    ProposedJournalLine,
)
from ledgerpilot.persistence.models.documents import Document, DocumentFile
from ledgerpilot.persistence.models.extraction import ExtractedField, ExtractionRun
from ledgerpilot.persistence.models.identity import (
    ClientAccess,
    ClientEntity,
    Firm,
    FirmMembership,
    User,
)
from ledgerpilot.persistence.models.reconciliation import (
    BankImportBatchRecord,
    BankTransactionRecord,
)
from ledgerpilot.persistence.models.review import ReviewOutcome, ReviewTask
from ledgerpilot.persistence.session import create_engine_from_settings, create_session_factory
from ledgerpilot.reconciliation.types import BankTransactionDirection
from ledgerpilot.review.states import (
    ReviewEscalationState,
    ReviewOutcomeType,
    ReviewRiskClass,
    ReviewTaskStatus,
)

ALEMBIC_HEAD = "0008_phase_6_recon_review"
SEED_NAMESPACE = UUID("5b95ae52-d281-4aca-b1c7-9376fe9c0006")
FIRM_ID = UUID("11111111-1111-1111-1111-111111111111")
CLIENT_A_ID = UUID("22222222-2222-2222-2222-222222222222")
CLIENT_B_ID = UUID("33333333-3333-3333-3333-333333333333")

USER_IDS = {
    "accountant": UUID("aaaa0001-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
    "senior": UUID("aaaa0002-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
    "submitter": UUID("aaaa0003-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
    "auditor": UUID("aaaa0004-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
    "admin": UUID("aaaa0005-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
}
MEMBERSHIP_IDS = {
    "accountant": UUID("bbbb0001-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
    "senior": UUID("bbbb0002-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
    "submitter": UUID("bbbb0003-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
    "auditor": UUID("bbbb0004-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
    "admin": UUID("bbbb0005-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
}
SUBJECTS = {
    "accountant": "dev-accountant",
    "senior": "dev-senior-reviewer",
    "submitter": "dev-client-submitter",
    "auditor": "dev-auditor",
    "admin": "dev-firm-admin",
}
ROLES = {
    "accountant": Role.ACCOUNTANT,
    "senior": Role.SENIOR_REVIEWER,
    "submitter": Role.CLIENT_SUBMITTER,
    "auditor": Role.AUDITOR,
    "admin": Role.FIRM_ADMIN,
}


@dataclass(frozen=True)
class FeatureTestSeedSummary:
    firm_id: UUID
    client_a_id: UUID
    client_b_id: UUID
    approved_outcome_id: UUID
    candidate_transaction_id: UUID
    unmatched_transaction_id: UUID
    untouched_transaction_id: UUID
    client_b_transaction_id: UUID


def _id(key: str) -> UUID:
    return uuid5(SEED_NAMESPACE, key)


def _at(minute: int) -> datetime:
    return datetime(2026, 8, 30, 12, minute, tzinfo=UTC)


def _summary() -> FeatureTestSeedSummary:
    return FeatureTestSeedSummary(
        firm_id=FIRM_ID,
        client_a_id=CLIENT_A_ID,
        client_b_id=CLIENT_B_ID,
        approved_outcome_id=_id("target:outcome"),
        candidate_transaction_id=_id("bank:candidate"),
        unmatched_transaction_id=_id("bank:unmatched"),
        untouched_transaction_id=_id("bank:untouched"),
        client_b_transaction_id=_id("bank:client-b"),
    )


def _require_safe_environment(settings: Settings, *, confirmed: bool) -> None:
    if settings.env is Environment.PRODUCTION:
        raise RuntimeError("feature-test seed is disabled in production")
    if not settings.development_auth_is_enabled:
        raise RuntimeError("feature-test seed requires development authentication")
    if not confirmed:
        raise RuntimeError("explicit synthetic test database confirmation is required")


def _require_alembic_head(session: Session) -> None:
    try:
        version = session.execute(text("select version_num from alembic_version")).scalar_one()
    except Exception as exc:
        raise RuntimeError("database must be migrated before feature-test seeding") from exc
    if version != ALEMBIC_HEAD:
        raise RuntimeError(f"database must be migrated to {ALEMBIC_HEAD}")


def _validate_existing_seed(session: Session) -> FeatureTestSeedSummary:
    summary = _summary()
    firm = session.get(Firm, FIRM_ID)
    if firm is None or firm.name != "LedgerPilot Feature Test Firm [Synthetic]":
        raise RuntimeError("existing feature-test seed marker is inconsistent")
    for key, user_id in USER_IDS.items():
        user = session.get(User, user_id)
        membership = session.get(FirmMembership, MEMBERSHIP_IDS[key])
        if user is None or user.external_subject != SUBJECTS[key] or not user.is_active:
            raise RuntimeError("existing feature-test user seed is inconsistent")
        if (
            membership is None
            or membership.user_id != user_id
            or membership.firm_id != FIRM_ID
            or membership.role != ROLES[key].value
            or not membership.is_active
        ):
            raise RuntimeError("existing feature-test membership seed is inconsistent")
    outcome = session.get(ReviewOutcome, summary.approved_outcome_id)
    if outcome is None or outcome.outcome_type != ReviewOutcomeType.APPROVED.value:
        raise RuntimeError("existing feature-test approved outcome seed is inconsistent")
    for transaction_id in (
        summary.candidate_transaction_id,
        summary.unmatched_transaction_id,
        summary.untouched_transaction_id,
        summary.client_b_transaction_id,
    ):
        if session.get(BankTransactionRecord, transaction_id) is None:
            raise RuntimeError("existing feature-test bank transaction seed is inconsistent")
    return summary


def _ensure_no_partial_seed(session: Session) -> None:
    if session.get(Firm, FIRM_ID) is not None:
        return
    if any(session.get(User, user_id) is not None for user_id in USER_IDS.values()):
        raise RuntimeError("partial feature-test identity seed detected")
    existing_subject = session.scalars(
        select(User).where(User.external_subject.in_(tuple(SUBJECTS.values())))
    ).first()
    if existing_subject is not None:
        raise RuntimeError("feature-test development subject already exists")


def _add_identity(session: Session) -> None:
    session.add(
        Firm(
            id=FIRM_ID,
            name="LedgerPilot Feature Test Firm [Synthetic]",
            status="active",
            created_at=_at(0),
            updated_at=_at(0),
        )
    )
    session.add_all(
        [
            ClientEntity(
                id=CLIENT_A_ID,
                firm_id=FIRM_ID,
                name="Alpha Trading Sdn Bhd [Synthetic Feature Test]",
                status="active",
                created_at=_at(1),
                updated_at=_at(1),
            ),
            ClientEntity(
                id=CLIENT_B_ID,
                firm_id=FIRM_ID,
                name="Beta Logistics Bhd [Synthetic Feature Test]",
                status="active",
                created_at=_at(2),
                updated_at=_at(2),
            ),
        ]
    )
    for minute, key in enumerate(
        ("accountant", "senior", "submitter", "auditor", "admin"),
        3,
    ):
        session.add(
            User(
                id=USER_IDS[key],
                external_subject=SUBJECTS[key],
                is_active=True,
                created_at=_at(minute),
                updated_at=_at(minute),
            )
        )
        session.add(
            FirmMembership(
                id=MEMBERSHIP_IDS[key],
                user_id=USER_IDS[key],
                firm_id=FIRM_ID,
                role=ROLES[key].value,
                is_active=True,
                created_at=_at(minute),
            )
        )
    access = (
        ("accountant", CLIENT_A_ID),
        ("accountant", CLIENT_B_ID),
        ("senior", CLIENT_A_ID),
        ("senior", CLIENT_B_ID),
        ("auditor", CLIENT_A_ID),
        ("auditor", CLIENT_B_ID),
        ("submitter", CLIENT_A_ID),
    )
    for minute, (key, client_id) in enumerate(access, 10):
        session.add(
            ClientAccess(
                id=_id(f"access:{key}:{client_id}"),
                membership_id=MEMBERSHIP_IDS[key],
                firm_id=FIRM_ID,
                client_id=client_id,
                is_active=True,
                created_at=_at(minute),
            )
        )


def _add_approved_target(session: Session) -> UUID:
    document_id = _id("target:document")
    file_id = _id("target:file")
    extraction_id = _id("target:extraction")
    decision_id = _id("target:decision")
    journal_id = _id("target:journal")
    task_id = _id("target:review-task")
    outcome_id = _id("target:outcome")
    digest = sha256(b"ledgerpilot-phase6-feature-test-approved-target").hexdigest()
    created_at = _at(20)

    session.add(
        Document(
            id=document_id,
            firm_id=FIRM_ID,
            client_id=CLIENT_A_ID,
            submitted_by_user_id=USER_IDS["accountant"],
            submitted_by_membership_id=MEMBERSHIP_IDS["accountant"],
            status=DocumentStatus.STORED.value,
            submitted_filename="SYN-FT-INV-001.synthetic.pdf",
            declared_media_type=DocumentMediaType.PDF.value,
            detected_media_type=DocumentMediaType.PDF.value,
            size_bytes=128,
            sha256=digest,
            failure_code=None,
            created_at=created_at,
            updated_at=created_at,
        )
    )
    session.add(
        DocumentFile(
            id=file_id,
            document_id=document_id,
            firm_id=FIRM_ID,
            client_id=CLIENT_A_ID,
            storage_backend="local",
            storage_area=DocumentFileArea.ACCEPTED.value,
            storage_key="phase6-feature-test/SYN-FT-INV-001.synthetic.pdf",
            size_bytes=128,
            sha256=digest,
            created_at=created_at,
        )
    )
    session.add(
        ExtractionRun(
            id=extraction_id,
            firm_id=FIRM_ID,
            client_id=CLIENT_A_ID,
            document_id=document_id,
            document_file_id=file_id,
            initiated_by_user_id=USER_IDS["accountant"],
            initiated_by_membership_id=MEMBERSHIP_IDS["accountant"],
            status=ExtractionRunStatus.SUCCEEDED.value,
            provider_name="synthetic_feature_test_seed",
            provider_version="1.0",
            model_version=None,
            extraction_schema_version="ledgerpilot.extraction.v1",
            source_sha256=digest,
            started_at=created_at,
            completed_at=created_at,
            failure_code=None,
            request_id="seed-approved-target-extraction",
            created_at=created_at,
        )
    )
    fields = (
        ("document.type", ExtractionValueType.TEXT.value, "purchase_invoice"),
        (
            "supplier.name",
            ExtractionValueType.TEXT.value,
            "Synthetic Feature Test Supplier Sdn Bhd",
        ),
        ("invoice.number", ExtractionValueType.TEXT.value, "SYN-FT-INV-001"),
        ("invoice.date", ExtractionValueType.DATE.value, "2026-08-11"),
        ("invoice.currency", ExtractionValueType.TEXT.value, "MYR"),
        ("invoice.total", ExtractionValueType.DECIMAL.value, "100.0000"),
    )
    for field_path, value_type, value in fields:
        session.add(
            ExtractedField(
                id=_id(f"target:field:{field_path}"),
                extraction_run_id=extraction_id,
                firm_id=FIRM_ID,
                client_id=CLIENT_A_ID,
                document_id=document_id,
                field_path=field_path,
                value_type=value_type,
                raw_value=value,
                normalized_value=value,
                confidence=Decimal("1.0000"),
                source_page_number=1,
                source_locator={"synthetic": True},
                created_at=created_at,
            )
        )
    session.add(
        AccountingDecisionRun(
            id=decision_id,
            firm_id=FIRM_ID,
            client_id=CLIENT_A_ID,
            document_id=document_id,
            extraction_run_id=extraction_id,
            initiated_by_user_id=USER_IDS["accountant"],
            initiated_by_membership_id=MEMBERSHIP_IDS["accountant"],
            status=AccountingDecisionRunStatus.SUCCEEDED.value,
            engine_name="synthetic_feature_test_seed",
            engine_version="1.0",
            model_version=None,
            source_sha256=digest,
            started_at=created_at,
            completed_at=created_at,
            failure_code=None,
            request_id="seed-approved-target-decision",
            created_at=created_at,
        )
    )
    session.add(
        ProposedJournal(
            id=journal_id,
            decision_run_id=decision_id,
            firm_id=FIRM_ID,
            client_id=CLIENT_A_ID,
            document_id=document_id,
            extraction_run_id=extraction_id,
            currency="MYR",
            total_debits=Decimal("100.0000"),
            total_credits=Decimal("100.0000"),
            balance_status=JournalBalanceStatus.BALANCED.value,
            is_balanced=True,
            explanation="Synthetic feature-test purchase invoice journal.",
            created_at=created_at,
        )
    )
    journal_lines = (
        (
            1,
            "SYN-6000-FEATURE-TEST-EXPENSE",
            Decimal("100.0000"),
            Decimal("0.0000"),
        ),
        (
            2,
            "SYN-2000-FEATURE-TEST-PAYABLE",
            Decimal("0.0000"),
            Decimal("100.0000"),
        ),
    )
    for line_number, account, debit, credit in journal_lines:
        session.add(
            ProposedJournalLine(
                id=_id(f"target:journal-line:{line_number}"),
                proposed_journal_id=journal_id,
                decision_run_id=decision_id,
                firm_id=FIRM_ID,
                client_id=CLIENT_A_ID,
                document_id=document_id,
                extraction_run_id=extraction_id,
                line_number=line_number,
                account_reference=account,
                debit_amount=debit,
                credit_amount=credit,
                tax_code_reference=None,
                cost_centre_reference=None,
                explanation="Synthetic feature-test journal line.",
                lineage_json={"seed": "phase6-feature-test"},
                created_at=created_at,
            )
        )
    session.add(
        ReviewTask(
            id=task_id,
            firm_id=FIRM_ID,
            client_id=CLIENT_A_ID,
            decision_run_id=decision_id,
            document_id=document_id,
            extraction_run_id=extraction_id,
            created_by_user_id=USER_IDS["accountant"],
            created_by_membership_id=MEMBERSHIP_IDS["accountant"],
            owner_user_id=USER_IDS["accountant"],
            owner_membership_id=MEMBERSHIP_IDS["accountant"],
            status=ReviewTaskStatus.APPROVED.value,
            risk_class=ReviewRiskClass.ORDINARY.value,
            escalation_state=ReviewEscalationState.NONE.value,
            escalated_at=None,
            request_id="seed-approved-target-review",
            created_at=created_at,
            updated_at=created_at,
        )
    )
    session.add(
        ReviewOutcome(
            id=outcome_id,
            review_task_id=task_id,
            firm_id=FIRM_ID,
            client_id=CLIENT_A_ID,
            decision_run_id=decision_id,
            document_id=document_id,
            extraction_run_id=extraction_id,
            actor_user_id=USER_IDS["accountant"],
            actor_membership_id=MEMBERSHIP_IDS["accountant"],
            outcome_type=ReviewOutcomeType.APPROVED.value,
            proposed_journal_id=journal_id,
            source_correction_count=0,
            reason=None,
            request_id="seed-approved-target-approval",
            created_at=created_at,
        )
    )
    return outcome_id


def _add_bank_batch(
    session: Session,
    *,
    client_id: UUID,
    key: str,
    transactions: tuple[tuple[str, date, Decimal, str, str], ...],
) -> None:
    batch_id = _id(f"bank:{key}:batch")
    account_reference = f"synthetic-feature-test-clearing-{key}"
    session.add(
        BankImportBatchRecord(
            id=batch_id,
            firm_id=FIRM_ID,
            client_id=client_id,
            provider_name="synthetic_bank_feed",
            provider_version="1.0",
            provider_batch_reference=f"phase6-feature-test-{key}-v1",
            account_reference=account_reference,
            period_start=date(2026, 8, 1),
            period_end=date(2026, 8, 31),
            created_at=_at(30),
        )
    )
    for tx_key, booking_date, amount, reference, counterparty in transactions:
        session.add(
            BankTransactionRecord(
                id=_id(f"bank:{tx_key}"),
                import_batch_id=batch_id,
                firm_id=FIRM_ID,
                client_id=client_id,
                provider_name="synthetic_bank_feed",
                account_reference=account_reference,
                source_transaction_id=f"phase6-feature-test-{tx_key}",
                booking_date=booking_date,
                value_date=booking_date,
                direction=BankTransactionDirection.DEBIT.value,
                amount=amount,
                currency="MYR",
                description="Synthetic feature-test supplier settlement.",
                reference=reference,
                counterparty_name=counterparty,
                created_at=_at(31),
            )
        )


def _add_bank_transactions(session: Session) -> None:
    _add_bank_batch(
        session,
        client_id=CLIENT_A_ID,
        key="client-a",
        transactions=(
            (
                "candidate",
                date(2026, 8, 11),
                Decimal("100.0000"),
                "SYN-FT-INV-001",
                "Synthetic Feature Test Supplier Sdn Bhd",
            ),
            (
                "unmatched",
                date(2026, 8, 12),
                Decimal("73.2500"),
                "SYN-FT-NO-MATCH-001",
                "Synthetic No Match Supplier",
            ),
            (
                "untouched",
                date(2026, 8, 13),
                Decimal("55.5500"),
                "SYN-FT-UNTOUCHED-001",
                "Synthetic Untouched Supplier",
            ),
        ),
    )
    _add_bank_batch(
        session,
        client_id=CLIENT_B_ID,
        key="client-b",
        transactions=(
            (
                "client-b",
                date(2026, 8, 11),
                Decimal("240.0000"),
                "SYN-FT-BETA-001",
                "Synthetic Beta Supplier",
            ),
        ),
    )


def seed_phase6_feature_test(
    session: Session,
    settings: Settings,
    *,
    confirm_synthetic_test_database: bool,
    require_alembic_head: bool = True,
) -> FeatureTestSeedSummary:
    _require_safe_environment(settings, confirmed=confirm_synthetic_test_database)
    if require_alembic_head:
        _require_alembic_head(session)
    if session.get(Firm, FIRM_ID) is not None:
        return _validate_existing_seed(session)
    _ensure_no_partial_seed(session)
    try:
        _add_identity(session)
        session.flush()
        _add_approved_target(session)
        _add_bank_transactions(session)
        session.commit()
    except Exception:
        session.rollback()
        raise
    return _validate_existing_seed(session)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed the synthetic Phase 6 feature-test database."
    )
    parser.add_argument(
        "--confirm-synthetic-test-database",
        action="store_true",
        help=(
            "Required acknowledgement that the configured database is isolated and synthetic-only."
        ),
    )
    args = parser.parse_args()
    settings = Settings()
    engine = create_engine_from_settings(settings)
    session_factory = create_session_factory(engine)
    try:
        with session_factory() as session:
            summary = seed_phase6_feature_test(
                session,
                settings,
                confirm_synthetic_test_database=args.confirm_synthetic_test_database,
            )
    finally:
        engine.dispose()
    print("Phase 6 feature-test seed ready.")
    print(f"firm_id={summary.firm_id}")
    print(f"client_a_id={summary.client_a_id}")
    print(f"client_b_id={summary.client_b_id}")
    print("subjects=" + ",".join(SUBJECTS.values()))


if __name__ == "__main__":
    main()
