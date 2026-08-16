from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from ledgerpilot.persistence.base import Base, utc_now
from ledgerpilot.review.states import ReviewEscalationState, ReviewTaskStatus

_REVIEW_STATUS_VALUES = ", ".join(f"'{status.value}'" for status in ReviewTaskStatus)
_ESCALATION_STATE_VALUES = ", ".join(f"'{state.value}'" for state in ReviewEscalationState)


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
            "(status = 'open' and escalation_state = 'none' and escalated_at is null) "
            "or (status = 'escalated' and escalation_state = 'senior_review' "
            "and escalated_at is not null)",
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
