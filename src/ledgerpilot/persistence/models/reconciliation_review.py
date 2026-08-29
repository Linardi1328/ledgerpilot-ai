from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from ledgerpilot.persistence.base import Base, utc_now
from ledgerpilot.reconciliation.states import (
    ReconciliationOutcomeType,
    ReconciliationReviewActionType,
    ReconciliationReviewStatus,
)

_REVIEW_STATUS_VALUES = ", ".join(f"'{status.value}'" for status in ReconciliationReviewStatus)
_ACTION_TYPE_VALUES = ", ".join(f"'{action.value}'" for action in ReconciliationReviewActionType)
_OUTCOME_TYPE_VALUES = ", ".join(f"'{outcome.value}'" for outcome in ReconciliationOutcomeType)


class ReconciliationReviewRecord(Base):
    __tablename__ = "reconciliation_reviews"
    __table_args__ = (
        CheckConstraint(
            f"status in ({_REVIEW_STATUS_VALUES})",
            name="ck_reconciliation_reviews_status",
        ),
        ForeignKeyConstraint(
            ["bank_transaction_id", "firm_id", "client_id"],
            [
                "bank_transactions.id",
                "bank_transactions.firm_id",
                "bank_transactions.client_id",
            ],
            name="fk_reconciliation_reviews_transaction_scope",
        ),
        ForeignKeyConstraint(
            ["match_run_id", "firm_id", "client_id", "bank_transaction_id"],
            [
                "reconciliation_match_runs.id",
                "reconciliation_match_runs.firm_id",
                "reconciliation_match_runs.client_id",
                "reconciliation_match_runs.bank_transaction_id",
            ],
            name="fk_reconciliation_reviews_match_run_scope",
        ),
        ForeignKeyConstraint(
            ["match_run_id", "selected_review_outcome_id"],
            [
                "reconciliation_candidates.match_run_id",
                "reconciliation_candidates.review_outcome_id",
            ],
            name="fk_reconciliation_reviews_selected_candidate",
        ),
        ForeignKeyConstraint(
            ["created_by_membership_id", "created_by_user_id", "firm_id"],
            [
                "firm_memberships.id",
                "firm_memberships.user_id",
                "firm_memberships.firm_id",
            ],
            name="fk_reconciliation_reviews_creator_membership_user_firm",
        ),
        UniqueConstraint(
            "bank_transaction_id",
            name="uq_reconciliation_reviews_transaction",
        ),
        UniqueConstraint(
            "id",
            "firm_id",
            "client_id",
            "bank_transaction_id",
            "match_run_id",
            name="uq_reconciliation_reviews_id_scope",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bank_transaction_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
        index=True,
    )
    firm_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    client_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    match_run_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    created_by_membership_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    selected_review_outcome_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        nullable=True,
        index=True,
    )
    request_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )


class ReconciliationReviewActionRecord(Base):
    __tablename__ = "reconciliation_review_actions"
    __table_args__ = (
        CheckConstraint(
            f"action_type in ({_ACTION_TYPE_VALUES})",
            name="ck_reconciliation_review_actions_type",
        ),
        CheckConstraint(
            "reason is null or length(reason) > 0",
            name="ck_reconciliation_review_actions_reason",
        ),
        ForeignKeyConstraint(
            [
                "reconciliation_review_id",
                "firm_id",
                "client_id",
                "bank_transaction_id",
                "match_run_id",
            ],
            [
                "reconciliation_reviews.id",
                "reconciliation_reviews.firm_id",
                "reconciliation_reviews.client_id",
                "reconciliation_reviews.bank_transaction_id",
                "reconciliation_reviews.match_run_id",
            ],
            name="fk_reconciliation_review_actions_review_scope",
        ),
        ForeignKeyConstraint(
            ["match_run_id", "candidate_review_outcome_id"],
            [
                "reconciliation_candidates.match_run_id",
                "reconciliation_candidates.review_outcome_id",
            ],
            name="fk_reconciliation_review_actions_candidate",
        ),
        ForeignKeyConstraint(
            ["actor_membership_id", "actor_user_id", "firm_id"],
            [
                "firm_memberships.id",
                "firm_memberships.user_id",
                "firm_memberships.firm_id",
            ],
            name="fk_reconciliation_review_actions_actor_membership_user_firm",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reconciliation_review_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
        index=True,
    )
    bank_transaction_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
        index=True,
    )
    firm_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    client_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    match_run_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    actor_user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    actor_membership_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    action_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    candidate_review_outcome_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        nullable=True,
        index=True,
    )
    reason: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )


class ReconciliationOutcomeRecord(Base):
    __tablename__ = "reconciliation_outcomes"
    __table_args__ = (
        CheckConstraint(
            f"outcome_type in ({_OUTCOME_TYPE_VALUES})",
            name="ck_reconciliation_outcomes_type",
        ),
        CheckConstraint(
            "("
            "outcome_type = 'matched' and matched_review_outcome_id is not null"
            ") or ("
            "outcome_type = 'unmatched' and matched_review_outcome_id is null "
            "and reason is not null and length(reason) > 0"
            ")",
            name="ck_reconciliation_outcomes_resolution_consistency",
        ),
        ForeignKeyConstraint(
            [
                "reconciliation_review_id",
                "firm_id",
                "client_id",
                "bank_transaction_id",
                "match_run_id",
            ],
            [
                "reconciliation_reviews.id",
                "reconciliation_reviews.firm_id",
                "reconciliation_reviews.client_id",
                "reconciliation_reviews.bank_transaction_id",
                "reconciliation_reviews.match_run_id",
            ],
            name="fk_reconciliation_outcomes_review_scope",
        ),
        ForeignKeyConstraint(
            ["match_run_id", "matched_review_outcome_id"],
            [
                "reconciliation_candidates.match_run_id",
                "reconciliation_candidates.review_outcome_id",
            ],
            name="fk_reconciliation_outcomes_candidate",
        ),
        ForeignKeyConstraint(
            ["actor_membership_id", "actor_user_id", "firm_id"],
            [
                "firm_memberships.id",
                "firm_memberships.user_id",
                "firm_memberships.firm_id",
            ],
            name="fk_reconciliation_outcomes_actor_membership_user_firm",
        ),
        UniqueConstraint(
            "reconciliation_review_id",
            name="uq_reconciliation_outcomes_review",
        ),
        UniqueConstraint(
            "bank_transaction_id",
            name="uq_reconciliation_outcomes_transaction",
        ),
        UniqueConstraint(
            "firm_id",
            "client_id",
            "matched_review_outcome_id",
            name="uq_reconciliation_outcomes_matched_review_outcome",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reconciliation_review_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
        index=True,
    )
    bank_transaction_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
        index=True,
    )
    firm_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    client_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    match_run_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    matched_review_outcome_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        nullable=True,
        index=True,
    )
    actor_user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    actor_membership_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    outcome_type: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    reason: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
