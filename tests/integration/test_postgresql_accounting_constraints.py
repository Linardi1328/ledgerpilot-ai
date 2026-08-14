from __future__ import annotations

import os
import uuid
from collections.abc import Generator
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ledgerpilot.accounting.states import AccountingDecisionRunStatus
from ledgerpilot.accounting.types import (
    AccountingFindingCode,
    AccountingFindingSeverity,
    AccountingRecommendationType,
    JournalBalanceStatus,
)
from ledgerpilot.documents.states import DocumentStatus
from ledgerpilot.documents.types import DocumentFileArea, DocumentMediaType
from ledgerpilot.extraction.states import ExtractionRunStatus
from ledgerpilot.identity.roles import Role
from ledgerpilot.persistence.models.accounting import (
    AccountingDecisionFinding,
    AccountingDecisionRun,
    AccountingDuplicateCandidate,
    AccountingRecommendation,
    ProposedJournal,
    ProposedJournalLine,
)
from ledgerpilot.persistence.models.documents import Document, DocumentFile
from ledgerpilot.persistence.models.extraction import ExtractionRun
from ledgerpilot.persistence.models.identity import ClientEntity, Firm, FirmMembership, User


@dataclass(frozen=True)
class PostgreSQLAccountingConstraintSeed:
    firm_a: Firm
    firm_b: Firm
    user_a: User
    user_firm_b: User
    membership_a: FirmMembership
    membership_firm_b: FirmMembership
    client_a: ClientEntity
    client_b_same_firm: ClientEntity
    firm_b_client: ClientEntity
    document_a: Document
    document_file_a: DocumentFile
    document_b_same_firm: Document
    document_file_b_same_firm: DocumentFile
    firm_b_document: Document
    firm_b_document_file: DocumentFile
    run_a: ExtractionRun
    run_b_same_firm: ExtractionRun
    firm_b_run: ExtractionRun
    decision_a: AccountingDecisionRun
    decision_b_same_firm: AccountingDecisionRun


@pytest.fixture(scope="module")
def postgresql_engine() -> Generator[Engine]:
    database_url = os.environ.get("LEDGERPILOT_DATABASE_URL")
    if not database_url:
        pytest.skip("LEDGERPILOT_DATABASE_URL is not set for PostgreSQL constraint tests")

    url = make_url(database_url)
    if not url.drivername.startswith("postgresql"):
        pytest.skip("PostgreSQL constraint tests require a PostgreSQL database URL")

    engine = create_engine(database_url, future=True, hide_parameters=True)
    try:
        yield engine
    finally:
        engine.dispose()


def test_postgresql_enforces_accounting_decision_ownership_and_invariants(
    postgresql_engine: Engine,
) -> None:
    with Session(postgresql_engine, expire_on_commit=False) as session:
        seed = _seed_postgresql_accounting_constraint_data(session)

        _assert_integrity_error(
            session,
            _decision_run(seed, extraction_run=seed.run_b_same_firm),
        )
        _assert_integrity_error(
            session,
            AccountingDecisionFinding(
                decision_run_id=seed.decision_a.id,
                firm_id=seed.firm_a.id,
                client_id=seed.client_b_same_firm.id,
                document_id=seed.document_a.id,
                extraction_run_id=seed.run_a.id,
                code=AccountingFindingCode.MISSING_REQUIRED_FIELD.value,
                severity=AccountingFindingSeverity.ERROR.value,
                field_path="invoice.number",
                description="Synthetic wrong-client finding.",
                evidence_json={},
            ),
        )
        _assert_integrity_error(
            session,
            AccountingRecommendation(
                decision_run_id=seed.decision_a.id,
                firm_id=seed.firm_a.id,
                client_id=seed.client_a.id,
                document_id=seed.document_a.id,
                extraction_run_id=seed.run_a.id,
                recommendation_type=AccountingRecommendationType.GL_ACCOUNT.value,
                recommended_value="expense:synthetic",
                confidence=Decimal("1.1000"),
                explanation="Synthetic invalid confidence.",
                evidence_json={},
                rule_name="synthetic_rule",
                rule_version="0.1.0",
            ),
        )

        journal = ProposedJournal(
            decision_run_id=seed.decision_a.id,
            firm_id=seed.firm_a.id,
            client_id=seed.client_a.id,
            document_id=seed.document_a.id,
            extraction_run_id=seed.run_a.id,
            currency="MYR",
            total_debits=Decimal("100.0000"),
            total_credits=Decimal("100.0000"),
            balance_status=JournalBalanceStatus.BALANCED.value,
            is_balanced=True,
            explanation="Synthetic balanced journal.",
        )
        session.add(journal)
        session.commit()

        _assert_integrity_error(
            session,
            ProposedJournal(
                decision_run_id=seed.decision_b_same_firm.id,
                firm_id=seed.firm_a.id,
                client_id=seed.client_b_same_firm.id,
                document_id=seed.document_b_same_firm.id,
                extraction_run_id=seed.run_b_same_firm.id,
                currency="MYR",
                total_debits=Decimal("100.0000"),
                total_credits=Decimal("99.9900"),
                balance_status=JournalBalanceStatus.BALANCED.value,
                is_balanced=True,
                explanation="Synthetic inconsistent journal.",
            ),
        )
        _assert_integrity_error(
            session,
            ProposedJournalLine(
                proposed_journal_id=journal.id,
                decision_run_id=seed.decision_a.id,
                firm_id=seed.firm_a.id,
                client_id=seed.client_a.id,
                document_id=seed.document_a.id,
                extraction_run_id=seed.run_a.id,
                line_number=1,
                account_reference="expense:synthetic",
                debit_amount=Decimal("100.0000"),
                credit_amount=Decimal("1.0000"),
                explanation="Synthetic invalid double-sided line.",
                lineage_json={},
            ),
        )
        _assert_integrity_error(
            session,
            ProposedJournalLine(
                proposed_journal_id=journal.id,
                decision_run_id=seed.decision_a.id,
                firm_id=seed.firm_a.id,
                client_id=seed.client_b_same_firm.id,
                document_id=seed.document_a.id,
                extraction_run_id=seed.run_a.id,
                line_number=2,
                account_reference="expense:synthetic",
                debit_amount=Decimal("100.0000"),
                credit_amount=Decimal("0.0000"),
                explanation="Synthetic wrong-client line.",
                lineage_json={},
            ),
        )
        _assert_integrity_error(
            session,
            AccountingDuplicateCandidate(
                decision_run_id=seed.decision_a.id,
                firm_id=seed.firm_a.id,
                client_id=seed.client_a.id,
                document_id=seed.document_a.id,
                extraction_run_id=seed.run_a.id,
                candidate_document_id=seed.document_b_same_firm.id,
                candidate_extraction_run_id=seed.run_b_same_firm.id,
                candidate_decision_run_id=seed.decision_b_same_firm.id,
                confidence=Decimal("0.9000"),
                explanation="Synthetic cross-client duplicate candidate.",
                evidence_json={"matched_signals": ["invoice.number"]},
                detector_name="synthetic_detector",
                detector_version="0.1.0",
            ),
        )


