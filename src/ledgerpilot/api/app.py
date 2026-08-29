from __future__ import annotations

from fastapi import FastAPI
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from ledgerpilot import __version__
from ledgerpilot.accounting.rules import AccountingDecisionPolicy, SyntheticAccountingDecisionPolicy
from ledgerpilot.api.errors import register_error_handlers
from ledgerpilot.api.middleware import RequestIDMiddleware
from ledgerpilot.api.routes import api_router
from ledgerpilot.core.config import Settings, get_settings
from ledgerpilot.core.logging import configure_logging
from ledgerpilot.extraction.development import get_extraction_provider
from ledgerpilot.extraction.protocol import ExtractionProvider
from ledgerpilot.identity.authentication import AuthenticationBackend, get_authentication_backend
from ledgerpilot.persistence.session import create_engine_from_settings, create_session_factory
from ledgerpilot.scanning.development import get_malware_scanner
from ledgerpilot.scanning.protocol import MalwareScanner
from ledgerpilot.storage.local import get_document_storage
from ledgerpilot.storage.protocol import DocumentStorage


def create_app(
    settings: Settings | None = None,
    session_factory: sessionmaker[Session] | None = None,
    auth_backend: AuthenticationBackend | None = None,
    document_storage: DocumentStorage | None = None,
    malware_scanner: MalwareScanner | None = None,
    extraction_provider: ExtractionProvider | None = None,
    accounting_decision_policy: AccountingDecisionPolicy | None = None,
) -> FastAPI:
    app_settings = settings or get_settings()
    configure_logging(app_settings.log_level)

    engine: Engine | None = None
    if session_factory is None:
        engine = create_engine_from_settings(app_settings)
        session_factory = create_session_factory(engine)

    app = FastAPI(
        title="LedgerPilot AI",
        version=__version__,
        description="Phase 5 human review workflow. Not production-ready.",
    )
    app.state.settings = app_settings
    app.state.engine = engine
    app.state.session_factory = session_factory
    app.state.auth_backend = auth_backend or get_authentication_backend(app_settings)
    app.state.document_storage = document_storage or get_document_storage(app_settings)
    app.state.malware_scanner = malware_scanner or get_malware_scanner(app_settings)
    app.state.extraction_provider = extraction_provider or get_extraction_provider(app_settings)
    app.state.accounting_decision_policy = (
        accounting_decision_policy or SyntheticAccountingDecisionPolicy()
    )

    app.add_middleware(RequestIDMiddleware)
    register_error_handlers(app)
    app.include_router(api_router, prefix="/api/v1")
    return app
