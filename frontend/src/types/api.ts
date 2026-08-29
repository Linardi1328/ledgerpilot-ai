import {
  AccountingFindingSeverity,
  ReviewCommentKind,
  ReviewEscalationState,
  ReviewOutcomeType,
  ReviewRiskClass,
  ReviewTaskStatus,
} from "./roles";

export interface ApiErrorDetail {
  code: string;
  message: string;
  request_id?: string | null;
}

export interface ApiErrorResponse {
  error: ApiErrorDetail;
}

export interface ContextResponse {
  user_id: string;
  firm_id: string;
  membership_id: string;
  role: string;
  permissions: string[];
  authorized_client_ids: string[];
}

export interface DocumentMetadataResponse {
  id: string;
  client_id: string;
  status: string;
  submitted_filename: string;
  media_type: string | null;
  size_bytes: number | null;
  sha256: string | null;
  created_at: string;
  updated_at: string;
}

export interface ExtractedFieldResponse {
  id: string;
  field_path: string;
  value_type: string;
  original_raw_value: string;
  original_normalized_value: string | null;
  effective_raw_value: string;
  effective_normalized_value: string | null;
  effective_value_type: string;
  confidence: string | null;
  source_page_number: number | null;
  source_locator: Record<string, unknown> | null;
  corrected: boolean;
  latest_correction_id: string | null;
  latest_revision_number: number | null;
}

export interface ExtractionRunResponse {
  id: string;
  client_id: string;
  document_id: string;
  document_file_id: string;
  status: string;
  provider_name: string;
  provider_version: string;
  model_version: string | null;
  extraction_schema_version: string;
  source_sha256: string;
  started_at: string | null;
  completed_at: string | null;
  failure_code: string | null;
  request_id: string | null;
  downstream_ready: boolean;
  fields: ExtractedFieldResponse[];
}

export interface ExtractionFieldCorrectionRequest {
  corrected_raw_value: string;
  corrected_normalized_value?: string | null;
  corrected_value_type: string;
  reason: string;
}

export interface AccountingDecisionFindingResponse {
  id: string;
  code: string;
  severity: AccountingFindingSeverity | string;
  field_path: string | null;
  description: string;
  evidence: Record<string, unknown>;
}

export interface SupplierMatchCandidateResponse {
  id: string;
  supplier_reference: string;
  supplier_name: string;
  confidence: string;
  explanation: string;
  evidence: Record<string, unknown>;
  matcher_name: string;
  matcher_version: string;
  model_version: string | null;
  is_confident: boolean;
}

export interface SupplierMatchResponse {
  status: string;
  candidates: SupplierMatchCandidateResponse[];
}

export interface DuplicateCandidateResponse {
  id: string;
  candidate_document_id: string;
  candidate_extraction_run_id: string;
  candidate_decision_run_id: string;
  confidence: string;
  explanation: string;
  evidence: Record<string, unknown>;
  detector_name: string;
  detector_version: string;
  model_version: string | null;
}

export interface AccountingRecommendationResponse {
  id: string;
  recommendation_type: string;
  recommended_value: string;
  confidence: string | null;
  explanation: string;
  evidence: Record<string, unknown>;
  rule_name: string;
  rule_version: string;
  model_version: string | null;
}

export interface ProposedJournalLineResponse {
  id: string;
  line_number: number;
  account_reference: string;
  debit_amount: string;
  credit_amount: string;
  tax_code_reference: string | null;
  cost_centre_reference: string | null;
  explanation: string;
  lineage: Record<string, unknown>;
}

export interface ProposedJournalResponse {
  id: string;
  currency: string;
  total_debits: string;
  total_credits: string;
  balance_status: string;
  is_balanced: boolean;
  explanation: string;
  lines: ProposedJournalLineResponse[];
}

export interface AccountingDecisionRunResponse {
  id: string;
  client_id: string;
  document_id: string;
  extraction_run_id: string;
  status: string;
  engine_name: string;
  engine_version: string;
  model_version: string | null;
  source_sha256: string;
  started_at: string | null;
  completed_at: string | null;
  failure_code: string | null;
  request_id: string | null;
  created_at: string;
  findings: AccountingDecisionFindingResponse[];
  supplier_match: SupplierMatchResponse;
  duplicate_candidates: DuplicateCandidateResponse[];
  recommendations: AccountingRecommendationResponse[];
  proposed_journal: ProposedJournalResponse | null;
}

export interface ReviewTaskResponse {
  id: string;
  firm_id: string;
  client_id: string;
  decision_run_id: string;
  document_id: string;
  extraction_run_id: string;
  created_by_user_id: string;
  created_by_membership_id: string;
  owner_user_id: string;
  owner_membership_id: string;
  status: ReviewTaskStatus | string;
  risk_class: ReviewRiskClass | string;
  escalation_state: ReviewEscalationState | string;
  escalated_at: string | null;
  request_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface ReviewCommentResponse {
  id: string;
  review_task_id: string;
  author_user_id: string;
  author_membership_id: string;
  kind: ReviewCommentKind | string;
  body: string;
  request_id: string | null;
  created_at: string;
}

export interface ReviewOutcomeResponse {
  id: string;
  review_task_id: string;
  actor_user_id: string;
  actor_membership_id: string;
  outcome_type: ReviewOutcomeType | string;
  proposed_journal_id: string | null;
  source_correction_count: number;
  reason: string | null;
  request_id: string | null;
  created_at: string;
}

export interface ReviewAuditEventResponse {
  id: string;
  actor_user_id: string | null;
  event_type: string;
  target_type: string;
  target_id: string;
  occurred_at: string;
  request_id: string | null;
  metadata: Record<string, unknown>;
}

export interface ReviewHistoryResponse {
  task: ReviewTaskResponse;
  comments: ReviewCommentResponse[];
  outcome: ReviewOutcomeResponse | null;
  audit_events: ReviewAuditEventResponse[];
}

export interface ReviewInteractionResponse {
  task: ReviewTaskResponse;
  comment: ReviewCommentResponse;
}

export interface ReviewResolutionResponse {
  task: ReviewTaskResponse;
  outcome: ReviewOutcomeResponse;
}

export interface ReviewTaskLineage {
  clientId: string;
  documentId: string;
  extractionRunId: string;
  decisionRunId: string;
  reviewTaskId: string;
}
