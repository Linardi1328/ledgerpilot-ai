import { ApiError } from "./errors";

export interface RequestOptions extends RequestInit {
  devSubject?: string;
  firmId?: string;
  requestId?: string;
  searchParams?: Record<string, string>;
}

export class ApiClient {
  private baseUrl: string;

  constructor(baseUrl?: string) {
    // In browser client-side, prefer using Next.js proxy route /api/backend or provided baseUrl
    this.baseUrl = baseUrl || (typeof window !== "undefined" ? "/api/backend" : (process.env.BACKEND_INTERNAL_URL || "http://127.0.0.1:8000/api/v1"));
  }

  async request<T>(path: string, options: RequestOptions = {}): Promise<T> {
    const { devSubject, firmId, requestId, searchParams, ...fetchOptions } = options;

    let url = path.startsWith("http") ? path : `${this.baseUrl}${path.startsWith("/") ? path : `/${path}`}`;
    if (searchParams) {
      const params = new URLSearchParams(searchParams);
      url += `?${params.toString()}`;
    }

    const headers = new Headers(fetchOptions.headers || {});
    if (!headers.has("Content-Type") && !(fetchOptions.body instanceof FormData)) {
      headers.set("Content-Type", "application/json");
    }
    if (!headers.has("Accept")) {
      headers.set("Accept", "application/json");
    }

    if (devSubject) {
      headers.set("X-LedgerPilot-Dev-Subject", devSubject);
    }
    if (firmId) {
      headers.set("X-LedgerPilot-Firm", firmId);
    }
    if (requestId) {
      headers.set("X-Request-ID", requestId);
    }

    let response: Response;
    try {
      response = await fetch(url, {
        ...fetchOptions,
        headers,
      });
    } catch (networkError) {
      throw new ApiError(
        0,
        "backend_unavailable",
        "Could not connect to LedgerPilot AI backend server."
      );
    }

    let payload: unknown;
    const contentType = response.headers.get("content-type");
    if (contentType && contentType.includes("application/json")) {
      try {
        payload = await response.json();
      } catch {
        payload = null;
      }
    } else {
      payload = await response.text();
    }

    if (!response.ok) {
      throw ApiError.fromResponse(response.status, payload, response.statusText);
    }

    return payload as T;
  }

  get<T>(path: string, options?: RequestOptions): Promise<T> {
    return this.request<T>(path, { ...options, method: "GET" });
  }

  post<T>(path: string, body?: unknown, options?: RequestOptions): Promise<T> {
    return this.request<T>(path, {
      ...options,
      method: "POST",
      body: body instanceof FormData ? body : JSON.stringify(body ?? {}),
    });
  }
}

export const defaultApiClient = new ApiClient();
