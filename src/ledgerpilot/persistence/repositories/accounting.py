from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from ledgerpilot.accounting.states import AccountingDecisionRunStatus
from ledgerpilot.persistence.models.accounting import (
    AccountingDecisionFinding,
    AccountingDecisionRun,
    AccountingDuplicateCandidate,
    AccountingRecommendation,
    AccountingSupplierMatchCandidate,
    ProposedJournal,
    ProposedJournalLine,
)


class AccountingRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add_run(self, run: AccountingDecisionRun) -> AccountingDecisionRun:
        self._session.add(run)
        return run

    def add_finding(self, finding: AccountingDecisionFinding) -> AccountingDecisionFinding:
        self._session.add(finding)
        return finding

    def add_supplier_match_candidate(
        self,
        candidate: AccountingSupplierMatchCandidate,
    ) -> AccountingSupplierMatchCandidate:
        self._session.add(candidate)
        return candidate

    def add_duplicate_candidate(
        self,
        candidate: AccountingDuplicateCandidate,
    ) -> AccountingDuplicateCandidate:
        self._session.add(candidate)
        return candidate

    def add_recommendation(
        self,
        recommendation: AccountingRecommendation,
    ) -> AccountingRecommendation:
        self._session.add(recommendation)
        return recommendation

    def add_proposed_journal(self, journal: ProposedJournal) -> ProposedJournal:
        self._session.add(journal)
        return journal

    def add_proposed_journal_line(self, line: ProposedJournalLine) -> ProposedJournalLine:
        self._session.add(line)
        return line

    def get_run_for_extraction(
        self,
        *,
        firm_id: UUID,
        client_id: UUID,
        document_id: UUID,
        extraction_run_id: UUID,
        decision_run_id: UUID,
    ) -> AccountingDecisionRun | None:
        statement = select(AccountingDecisionRun).where(
            AccountingDecisionRun.id == decision_run_id,
            AccountingDecisionRun.firm_id == firm_id,
            AccountingDecisionRun.client_id == client_id,
            AccountingDecisionRun.document_id == document_id,
            AccountingDecisionRun.extraction_run_id == extraction_run_id,
        )
        return self._session.scalar(statement)

    def list_runs_for_extraction(
        self,
        *,
        firm_id: UUID,
        client_id: UUID,
        document_id: UUID,
        extraction_run_id: UUID,
        limit: int = 50,
    ) -> list[AccountingDecisionRun]:
        statement = (
            select(AccountingDecisionRun)
            .where(
                AccountingDecisionRun.firm_id == firm_id,
                AccountingDecisionRun.client_id == client_id,
                AccountingDecisionRun.document_id == document_id,
                AccountingDecisionRun.extraction_run_id == extraction_run_id,
            )
            .order_by(AccountingDecisionRun.created_at.desc())
            .limit(limit)
        )
        return list(self._session.scalars(statement))

    def list_succeeded_runs_for_client(
        self,
        *,
        firm_id: UUID,
        client_id: UUID,
        limit: int = 50,
    ) -> list[AccountingDecisionRun]:
        statement = (
            select(AccountingDecisionRun)
            .where(
                AccountingDecisionRun.firm_id == firm_id,
                AccountingDecisionRun.client_id == client_id,
                AccountingDecisionRun.status == AccountingDecisionRunStatus.SUCCEEDED.value,
            )
            .order_by(AccountingDecisionRun.created_at.desc())
            .limit(limit)
        )
        return list(self._session.scalars(statement))

    def list_findings_for_run(
        self,
        *,
        firm_id: UUID,
        client_id: UUID,
        document_id: UUID,
        extraction_run_id: UUID,
        decision_run_id: UUID,
    ) -> list[AccountingDecisionFinding]:
        statement = (
            select(AccountingDecisionFinding)
            .where(
                AccountingDecisionFinding.decision_run_id == decision_run_id,
                AccountingDecisionFinding.firm_id == firm_id,
                AccountingDecisionFinding.client_id == client_id,
                AccountingDecisionFinding.document_id == document_id,
                AccountingDecisionFinding.extraction_run_id == extraction_run_id,
            )
            .order_by(AccountingDecisionFinding.created_at.asc())
        )
        return list(self._session.scalars(statement))

    def list_supplier_match_candidates_for_run(
        self,
        *,
        firm_id: UUID,
        client_id: UUID,
        document_id: UUID,
        extraction_run_id: UUID,
        decision_run_id: UUID,
    ) -> list[AccountingSupplierMatchCandidate]:
        statement = (
            select(AccountingSupplierMatchCandidate)
            .where(
                AccountingSupplierMatchCandidate.decision_run_id == decision_run_id,
                AccountingSupplierMatchCandidate.firm_id == firm_id,
                AccountingSupplierMatchCandidate.client_id == client_id,
                AccountingSupplierMatchCandidate.document_id == document_id,
                AccountingSupplierMatchCandidate.extraction_run_id == extraction_run_id,
            )
            .order_by(
                AccountingSupplierMatchCandidate.is_confident.desc(),
                AccountingSupplierMatchCandidate.confidence.desc(),
                AccountingSupplierMatchCandidate.created_at.asc(),
            )
        )
        return list(self._session.scalars(statement))

    def list_duplicate_candidates_for_run(
        self,
        *,
        firm_id: UUID,
        client_id: UUID,
        document_id: UUID,
        extraction_run_id: UUID,
        decision_run_id: UUID,
    ) -> list[AccountingDuplicateCandidate]:
        statement = (
            select(AccountingDuplicateCandidate)
            .where(
                AccountingDuplicateCandidate.decision_run_id == decision_run_id,
                AccountingDuplicateCandidate.firm_id == firm_id,
                AccountingDuplicateCandidate.client_id == client_id,
                AccountingDuplicateCandidate.document_id == document_id,
                AccountingDuplicateCandidate.extraction_run_id == extraction_run_id,
            )
            .order_by(
                AccountingDuplicateCandidate.confidence.desc(),
                AccountingDuplicateCandidate.created_at.asc(),
            )
        )
        return list(self._session.scalars(statement))

    def list_recommendations_for_run(
        self,
        *,
        firm_id: UUID,
        client_id: UUID,
        document_id: UUID,
        extraction_run_id: UUID,
        decision_run_id: UUID,
    ) -> list[AccountingRecommendation]:
        statement = (
            select(AccountingRecommendation)
            .where(
                AccountingRecommendation.decision_run_id == decision_run_id,
                AccountingRecommendation.firm_id == firm_id,
                AccountingRecommendation.client_id == client_id,
                AccountingRecommendation.document_id == document_id,
                AccountingRecommendation.extraction_run_id == extraction_run_id,
            )
            .order_by(AccountingRecommendation.recommendation_type.asc())
        )
        return list(self._session.scalars(statement))

    def get_proposed_journal_for_run(
        self,
        *,
        firm_id: UUID,
        client_id: UUID,
        document_id: UUID,
        extraction_run_id: UUID,
        decision_run_id: UUID,
    ) -> ProposedJournal | None:
        statement = select(ProposedJournal).where(
            ProposedJournal.decision_run_id == decision_run_id,
            ProposedJournal.firm_id == firm_id,
            ProposedJournal.client_id == client_id,
            ProposedJournal.document_id == document_id,
            ProposedJournal.extraction_run_id == extraction_run_id,
        )
        return self._session.scalar(statement)

    def list_proposed_journal_lines_for_run(
        self,
        *,
        firm_id: UUID,
        client_id: UUID,
        document_id: UUID,
        extraction_run_id: UUID,
        decision_run_id: UUID,
    ) -> list[ProposedJournalLine]:
        statement = (
            select(ProposedJournalLine)
            .where(
                ProposedJournalLine.decision_run_id == decision_run_id,
                ProposedJournalLine.firm_id == firm_id,
                ProposedJournalLine.client_id == client_id,
                ProposedJournalLine.document_id == document_id,
                ProposedJournalLine.extraction_run_id == extraction_run_id,
            )
            .order_by(ProposedJournalLine.line_number.asc())
        )
        return list(self._session.scalars(statement))
