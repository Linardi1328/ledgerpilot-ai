from __future__ import annotations

from enum import StrEnum


class Role(StrEnum):
    FIRM_ADMIN = "firm_admin"
    ACCOUNTANT = "accountant"
    SENIOR_REVIEWER = "senior_reviewer"
    CLIENT_SUBMITTER = "client_submitter"
    AUDITOR = "auditor"