def _seed_postgresql_accounting_constraint_data(
    session: Session,
) -> PostgreSQLAccountingConstraintSeed:
    suffix = uuid.uuid4().hex
    firm_a = Firm(name=f"Synthetic Accounting PG Firm A {suffix}")
    firm_b = Firm(name=f"Synthetic Accounting PG Firm B {suffix}")
    user_a = User(external_subject=f"pg-accounting-user-a-{suffix}")
    user_firm_b = User(external_subject=f"pg-accounting-user-b-{suffix}")
    session.add_all([firm_a, firm_b, user_a, user_firm_b])
    session.flush()

    membership_a = FirmMembership(
        user_id=user_a.id,
        firm_id=firm_a.id,
        role=Role.ACCOUNTANT.value,
    )
    membership_firm_b = FirmMembership(
        user_id=user_firm_b.id,
        firm_id=firm_b.id,
        role=Role.ACCOUNTANT.value,
    )
    client_a = ClientEntity(firm_id=firm_a.id, name=f"Synthetic Accounting Client A {suffix}")
    client_b_same_firm = ClientEntity(
        firm_id=firm_a.id,
        name=f"Synthetic Accounting Client B {suffix}",
    )
    firm_b_client = ClientEntity(
        firm_id=firm_b.id,
        name=f"Synthetic Accounting Client C {suffix}",
    )
    session.add_all([membership_a, membership_firm_b, client_a, client_b_same_firm, firm_b_client])
    session.flush()

    document_a, document_file_a = _document_with_file(
        firm_id=firm_a.id,
        client_id=client_a.id,
        user_id=user_a.id,
        membership_id=membership_a.id,
        suffix=suffix,
    )
    document_b_same_firm, document_file_b_same_firm = _document_with_file(
        firm_id=firm_a.id,
        client_id=client_b_same_firm.id,
        user_id=user_a.id,
        membership_id=membership_a.id,
        suffix=suffix,
    )
    firm_b_document, firm_b_document_file = _document_with_file(
        firm_id=firm_b.id,
        client_id=firm_b_client.id,
        user_id=user_firm_b.id,
        membership_id=membership_firm_b.id,
        suffix=suffix,
    )
    session.add_all([document_a, document_b_same_firm, firm_b_document])
    session.flush()
    session.add_all([document_file_a, document_file_b_same_firm, firm_b_document_file])
    session.flush()

    run_a = _extraction_run(
        firm_id=firm_a.id,
        client_id=client_a.id,
        document_id=document_a.id,
        document_file_id=document_file_a.id,
        user_id=user_a.id,
        membership_id=membership_a.id,
        source_sha256=document_file_a.sha256,
    )
    run_b_same_firm = _extraction_run(
        firm_id=firm_a.id,
        client_id=client_b_same_firm.id,
        document_id=document_b_same_firm.id,
        document_file_id=document_file_b_same_firm.id,
        user_id=user_a.id,
        membership_id=membership_a.id,
        source_sha256=document_file_b_same_firm.sha256,
    )
    firm_b_run = _extraction_run(
        firm_id=firm_b.id,
        client_id=firm_b_client.id,
        document_id=firm_b_document.id,
        document_file_id=firm_b_document_file.id,
        user_id=user_firm_b.id,
        membership_id=membership_firm_b.id,
        source_sha256=firm_b_document_file.sha256,
    )
    session.add_all([run_a, run_b_same_firm, firm_b_run])
    session.flush()

    decision_a = _decision_run(
        _SeedProxy(
            firm_a=firm_a,
            user_a=user_a,
            membership_a=membership_a,
            client_a=client_a,
            document_a=document_a,
            run_a=run_a,
        )
    )
    decision_b_same_firm = _decision_run(
        _SeedProxy(
            firm_a=firm_a,
            user_a=user_a,
            membership_a=membership_a,
            client_a=client_b_same_firm,
            document_a=document_b_same_firm,
            run_a=run_b_same_firm,
        )
    )
    session.add_all([decision_a, decision_b_same_firm])
    session.commit()

    return PostgreSQLAccountingConstraintSeed(
        firm_a=firm_a,
        firm_b=firm_b,
        user_a=user_a,
        user_firm_b=user_firm_b,
        membership_a=membership_a,
        membership_firm_b=membership_firm_b,
        client_a=client_a,
        client_b_same_firm=client_b_same_firm,
        firm_b_client=firm_b_client,
        document_a=document_a,
        document_file_a=document_file_a,
        document_b_same_firm=document_b_same_firm,
        document_file_b_same_firm=document_file_b_same_firm,
        firm_b_document=firm_b_document,
        firm_b_document_file=firm_b_document_file,
        run_a=run_a,
        run_b_same_firm=run_b_same_firm,
        firm_b_run=firm_b_run,
        decision_a=decision_a,
        decision_b_same_firm=decision_b_same_firm,
    )


