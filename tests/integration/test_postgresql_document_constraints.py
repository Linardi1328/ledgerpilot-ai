from __future__ import annotations

import os
import uuid
from collections.abc import Generator
from dataclasses import dataclass

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ledgerpilot.documents.states import DocumentStatus
from ledgerpilot.documents.types import DocumentFileArea, DocumentMediaType
from ledgerpilot.identity.roles import Role
from ledgerpilot.persistence.models.documents import Document, DocumentFile
from ledgerpilot.persistence.models.identity import ClientEntity, Firm, FirmMembership, User


@dataclass(frozen=True)
class PostgreSQLConstraintSeed:
    firm_a: Firm
    firm_b: Firm
    user_a: User
    user_b_same_firm: User
    membership_a: FirmMembership
    membership_b_same_firm: FirmMembership
    client_a: ClientEntity
    client_b_same_firm: ClientEntity
    firm_b_client: ClientEntity
    stored_document: Document
    accepted_storage_key: str


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


def test_postgresql_enforces_document_tenant_and_file_constraints(
    postgresql_engine: Engine,
) -> None:
    with Session(postgresql_engine, expire_on_commit=False) as session:
        seed = _seed_postgresql_constraint_data(session)

        _assert_integrity_error(
            session,
            Document(
                firm_id=seed.firm_a.id,
                client_id=seed.firm_b_client.id,
                submitted_by_user_id=seed.user_a.id,
                submitted_by_membership_id=seed.membership_a.id,
                status=DocumentStatus.UPLOADED.value,
                submitted_filename="cross-firm-client.pdf",
            ),
        )
        _assert_integrity_error(
            session,
            Document(
                firm_id=seed.firm_a.id,
                client_id=seed.client_a.id,
                submitted_by_user_id=seed.user_a.id,
                submitted_by_membership_id=seed.membership_b_same_firm.id,
                status=DocumentStatus.UPLOADED.value,
                submitted_filename="same-firm-mismatched-submitter.pdf",
            ),
        )
        _assert_integrity_error(
            session,
            DocumentFile(
                document_id=seed.stored_document.id,
                firm_id=seed.firm_a.id,
                client_id=seed.client_b_same_firm.id,
                storage_backend="local",
                storage_area=DocumentFileArea.ACCEPTED.value,
                storage_key=_storage_key(seed.firm_a.id, seed.client_b_same_firm.id),
                size_bytes=1,
                sha256="b" * 64,
            ),
        )
        _assert_integrity_error(
            session,
            DocumentFile(
                document_id=seed.stored_document.id,
                firm_id=seed.firm_a.id,
                client_id=seed.client_a.id,
                storage_backend="local",
                storage_area=DocumentFileArea.ACCEPTED.value,
                storage_key=_storage_key(seed.firm_a.id, seed.client_a.id),
                size_bytes=1,
                sha256="c" * 64,
            ),
        )
        _assert_integrity_error(
            session,
            DocumentFile(
                document_id=seed.stored_document.id,
                firm_id=seed.firm_a.id,
                client_id=seed.client_a.id,
                storage_backend="local",
                storage_area=DocumentFileArea.QUARANTINE.value,
                storage_key=seed.accepted_storage_key,
                size_bytes=1,
                sha256="d" * 64,
            ),
        )


def _seed_postgresql_constraint_data(session: Session) -> PostgreSQLConstraintSeed:
    suffix = uuid.uuid4().hex
    firm_a = Firm(name=f"Synthetic PostgreSQL Firm A {suffix}")
    firm_b = Firm(name=f"Synthetic PostgreSQL Firm B {suffix}")
    user_a = User(external_subject=f"pg-user-a-{suffix}")
    user_b_same_firm = User(external_subject=f"pg-user-b-{suffix}")
    session.add_all([firm_a, firm_b, user_a, user_b_same_firm])
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
    client_a = ClientEntity(firm_id=firm_a.id, name=f"Synthetic PostgreSQL Client A {suffix}")
    client_b_same_firm = ClientEntity(
        firm_id=firm_a.id,
        name=f"Synthetic PostgreSQL Client B {suffix}",
    )
    firm_b_client = ClientEntity(
        firm_id=firm_b.id,
        name=f"Synthetic PostgreSQL Client C {suffix}",
    )
    session.add_all(
        [
            membership_a,
            membership_b_same_firm,
            client_a,
            client_b_same_firm,
            firm_b_client,
        ]
    )
    session.flush()

    stored_document = Document(
        firm_id=firm_a.id,
        client_id=client_a.id,
        submitted_by_user_id=user_a.id,
        submitted_by_membership_id=membership_a.id,
        status=DocumentStatus.STORED.value,
        submitted_filename="synthetic-postgresql.pdf",
        declared_media_type=DocumentMediaType.PDF.value,
        detected_media_type=DocumentMediaType.PDF.value,
        size_bytes=1,
        sha256="a" * 64,
    )
    session.add(stored_document)
    session.flush()

    accepted_storage_key = _storage_key(firm_a.id, client_a.id)
    session.add(
        DocumentFile(
            document_id=stored_document.id,
            firm_id=firm_a.id,
            client_id=client_a.id,
            storage_backend="local",
            storage_area=DocumentFileArea.ACCEPTED.value,
            storage_key=accepted_storage_key,
            size_bytes=1,
            sha256="a" * 64,
        )
    )
    session.commit()

    return PostgreSQLConstraintSeed(
        firm_a=firm_a,
        firm_b=firm_b,
        user_a=user_a,
        user_b_same_firm=user_b_same_firm,
        membership_a=membership_a,
        membership_b_same_firm=membership_b_same_firm,
        client_a=client_a,
        client_b_same_firm=client_b_same_firm,
        firm_b_client=firm_b_client,
        stored_document=stored_document,
        accepted_storage_key=accepted_storage_key,
    )


def _assert_integrity_error(session: Session, instance: object) -> None:
    session.add(instance)
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def _storage_key(firm_id: uuid.UUID, client_id: uuid.UUID) -> str:
    return f"{firm_id}/{client_id}/{uuid.uuid4()}/{uuid.uuid4().hex}"
