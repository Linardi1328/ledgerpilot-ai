import { ApiClient, defaultApiClient, RequestOptions } from "./client";
import { ContextResponse } from "@/types/api";
import { Permission, Principal, Role } from "@/types/roles";
import { ApiError } from "./errors";

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

/**
 * Validates the runtime payload from /api/v1/context against the authoritative Principal schema.
 * Throws ApiError if any required field is missing or contains an unmapped role/permission.
 */
export function validateContextResponse(payload: unknown): Principal {
  if (!payload || typeof payload !== "object") {
    throw new ApiError(422, "invalid_context_payload", "Context payload is not an object.");
  }

  const data = payload as Record<string, unknown>;

  if (typeof data.user_id !== "string" || !data.user_id.trim()) {
    throw new ApiError(422, "invalid_context_payload", "Context missing valid user_id.");
  }

  if (typeof data.firm_id !== "string" || !data.firm_id.trim()) {
    throw new ApiError(422, "invalid_context_payload", "Context missing valid firm_id.");
  }

  if (typeof data.membership_id !== "string" || !data.membership_id.trim()) {
    throw new ApiError(422, "invalid_context_payload", "Context missing valid membership_id.");
  }

  const validRoles = Object.values(Role) as string[];
  if (typeof data.role !== "string" || !validRoles.includes(data.role)) {
    throw new ApiError(422, "invalid_context_payload", `Unknown role in context: ${data.role}`);
  }

  if (!Array.isArray(data.permissions)) {
    throw new ApiError(422, "invalid_context_payload", "Context permissions must be an array.");
  }

  const validPermissions = Object.values(Permission) as string[];
  for (const perm of data.permissions) {
    if (typeof perm !== "string" || !validPermissions.includes(perm)) {
      throw new ApiError(422, "invalid_context_payload", `Unknown permission in context: ${perm}`);
    }
  }

  if (!Array.isArray(data.authorized_client_ids)) {
    throw new ApiError(422, "invalid_context_payload", "Context authorized_client_ids must be an array.");
  }

  for (const clientId of data.authorized_client_ids) {
    if (typeof clientId !== "string") {
      throw new ApiError(422, "invalid_context_payload", "Invalid client ID format in context.");
    }
  }

  return {
    user_id: data.user_id,
    firm_id: data.firm_id,
    membership_id: data.membership_id,
    role: data.role as Role,
    permissions: data.permissions as Permission[],
    authorized_client_ids: data.authorized_client_ids as string[],
  };
}
