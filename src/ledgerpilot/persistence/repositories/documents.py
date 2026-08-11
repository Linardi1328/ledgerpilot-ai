from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from ledgerpilot.persistence.models.documents import Document, DocumentFile


class DocumentRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add_document(self, document: Document) -> Document:
        self._session.add(document)
        return document

    def add_document_file(self, document_file: DocumentFile) -> DocumentFile:
        self._session.add(document_file)
        return document_file

    def get_document_for_client(
        self,
        *,
        firm_id: UUID,
        client_id: UUID,
        document_id: UUID,
    ) -> Document | None:
        statement = select(Document).where(
            Document.id == document_id,
            Document.firm_id == firm_id,
            Document.client_id == client_id,
        )
        return self._session.scalar(statement)

    def get_document_file_for_client(
        self,
        *,
        firm_id: UUID,
        client_id: UUID,
        document_id: UUID,
    ) -> DocumentFile | None:
        statement = select(DocumentFile).where(
            DocumentFile.document_id == document_id,
            DocumentFile.firm_id == firm_id,
            DocumentFile.client_id == client_id,
        )
        return self._session.scalar(statement)
