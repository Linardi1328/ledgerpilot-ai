import { ApiClient, defaultApiClient, RequestOptions } from "./client";
import {
  ExtractedFieldResponse,
  ExtractionFieldCorrectionRequest,
  ExtractionRunResponse,
} from "@/types/api";

export async function createExtractionRun(
  clientId: string,
  documentId: string,
  client: ApiClient = defaultApiClient,
  options?: RequestOptions
): Promise<ExtractionRunResponse> {
  return client.post<ExtractionRunResponse>(
    `/clients/${clientId}/documents/${documentId}/extractions`,
    {},
    options
  );
}

export async function fetchExtractionRun(
  clientId: string,
  documentId: string,
  runId: string,
  client: ApiClient = defaultApiClient,
  options?: RequestOptions
): Promise<ExtractionRunResponse> {
  return client.get<ExtractionRunResponse>(
    `/clients/${clientId}/documents/${documentId}/extractions/${runId}`,
    options
  );
}

export async function addFieldCorrection(
  clientId: string,
  documentId: string,
  runId: string,
  fieldId: string,
  correction: ExtractionFieldCorrectionRequest,
  client: ApiClient = defaultApiClient,
  options?: RequestOptions
): Promise<ExtractedFieldResponse> {
  return client.post<ExtractedFieldResponse>(
    `/clients/${clientId}/documents/${documentId}/extractions/${runId}/fields/${fieldId}/corrections`,
    correction,
    options
  );
}