@dataclass(frozen=True)
class _SeedProxy:
    firm_a: Firm
    user_a: User
    membership_a: FirmMembership
    client_a: ClientEntity
    document_a: Document
    run_a: ExtractionRun


def _decision_run(
    seed: PostgreSQLAccountingConstraintSeed | _SeedProxy,
    *,
    extraction_run: ExtractionRun | None = None,
) -> AccountingDecisionRun:
    run = extraction_run or seed.run_a
    now = datetime.now(UTC)
    return AccountingDecisionRun(
        firm_id=seed.firm_a.id,
        client_id=seed.client_a.id,
        document_id=seed.document_a.id,
        extraction_run_id=run.id,
        initiated_by_user_id=seed.user_a.id,
        initiated_by_membership_id=seed.membership_a.id,
        status=AccountingDecisionRunStatus.SUCCEEDED.value,
        engine_name="synthetic_accounting_decision_engine",
        engine_version="0.1.0",
        model_version=None,
        source_sha256=run.source_sha256,
        started_at=now,
        completed_at=now,
    )


def _extraction_run(
    *,
    firm_id: uuid.UUID,
    client_id: uuid.UUID,
    document_id: uuid.UUID,
    document_file_id: uuid.UUID,
    user_id: uuid.UUID,
    membership_id: uuid.UUID,
    source_sha256: str,
) -> ExtractionRun:
    now = datetime.now(UTC)
    return ExtractionRun(
        firm_id=firm_id,
        client_id=client_id,
        document_id=document_id,
        document_file_id=document_file_id,
        initiated_by_user_id=user_id,
        initiated_by_membership_id=membership_id,
        status=ExtractionRunStatus.SUCCEEDED.value,
        provider_name="synthetic_postgresql_provider",
        provider_version="0.1.0",
        model_version=None,
        extraction_schema_version="ledgerpilot.extraction.v1",
        source_sha256=source_sha256,
        started_at=now,
        completed_at=now,
    )


def _document_with_file(
    *,
    firm_id: uuid.UUID,
    client_id: uuid.UUID,
    user_id: uuid.UUID,
    membership_id: uuid.UUID,
    suffix: str,
) -> tuple[Document, DocumentFile]:
    document = Document(
        id=uuid.uuid4(),
        firm_id=firm_id,
        client_id=client_id,
        submitted_by_user_id=user_id,
        submitted_by_membership_id=membership_id,
        status=DocumentStatus.STORED.value,
        submitted_filename=f"synthetic-accounting-{suffix}.pdf",
        declared_media_type=DocumentMediaType.PDF.value,
        detected_media_type=DocumentMediaType.PDF.value,
        size_bytes=1,
        sha256="a" * 64,
    )
    document_file = DocumentFile(
        id=uuid.uuid4(),
        document_id=document.id,
        firm_id=firm_id,
        client_id=client_id,
        storage_backend="local",
        storage_area=DocumentFileArea.ACCEPTED.value,
        storage_key=f"{firm_id}/{client_id}/{document.id}/{uuid.uuid4().hex}",
        size_bytes=1,
        sha256="a" * 64,
    )
    return document, document_file


def _assert_integrity_error(session: Session, instance: object) -> None:
    session.add(instance)
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()
