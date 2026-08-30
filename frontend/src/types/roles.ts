export enum Role {
  FIRM_ADMIN = "firm_admin",
  ACCOUNTANT = "accountant",
  SENIOR_REVIEWER = "senior_reviewer",
  CLIENT_SUBMITTER = "client_submitter",
  AUDITOR = "auditor",
}

export enum Permission {
  VIEW_CONTEXT = "view_context",
  UPLOAD_DOCUMENTS = "upload_documents",
  VIEW_DOCUMENTS = "view_documents",
  RUN_EXTRACTION = "run_extraction",
  CORRECT_EXTRACTED_INFORMATION = "correct_extracted_information",
  RUN_ACCOUNTING_DECISION = "run_accounting_decision",
  REVIEW_RECOMMENDATIONS = "review_recommendations",
  CREATE_REVIEW_TASK = "create_review_task",
  VIEW_REVIEW_TASK = "view_review_task",
  ADD_REVIEW_COMMENT = "add_review_comment",
  VIEW_REVIEW_HISTORY = "view_review_history",
  VIEW_INFORMATION_REQUEST = "view_information_request",
  RESPOND_TO_INFORMATION_REQUEST = "respond_to_information_request",
  APPROVE_ORDINARY_TRANSACTION = "approve_ordinary_transaction",
  APPROVE_HIGH_RISK_TRANSACTION = "approve_high_risk_transaction",
  REJECT_TRANSACTION = "reject_transaction",
  ESCALATE_TRANSACTION = "escalate_transaction",
  REQUEST_INFORMATION = "request_information",
  VIEW_AUDIT_HISTORY = "view_audit_history",
  IMPORT_BANK_TRANSACTIONS = "import_bank_transactions",
  VIEW_BANK_TRANSACTIONS = "view_bank_transactions",
  RUN_RECONCILIATION_MATCHING = "run_reconciliation_matching",
  VIEW_RECONCILIATION_MATCHES = "view_reconciliation_matches",
  CREATE_RECONCILIATION_REVIEW = "create_reconciliation_review",
  REVIEW_RECONCILIATION = "review_reconciliation",
  APPROVE_RECONCILIATION = "approve_reconciliation",
  VIEW_RECONCILIATION_HISTORY = "view_reconciliation_history",
  MANAGE_USERS = "manage_users",
  MANAGE_CONFIGURATION = "manage_configuration",
  MANAGE_INTEGRATIONS = "manage_integrations",
  EXPORT_APPROVED_ENTRIES = "export_approved_entries",
  CORRECT_APPROVED_RECORDS = "correct_approved_records",
}

export enum ReviewRiskClass {
  ORDINARY = "ordinary",
  SENIOR_REVIEW_REQUIRED = "senior_review_required",
  BLOCKED = "blocked",
}

export enum ReviewTaskStatus {
  OPEN = "open",
  ESCALATED = "escalated",
  INFORMATION_REQUESTED = "information_requested",
  APPROVED = "approved",
  REJECTED = "rejected",
}

export enum ReviewEscalationState {
  NONE = "none",
  SENIOR_REVIEW = "senior_review",
}

export enum ReviewOutcomeType {
  APPROVED = "approved",
  CORRECTED_AND_APPROVED = "corrected_and_approved",
  REJECTED = "rejected",
}

export enum ReviewCommentKind {
  COMMENT = "comment",
  ESCALATION_REASON = "escalation_reason",
  INFORMATION_REQUEST = "information_request",
  INFORMATION_RESPONSE = "information_response",
}

export enum AccountingFindingSeverity {
  ERROR = "error",
  WARNING = "warning",
  INFO = "info",
}

export interface Principal {
  user_id: string;
  firm_id: string;
  membership_id: string;
  role: Role;
  permissions: Permission[];
  authorized_client_ids: string[];
}
