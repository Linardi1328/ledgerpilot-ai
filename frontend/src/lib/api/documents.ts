import { ApiClient, defaultApiClient, RequestOptions } from "./client";
import { DocumentMetadataResponse } from "@/types/api";

export async function uploadDocument(
  clientId: string,
  file: File,
  client: ApiClient = defaultApiClient,
  options?: RequestOptions
): Promise<DocumentMetadataResponse> {
  const formData = new FormData();
  formData.append("file", file);
  return client.post<DocumentMetadataResponse>(`/clients/${clientId}/documents`, formData, options);
}

export async function fetchDocumentMetadata(
  clientId: string,
  documentId: string,
  client: ApiClient = defaultApiClient,
  options?: RequestOptions
): Promise<DocumentMetadataResponse> {
  return client.get<DocumentMetadataResponse>(`/clients/${clientId}/documents/${documentId}`, options);
}
