from __future__ import annotations

import os
import threading
import time
import uuid
from collections.abc import Generator
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from queue import Queue

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ledgerpilot.documents.states import DocumentStatus
from ledgerpilot.documents.types import DocumentFileArea, DocumentMediaType
from ledgerpilot.extraction.states import ExtractionRunStatus
from ledgerpilot.extraction.types import ExtractionValueType
from ledgerpilot.identity.roles import Role
from ledgerpilot.persistence.models.documents import Document, DocumentFile
from ledgerpilot.persistence.models.extraction import (
    ExtractedField,
    ExtractionFieldCorrection,
    ExtractionRun,
)
from ledgerpilot.persistence.models.identity import ClientEntity, Firm, FirmMembership, User
from ledgerpilot.persistence.repositories.extraction import ExtractionRepository


@dataclass(frozen=True)
class PostgreSQLExtractionConstraintSeed:
    firm_a: Firm
    firm_b: Firm
    user_a: User
    user_b_same_firm: User
    user_firm_b: User
    membership_a: FirmMembership
    membership_b_same_firm: FirmMembership
    membership_firm_b: FirmMembership
    client_a: ClientEntity
    client_b_same_firm: ClientEntity
    firm_b_client: ClientEntity
    document_a: Document
    document_file_a: DocumentFile
    document_b_same_firm: Document
    document_file_b_same_firm: DocumentFile
    firm_b_document: Document
    run_a: ExtractionRun
    field_a: ExtractedField


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


def test_postgresql_enforces_extraction_tenant_file_field_and_correction_constraints(
    postgresql_engine: Engine,
) -> None:
    with Session(postgresql_engine, expire_on_commit=False) as session:
        seed = _seed_postgresql_extraction_constraint_data(session)

        _assert_integrity_error(
            session,
            _run(
                seed,
                document_id=seed.firm_b_document.id,
                document_file_id=seed.document_file_a.id,
            ),
        )
        _assert_integrity_error(
            session,
            _run(
                seed,
                document_id=seed.document_a.id,
                document_file_id=seed.document_file_b_same_firm.id,
            ),
        )
        _assert_integrity_error(
            session,
            ExtractedField(
                extraction_run_id=seed.run_a.id,
                firm_id=seed.firm_a.id,
                client_id=seed.client_b_same_firm.id,
                document_id=seed.document_a.id,
                field_path="invoice.number",
                value_type=ExtractionValueType.TEXT.value,
                raw_value="SYN-PG-002",
            ),
        )
        _assert_integrity_error(
            session,
            ExtractionFieldCorrection(
                field_id=seed.field_a.id,
                extraction_run_id=seed.run_a.id,
                firm_id=seed.firm_a.id,
                client_id=seed.client_b_same_firm.id,
                document_id=seed.document_a.id,
                corrected_by_user_id=seed.user_a.id,
                corrected_by_membership_id=seed.membership_a.id,
                revision_number=1,
                corrected_raw_value="SYN-PG-CORRECTED",
                corrected_value_type=ExtractionValueType.TEXT.value,
                reason="Synthetic wrong-client correction.",
            ),
        )
        _assert_integrity_error(
            session,
            ExtractionFieldCorrection(
                field_id=seed.field_a.id,
                extraction_run_id=seed.run_a.id,
                firm_id=seed.firm_a.id,
                client_id=seed.client_a.id,
                document_id=seed.document_a.id,
                corrected_by_user_id=seed.user_b_same_firm.id,
                corrected_by_membership_id=seed.membership_a.id,
                revision_number=1,
                corrected_raw_value="SYN-PG-CORRECTED",
                corrected_value_type=ExtractionValueType.TEXT.value,
                reason="Synthetic mismatched corrector attribution.",
            ),
        )

        valid_correction = ExtractionFieldCorrection(
            field_id=seed.field_a.id,
            extraction_run_id=seed.run_a.id,
            firm_id=seed.firm_a.id,
            client_id=seed.client_a.id,
            document_id=seed.document_a.id,
            corrected_by_user_id=seed.user_a.id,
            corrected_by_membership_id=seed.membership_a.id,
            revision_number=1,
            corrected_raw_value="SYN-PG-CORRECTED",
            corrected_value_type=ExtractionValueType.TEXT.value,
            reason="Synthetic valid correction.",
        )
        session.add(valid_correction)
        session.commit()

        _assert_integrity_error(
            session,
            ExtractionFieldCorrection(
                field_id=seed.field_a.id,
                extraction_run_id=seed.run_a.id,
                firm_id=seed.firm_a.id,
                client_id=seed.client_a.id,
                document_id=seed.document_a.id,
                corrected_by_user_id=seed.user_a.id,
                corrected_by_membership_id=seed.membership_a.id,
                revision_number=1,
                corrected_raw_value="SYN-PG-DUPLICATE",
                corrected_value_type=ExtractionValueType.TEXT.value,
                reason="Synthetic duplicate revision.",
            ),
        )
        _assert_integrity_error(
            session,
            ExtractedField(
                extraction_run_id=seed.run_a.id,
                firm_id=seed.firm_a.id,
                client_id=seed.client_a.id,
                document_id=seed.document_a.id,
                field_path="invoice.total",
                value_type=ExtractionValueType.DECIMAL.value,
                raw_value="RM 100.00",
                normalized_value="100.00",
                confidence=Decimal("1.1000"),
            ),
        )


