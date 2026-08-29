import { ApiClient, defaultApiClient, RequestOptions } from "./client";
import { ContextResponse } from "@/types/api";

export async function fetchContext(
  client: ApiClient = defaultApiClient,
  options?: RequestOptions
): Promise<ContextResponse> {
  return client.get<ContextResponse>("/context", options);
}

export async function checkLiveness(
  client: ApiClient = defaultApiClient
): Promise<{ status: string }> {
  return client.get<{ status: string }>("/health/live");
}
