from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ledgerpilot.persistence.models.extraction import (
    ExtractedField,
    ExtractionFieldCorrection,
    ExtractionRun,
)


class ExtractionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add_run(self, run: ExtractionRun) -> ExtractionRun:
        self._session.add(run)
        return run

    def add_field(self, field: ExtractedField) -> ExtractedField:
        self._session.add(field)
        return field

    def add_correction(self, correction: ExtractionFieldCorrection) -> ExtractionFieldCorrection:
        self._session.add(correction)
        return correction

    def get_run_for_document(
        self,
        *,
        firm_id: UUID,
        client_id: UUID,
        document_id: UUID,
        run_id: UUID,
    ) -> ExtractionRun | None:
        statement = select(ExtractionRun).where(
            ExtractionRun.id == run_id,
            ExtractionRun.firm_id == firm_id,
            ExtractionRun.client_id == client_id,
            ExtractionRun.document_id == document_id,
        )
        return self._session.scalar(statement)

    def list_runs_for_document(
        self,
        *,
        firm_id: UUID,
        client_id: UUID,
        document_id: UUID,
        limit: int = 50,
    ) -> list[ExtractionRun]:
        statement = (
            select(ExtractionRun)
            .where(
                ExtractionRun.firm_id == firm_id,
                ExtractionRun.client_id == client_id,
                ExtractionRun.document_id == document_id,
            )
            .order_by(ExtractionRun.created_at.desc())
            .limit(limit)
        )
        return list(self._session.scalars(statement))

    def list_fields_for_run(
        self,
        *,
        firm_id: UUID,
        client_id: UUID,
        document_id: UUID,
        run_id: UUID,
    ) -> list[ExtractedField]:
        statement = (
            select(ExtractedField)
            .where(
                ExtractedField.extraction_run_id == run_id,
                ExtractedField.firm_id == firm_id,
                ExtractedField.client_id == client_id,
                ExtractedField.document_id == document_id,
            )
            .order_by(ExtractedField.field_path.asc())
        )
        return list(self._session.scalars(statement))

    def get_field_for_run(
        self,
        *,
        firm_id: UUID,
        client_id: UUID,
        document_id: UUID,
        run_id: UUID,
        field_id: UUID,
    ) -> ExtractedField | None:
        statement = select(ExtractedField).where(
            ExtractedField.id == field_id,
            ExtractedField.extraction_run_id == run_id,
            ExtractedField.firm_id == firm_id,
            ExtractedField.client_id == client_id,
            ExtractedField.document_id == document_id,
        )
        return self._session.scalar(statement)

    def list_corrections_for_run(
        self,
        *,
        firm_id: UUID,
        client_id: UUID,
        document_id: UUID,
        run_id: UUID,
    ) -> list[ExtractionFieldCorrection]:
        statement = (
            select(ExtractionFieldCorrection)
            .where(
                ExtractionFieldCorrection.extraction_run_id == run_id,
                ExtractionFieldCorrection.firm_id == firm_id,
                ExtractionFieldCorrection.client_id == client_id,
                ExtractionFieldCorrection.document_id == document_id,
            )
            .order_by(
                ExtractionFieldCorrection.field_id.asc(),
                ExtractionFieldCorrection.revision_number.asc(),
            )
        )
        return list(self._session.scalars(statement))

    def list_corrections_for_field(
        self,
        *,
        firm_id: UUID,
        client_id: UUID,
        document_id: UUID,
        run_id: UUID,
        field_id: UUID,
    ) -> list[ExtractionFieldCorrection]:
        statement = (
            select(ExtractionFieldCorrection)
            .where(
                ExtractionFieldCorrection.field_id == field_id,
                ExtractionFieldCorrection.extraction_run_id == run_id,
                ExtractionFieldCorrection.firm_id == firm_id,
                ExtractionFieldCorrection.client_id == client_id,
                ExtractionFieldCorrection.document_id == document_id,
            )
            .order_by(ExtractionFieldCorrection.revision_number.asc())
        )
        return list(self._session.scalars(statement))

    def next_revision_number(
        self,
        *,
        field_id: UUID,
    ) -> int:
        statement = select(
            func.coalesce(func.max(ExtractionFieldCorrection.revision_number), 0)
        ).where(ExtractionFieldCorrection.field_id == field_id)
        return int(self._session.scalar(statement) or 0) + 1
