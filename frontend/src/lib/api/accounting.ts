import { ApiClient, defaultApiClient, RequestOptions } from "./client";
import { AccountingDecisionRunResponse } from "@/types/api";

export async function createAccountingDecisionRun(
  clientId: string,
  documentId: string,
  extractionRunId: string,
  client: ApiClient = defaultApiClient,
  options?: RequestOptions
): Promise<AccountingDecisionRunResponse> {
  return client.post<AccountingDecisionRunResponse>(
    `/clients/${clientId}/documents/${documentId}/extractions/${extractionRunId}/accounting-decisions`,
    {},
    options
  );
}

export async function fetchAccountingDecisionRun(
  clientId: string,
  documentId: string,
  extractionRunId: string,
  decisionRunId: string,
  client: ApiClient = defaultApiClient,
  options?: RequestOptions
): Promise<AccountingDecisionRunResponse> {
  return client.get<AccountingDecisionRunResponse>(
    `/clients/${clientId}/documents/${documentId}/extractions/${extractionRunId}/accounting-decisions/${decisionRunId}`,
    options
  );
}
