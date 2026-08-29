import { ReviewTaskLineage } from "@/types/api";

export function buildLiveReviewTaskUrl(lineage: ReviewTaskLineage): string {
  return `/reviews/${lineage.clientId}/documents/${lineage.documentId}/extractions/${lineage.extractionRunId}/decisions/${lineage.decisionRunId}/tasks/${lineage.reviewTaskId}`;
}

export function buildLivePortalUrl(lineage: ReviewTaskLineage): string {
  return `/portal/${lineage.clientId}/documents/${lineage.documentId}/extractions/${lineage.extractionRunId}/decisions/${lineage.decisionRunId}/tasks/${lineage.reviewTaskId}`;
}

export function buildReviewTaskApiPath(lineage: ReviewTaskLineage): string {
  return `/clients/${lineage.clientId}/documents/${lineage.documentId}/extractions/${lineage.extractionRunId}/accounting-decisions/${lineage.decisionRunId}/review-tasks/${lineage.reviewTaskId}`;
}

export function buildDecisionApiPath(clientId: string, documentId: string, extractionRunId: string, decisionRunId: string): string {
  return `/clients/${clientId}/documents/${documentId}/extractions/${extractionRunId}/accounting-decisions/${decisionRunId}`;
}

export function buildExtractionApiPath(clientId: string, documentId: string, extractionRunId: string): string {
  return `/clients/${clientId}/documents/${documentId}/extractions/${extractionRunId}`;
}

export function buildDocumentApiPath(clientId: string, documentId: string): string {
  return `/clients/${clientId}/documents/${documentId}`;
}
