from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from ledgerpilot.persistence.base import Base, utc_now
from ledgerpilot.review.states import (
    ReviewCommentKind,
    ReviewEscalationState,
    ReviewOutcomeType,
    ReviewRiskClass,
    ReviewTaskStatus,
)

_REVIEW_STATUS_VALUES = ", ".join(f"'{status.value}'" for status in ReviewTaskStatus)
_ESCALATION_STATE_VALUES = ", ".join(f"'{state.value}'" for state in ReviewEscalationState)
_RISK_CLASS_VALUES = ", ".join(f"'{risk.value}'" for risk in ReviewRiskClass)
_COMMENT_KIND_VALUES = ", ".join(f"'{kind.value}'" for kind in ReviewCommentKind)
_OUTCOME_TYPE_VALUES = ", ".join(f"'{outcome.value}'" for outcome in ReviewOutcomeType)


class ReviewTask(Base):
    __tablename__ = "review_tasks"
    __table_args__ = (
        CheckConstraint(
            f"status in ({_REVIEW_STATUS_VALUES})",
            name="ck_review_tasks_status",
        ),
        CheckConstraint(
            f"escalation_state in ({_ESCALATION_STATE_VALUES})",
            name="ck_review_tasks_escalation_state",
        ),
        CheckConstraint(
            f"risk_class in ({_RISK_CLASS_VALUES})",
            name="ck_review_tasks_risk_class",
        ),
        CheckConstraint(
            "("
            "(escalation_state = 'none' and escalated_at is null) "
            "or (escalation_state = 'senior_review' and escalated_at is not null)"
            ") and ("
            "(status = 'open' and escalation_state = 'none') "
            "or (status = 'escalated' and escalation_state = 'senior_review') "
            "or status in ('information_requested', 'approved', 'rejected')"
            ")",
            name="ck_review_tasks_state_consistency",
        ),
        ForeignKeyConstraint(
            ["client_id", "firm_id"],
            ["client_entities.id", "client_entities.firm_id"],
            name="fk_review_tasks_client_firm",
        ),
        ForeignKeyConstraint(
            ["decision_run_id", "firm_id", "client_id", "document_id", "extraction_run_id"],
            [
                "accounting_decision_runs.id",
                "accounting_decision_runs.firm_id",
                "accounting_decision_runs.client_id",
                "accounting_decision_runs.document_id",
                "accounting_decision_runs.extraction_run_id",
            ],
            name="fk_review_tasks_decision_scope",
        ),
        ForeignKeyConstraint(
            ["created_by_membership_id", "created_by_user_id", "firm_id"],
            ["firm_memberships.id", "firm_memberships.user_id", "firm_memberships.firm_id"],
            name="fk_review_tasks_creator_membership_user_firm",
        ),
        ForeignKeyConstraint(
            ["owner_membership_id", "owner_user_id", "firm_id"],
            ["firm_memberships.id", "firm_memberships.user_id", "firm_memberships.firm_id"],
            name="fk_review_tasks_owner_membership_user_firm",
        ),
        ForeignKeyConstraint(
            ["owner_membership_id", "client_id"],
            ["client_access.membership_id", "client_access.client_id"],
            name="fk_review_tasks_owner_client_access",
        ),
        UniqueConstraint("decision_run_id", name="uq_review_tasks_decision_run"),
        UniqueConstraint(
            "id",
            "firm_id",
            "client_id",
            "decision_run_id",
            name="uq_review_tasks_id_scope",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    firm_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("firms.id"), nullable=False, index=True)
    client_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    decision_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
        index=True,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    extraction_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
        index=True,
    )
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    created_by_membership_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    owner_user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    owner_membership_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    risk_class: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    escalation_state: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    escalated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
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


class ReviewComment(Base):
    __tablename__ = "review_comments"
    __table_args__ = (
        CheckConstraint(
            f"kind in ({_COMMENT_KIND_VALUES})",
            name="ck_review_comments_kind",
        ),
        CheckConstraint("length(body) > 0", name="ck_review_comments_body_nonempty"),
        ForeignKeyConstraint(
            ["review_task_id", "firm_id", "client_id", "decision_run_id"],
            [
                "review_tasks.id",
                "review_tasks.firm_id",
                "review_tasks.client_id",
                "review_tasks.decision_run_id",
            ],
            name="fk_review_comments_task_scope",
        ),
        ForeignKeyConstraint(
            ["author_membership_id", "author_user_id", "firm_id"],
            ["firm_memberships.id", "firm_memberships.user_id", "firm_memberships.firm_id"],
            name="fk_review_comments_author_membership_user_firm",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    review_task_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), nullable=False, index=True
    )
    firm_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    client_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    decision_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), nullable=False, index=True
    )
    author_user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    author_membership_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    body: Mapped[str] = mapped_column(String(2000), nullable=False)
    request_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )


class ReviewOutcome(Base):
    __tablename__ = "review_outcomes"
    __table_args__ = (
        CheckConstraint(
            f"outcome_type in ({_OUTCOME_TYPE_VALUES})",
            name="ck_review_outcomes_type",
        ),
        CheckConstraint(
            "source_correction_count >= 0",
            name="ck_review_outcomes_correction_count_nonnegative",
        ),
        CheckConstraint(
            "("
            "(outcome_type = 'rejected' and reason is not null and length(reason) > 0 "
            "and proposed_journal_id is null) "
            "or (outcome_type in ('approved', 'corrected_and_approved') "
            "and proposed_journal_id is not null)"
            ")",
            name="ck_review_outcomes_resolution_consistency",
        ),
        ForeignKeyConstraint(
            ["review_task_id", "firm_id", "client_id", "decision_run_id"],
            [
                "review_tasks.id",
                "review_tasks.firm_id",
                "review_tasks.client_id",
                "review_tasks.decision_run_id",
            ],
            name="fk_review_outcomes_task_scope",
        ),
        ForeignKeyConstraint(
            ["actor_membership_id", "actor_user_id", "firm_id"],
            ["firm_memberships.id", "firm_memberships.user_id", "firm_memberships.firm_id"],
            name="fk_review_outcomes_actor_membership_user_firm",
        ),
        ForeignKeyConstraint(
            [
                "proposed_journal_id",
                "decision_run_id",
                "firm_id",
                "client_id",
                "document_id",
                "extraction_run_id",
            ],
            [
                "proposed_journals.id",
                "proposed_journals.decision_run_id",
                "proposed_journals.firm_id",
                "proposed_journals.client_id",
                "proposed_journals.document_id",
                "proposed_journals.extraction_run_id",
            ],
            name="fk_review_outcomes_journal_scope",
        ),
        UniqueConstraint("review_task_id", name="uq_review_outcomes_review_task"),
        UniqueConstraint(
            "id",
            "firm_id",
            "client_id",
            "decision_run_id",
            "document_id",
            name="uq_review_outcomes_id_scope",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    review_task_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), nullable=False, index=True
    )
    firm_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    client_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    decision_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), nullable=False, index=True
    )
    document_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    extraction_run_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    actor_user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    actor_membership_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    outcome_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    proposed_journal_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    source_correction_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
