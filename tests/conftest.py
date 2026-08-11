from __future__ import annotations

from collections.abc import Generator
from dataclasses import dataclass

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from ledgerpilot.api.app import create_app
from ledgerpilot.core.config import AuthMode, Environment, Settings
from ledgerpilot.identity.roles import Role
from ledgerpilot.persistence.base import Base
from ledgerpilot.persistence.models.identity import ClientEntity, Firm, FirmMembership, User
from ledgerpilot.persistence.repositories.identity import IdentityRepository
from ledgerpilot.persistence.session import create_engine_from_settings, create_session_factory


@pytest.fixture
def settings() -> Settings:
    return Settings(
        env=Environment.TEST,
        database_url="sqlite+pysqlite:///:memory:",
        auth_mode=AuthMode.DEVELOPMENT,
        dev_auth_enabled=True,
    )


@pytest.fixture
def engine(settings: Settings) -> Generator[Engine]:
    test_engine = create_engine_from_settings(settings)
    Base.metadata.create_all(test_engine)
    try:
        yield test_engine
    finally:
        Base.metadata.drop_all(test_engine)
        test_engine.dispose()


@pytest.fixture
def session_factory(engine: Engine) -> sessionmaker[Session]:
    return create_session_factory(engine)


@pytest.fixture
def db_session(session_factory: sessionmaker[Session]) -> Generator[Session]:
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def app(settings: Settings, session_factory: sessionmaker[Session]):
    return create_app(settings=settings, session_factory=session_factory)


@pytest.fixture
def client(app) -> Generator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@dataclass(frozen=True)
class IdentitySeed:
    firm_a: Firm
    firm_b: Firm
    accountant: User
    admin: User
    auditor: User
    submitter: User
    outsider: User
    accountant_membership: FirmMembership
    admin_membership: FirmMembership
    auditor_membership: FirmMembership
    submitter_membership: FirmMembership
    client_a: ClientEntity
    client_b: ClientEntity
    firm_b_client: ClientEntity


@pytest.fixture
def identity_seed(db_session: Session) -> IdentitySeed:
    repository = IdentityRepository(db_session)
    firm_a = repository.add_firm(name="Synthetic Firm A")
    firm_b = repository.add_firm(name="Synthetic Firm B")
    db_session.flush()

    accountant = repository.add_user(external_subject="dev-accountant")
    admin = repository.add_user(external_subject="dev-admin")
    auditor = repository.add_user(external_subject="dev-auditor")
    submitter = repository.add_user(external_subject="dev-submitter")
    outsider = repository.add_user(external_subject="dev-outsider")
    db_session.flush()

    accountant_membership = repository.add_membership(
        user_id=accountant.id,
        firm_id=firm_a.id,
        role=Role.ACCOUNTANT.value,
    )
    admin_membership = repository.add_membership(
        user_id=admin.id,
        firm_id=firm_a.id,
        role=Role.FIRM_ADMIN.value,
    )
    auditor_membership = repository.add_membership(
        user_id=auditor.id,
        firm_id=firm_a.id,
        role=Role.AUDITOR.value,
    )
    submitter_membership = repository.add_membership(
        user_id=submitter.id,
        firm_id=firm_a.id,
        role=Role.CLIENT_SUBMITTER.value,
    )
    db_session.flush()

    client_a = repository.add_client(firm_id=firm_a.id, name="Synthetic Client A")
    client_b = repository.add_client(firm_id=firm_a.id, name="Synthetic Client B")
    firm_b_client = repository.add_client(firm_id=firm_b.id, name="Synthetic Client C")
    db_session.flush()

    repository.grant_client_access(
        membership_id=accountant_membership.id,
        firm_id=firm_a.id,
        client_id=client_a.id,
    )
    repository.grant_client_access(
        membership_id=submitter_membership.id,
        firm_id=firm_a.id,
        client_id=client_a.id,
    )
    db_session.commit()

    return IdentitySeed(
        firm_a=firm_a,
        firm_b=firm_b,
        accountant=accountant,
        admin=admin,
        auditor=auditor,
        submitter=submitter,
        outsider=outsider,
        accountant_membership=accountant_membership,
        admin_membership=admin_membership,
        auditor_membership=auditor_membership,
        submitter_membership=submitter_membership,
        client_a=client_a,
        client_b=client_b,
        firm_b_client=firm_b_client,
    )
