from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from ledgerpilot.audit.service import AuditService, UnsafeAuditMetadataError
from ledgerpilot.audit.types import AuditEventType
from ledgerpilot.persistence.repositories.audit import AuditRepository
from tests.conftest import IdentitySeed


def test_audit_event_can_be_appended_with_actor_firm_and_time(
    db_session: Session,
    identity_seed: IdentitySeed,
) -> None:
    service = AuditService(db_session)
    event = service.record_event(
        firm_id=identity_seed.firm_a.id,
        actor_user_id=identity_seed.accountant.id,
        event_type=AuditEventType.INFRASTRUCTURE_EVENT.value,
        target_type="test",
        target_id="synthetic-target",
        request_id="req-123",
        metadata={"result": "ok"},
    )
    db_session.commit()

    assert event.id is not None
    assert event.firm_id == identity_seed.firm_a.id
    assert event.actor_user_id == identity_seed.accountant.id
    assert event.occurred_at.tzinfo is not None
    assert event.metadata_json == {"result": "ok"}


def test_tenant_scoped_audit_query_does_not_leak_other_firm_events(
    db_session: Session,
    identity_seed: IdentitySeed,
) -> None:
    service = AuditService(db_session)
    service.record_event(
        firm_id=identity_seed.firm_a.id,
        event_type=AuditEventType.INFRASTRUCTURE_EVENT.value,
        target_type="test",
        target_id="firm-a",
    )
    service.record_event(
        firm_id=identity_seed.firm_b.id,
        event_type=AuditEventType.INFRASTRUCTURE_EVENT.value,
        target_type="test",
        target_id="firm-b",
    )
    db_session.commit()

    events = AuditRepository(db_session).list_for_firm(firm_id=identity_seed.firm_a.id)
    assert [event.target_id for event in events] == ["firm-a"]


def test_audit_service_rejects_sensitive_metadata_keys(
    db_session: Session,
    identity_seed: IdentitySeed,
) -> None:
    service = AuditService(db_session)
    with pytest.raises(UnsafeAuditMetadataError):
        service.record_event(
            firm_id=identity_seed.firm_a.id,
            event_type=AuditEventType.INFRASTRUCTURE_EVENT.value,
            target_type="test",
            target_id="synthetic-target",
            metadata={"token": "not-allowed"},
        )


def test_audit_service_exposes_no_update_or_delete_interface(db_session: Session) -> None:
    service = AuditService(db_session)
    repository = AuditRepository(db_session)
    assert not hasattr(service, "delete_event")
    assert not hasattr(service, "update_event")
    assert not hasattr(repository, "delete")
    assert not hasattr(repository, "update")