def test_postgresql_serializes_simultaneous_correction_revision_allocation(
    postgresql_engine: Engine,
) -> None:
    with Session(postgresql_engine, expire_on_commit=False) as session:
        seed = _seed_postgresql_extraction_constraint_data(session)

    first_locked = threading.Event()
    outcomes: Queue[int | BaseException] = Queue()

    def add_correction(label: str, *, hold_lock: bool = False) -> None:
        try:
            with Session(postgresql_engine, expire_on_commit=False) as session:
                repository = ExtractionRepository(session)
                locked_field = repository.lock_field_for_correction(
                    firm_id=seed.firm_a.id,
                    client_id=seed.client_a.id,
                    document_id=seed.document_a.id,
                    run_id=seed.run_a.id,
                    field_id=seed.field_a.id,
                )
                assert locked_field is not None
                if hold_lock:
                    first_locked.set()
                    time.sleep(0.75)
                revision_number = repository.next_revision_number(field_id=locked_field.id)
                repository.add_correction(
                    ExtractionFieldCorrection(
                        field_id=locked_field.id,
                        extraction_run_id=locked_field.extraction_run_id,
                        firm_id=locked_field.firm_id,
                        client_id=locked_field.client_id,
                        document_id=locked_field.document_id,
                        corrected_by_user_id=seed.user_a.id,
                        corrected_by_membership_id=seed.membership_a.id,
                        revision_number=revision_number,
                        corrected_raw_value=f"SYN-PG-CONCURRENT-{label}",
                        corrected_value_type=ExtractionValueType.TEXT.value,
                        reason=f"Synthetic concurrent correction {label}.",
                    )
                )
                session.commit()
                outcomes.put(revision_number)
        except BaseException as exc:
            outcomes.put(exc)

    first = threading.Thread(target=add_correction, args=("first",), kwargs={"hold_lock": True})
    second = threading.Thread(target=add_correction, args=("second",))

    first.start()
    assert first_locked.wait(timeout=5)
    second.start()
    first.join(timeout=10)
    second.join(timeout=10)

    assert not first.is_alive()
    assert not second.is_alive()
    results = [outcomes.get_nowait(), outcomes.get_nowait()]
    errors = [result for result in results if isinstance(result, BaseException)]
    assert errors == []
    assert sorted(result for result in results if isinstance(result, int)) == [1, 2]

    with Session(postgresql_engine, expire_on_commit=False) as session:
        corrections = session.scalars(
            select(ExtractionFieldCorrection)
            .where(ExtractionFieldCorrection.field_id == seed.field_a.id)
            .order_by(ExtractionFieldCorrection.revision_number.asc())
        ).all()
    assert [correction.revision_number for correction in corrections] == [1, 2]
    assert [correction.corrected_raw_value for correction in corrections] == [
        "SYN-PG-CONCURRENT-first",
        "SYN-PG-CONCURRENT-second",
    ]


