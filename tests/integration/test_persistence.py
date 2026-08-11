from __future__ import annotations

import pytest
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ledgerpilot.audit.service import AuditService
from ledgerpilot.audit.types import AuditEventType
from ledgerpilot.documents.states import DocumentStatus
from ledgerpilot.identity.roles import Role
from ledgerpilot.persistence.models.documents import Document
from ledgerpilot.persistence.repositories.identity import IdentityRepository
from tests.conftest import IdentitySeed


def test_session_rollback_works(db_session: Session) -> None:
    repository = IdentityRepository(db_session)
    firm = repository.add_firm(name="Synthetic Rollback Firm")
    db_session.flush()
    firm_id = firm.id
    db_session.rollback()

    assert repository.get_client_for_firm(firm_id=firm_id, client_id=firm_id) is None
    assert db_session.get(type(firm), firm_id) is None


def test_configured_engine_hides_sqlalchemy_parameter_values(engine: Engine) -> None:
    assert engine.hide_parameters


def test_unique_external_subject_constraint(db_session: Session) -> None:
    repository = IdentityRepository(db_session)
    repository.add_user(external_subject="duplicate-subject")
    repository.add_user(external_subject="duplicate-subject")
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_foreign_key_ownership_constraint_blocks_cross_firm_client_access(
    db_session: Session,
    identity_seed: IdentitySeed,
) -> None:
    repository = IdentityRepository(db_session)
    repository.grant_client_access(
        membership_id=identity_seed.accountant_membership.id,
        firm_id=identity_seed.firm_a.id,
        client_id=identity_seed.firm_b_client.id,
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_audit_event_ownership_constraint_blocks_cross_firm_client_reference(
    db_session: Session,
    identity_seed: IdentitySeed,
) -> None:
    AuditService(db_session).record_event(
        firm_id=identity_seed.firm_a.id,
        client_id=identity_seed.firm_b_client.id,
        event_type=AuditEventType.INFRASTRUCTURE_EVENT.value,
        target_type="test",
        target_id="cross-firm-client-reference",
    )

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_document_ownership_constraint_blocks_cross_firm_client_reference(
    db_session: Session,
    identity_seed: IdentitySeed,
) -> None:
    db_session.add(
        Document(
            firm_id=identity_seed.firm_a.id,
            client_id=identity_seed.firm_b_client.id,
            submitted_by_user_id=identity_seed.accountant.id,
            submitted_by_membership_id=identity_seed.accountant_membership.id,
            status=DocumentStatus.UPLOADED.value,
            submitted_filename="synthetic.pdf",
        )
    )

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_document_submitter_membership_must_belong_to_document_firm(
    db_session: Session,
    identity_seed: IdentitySeed,
) -> None:
    repository = IdentityRepository(db_session)
    firm_b_membership = repository.add_membership(
        user_id=identity_seed.outsider.id,
        firm_id=identity_seed.firm_b.id,
        role=Role.ACCOUNTANT.value,
    )
    db_session.flush()
    db_session.add(
        Document(
            firm_id=identity_seed.firm_a.id,
            client_id=identity_seed.client_a.id,
            submitted_by_user_id=identity_seed.outsider.id,
            submitted_by_membership_id=firm_b_membership.id,
            status=DocumentStatus.UPLOADED.value,
            submitted_filename="synthetic.pdf",
        )
    )

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_membership_uniqueness_per_user_and_firm(
    db_session: Session,
    identity_seed: IdentitySeed,
) -> None:
    repository = IdentityRepository(db_session)
    repository.add_membership(
        user_id=identity_seed.accountant.id,
        firm_id=identity_seed.firm_a.id,
        role=Role.AUDITOR.value,
    )
    with pytest.raises(IntegrityError):
        db_session.flush()