def _seed_postgresql_extraction_constraint_data(
    session: Session,
) -> PostgreSQLExtractionConstraintSeed:
    suffix = uuid.uuid4().hex
    firm_a = Firm(name=f"Synthetic Extraction PG Firm A {suffix}")
    firm_b = Firm(name=f"Synthetic Extraction PG Firm B {suffix}")
    user_a = User(external_subject=f"pg-extraction-user-a-{suffix}")
    user_b_same_firm = User(external_subject=f"pg-extraction-user-b-{suffix}")
    user_firm_b = User(external_subject=f"pg-extraction-firm-b-user-{suffix}")
    session.add_all([firm_a, firm_b, user_a, user_b_same_firm, user_firm_b])
    session.flush()

    membership_a = FirmMembership(
        user_id=user_a.id,
        firm_id=firm_a.id,
        role=Role.ACCOUNTANT.value,
    )
    membership_b_same_firm = FirmMembership(
        user_id=user_b_same_firm.id,
        firm_id=firm_a.id,
        role=Role.ACCOUNTANT.value,
    )
    membership_firm_b = FirmMembership(
        user_id=user_firm_b.id,
        firm_id=firm_b.id,
        role=Role.ACCOUNTANT.value,
    )
    client_a = ClientEntity(firm_id=firm_a.id, name=f"Synthetic Extraction Client A {suffix}")
    client_b_same_firm = ClientEntity(
        firm_id=firm_a.id,
        name=f"Synthetic Extraction Client B {suffix}",
    )
    firm_b_client = ClientEntity(
        firm_id=firm_b.id,
        name=f"Synthetic Extraction Client C {suffix}",
    )
    session.add_all(
        [
            membership_a,
            membership_b_same_firm,
            membership_firm_b,
            client_a,
            client_b_same_firm,
            firm_b_client,
        ]
    )
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
    firm_b_document, _ = _document_with_file(
        firm_id=firm_b.id,
        client_id=firm_b_client.id,
        user_id=user_firm_b.id,
        membership_id=membership_firm_b.id,
        suffix=suffix,
    )
    session.add_all(
        [
            document_a,
            document_b_same_firm,
            firm_b_document,
        ]
    )
    session.flush()
    session.add_all([document_file_a, document_file_b_same_firm])
    session.flush()

    run_a = _run(
        _SyntheticSeedProxy(
            firm_a=firm_a,
            user_a=user_a,
            membership_a=membership_a,
            client_a=client_a,
            document_a=document_a,
            document_file_a=document_file_a,
        )
    )
    session.add(run_a)
    session.flush()
    field_a = ExtractedField(
        extraction_run_id=run_a.id,
        firm_id=firm_a.id,
        client_id=client_a.id,
        document_id=document_a.id,
        field_path="invoice.number",
        value_type=ExtractionValueType.TEXT.value,
        raw_value="SYN-PG-001",
        confidence=Decimal("0.5000"),
        source_page_number=1,
    )
    session.add(field_a)
    session.commit()

    return PostgreSQLExtractionConstraintSeed(
        firm_a=firm_a,
        firm_b=firm_b,
        user_a=user_a,
        user_b_same_firm=user_b_same_firm,
        user_firm_b=user_firm_b,
        membership_a=membership_a,
        membership_b_same_firm=membership_b_same_firm,
        membership_firm_b=membership_firm_b,
        client_a=client_a,
        client_b_same_firm=client_b_same_firm,
        firm_b_client=firm_b_client,
        document_a=document_a,
        document_file_a=document_file_a,
        document_b_same_firm=document_b_same_firm,
        document_file_b_same_firm=document_file_b_same_firm,
        firm_b_document=firm_b_document,
        run_a=run_a,
        field_a=field_a,
    )


@dataclass(frozen=True)
class _SyntheticSeedProxy:
    firm_a: Firm
    user_a: User
    membership_a: FirmMembership
    client_a: ClientEntity
    document_a: Document
    document_file_a: DocumentFile


def _run(
    seed: PostgreSQLExtractionConstraintSeed | _SyntheticSeedProxy,
    *,
    document_id: uuid.UUID | None = None,
    document_file_id: uuid.UUID | None = None,
) -> ExtractionRun:
    now = datetime.now(UTC)
    return ExtractionRun(
        firm_id=seed.firm_a.id,
        client_id=seed.client_a.id,
        document_id=document_id or seed.document_a.id,
        document_file_id=document_file_id or seed.document_file_a.id,
        initiated_by_user_id=seed.user_a.id,
        initiated_by_membership_id=seed.membership_a.id,
        status=ExtractionRunStatus.SUCCEEDED.value,
        provider_name="synthetic_postgresql_provider",
        provider_version="0.1.0",
        model_version=None,
        extraction_schema_version="ledgerpilot.extraction.v1",
        source_sha256="a" * 64,
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
        submitted_filename=f"synthetic-extraction-{suffix}.pdf",
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
