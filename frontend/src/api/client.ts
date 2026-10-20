import { getToken } from "../features/auth/session";
import type { components } from "./schema";

type ValidationError = components["schemas"]["ValidationError"];

const API_URL = import.meta.env.VITE_API_URL;

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

let onUnauthorized: () => void = () => {};

export function setUnauthorizedHandler(handler: () => void): void {
  onUnauthorized = handler;
}

function describeValidationErrors(errors: ValidationError[]): string {
  // FastAPI reports each invalid field as a location path such as ["body", "email"]; the first part is noise for users.
  return errors.map((error) => `${error.loc.slice(1).join(".")}: ${error.msg}`).join("; ");
}

async function readErrorMessage(response: Response): Promise<string> {
  const fallback = `Request failed with status ${response.status} ${response.statusText}`;
  if (!response.headers.get("content-type")?.includes("application/json")) {
    return fallback;
  }
  const body: { detail?: string | ValidationError[] } = await response.json();
  if (typeof body.detail === "string") {
    return body.detail;
  }
  if (Array.isArray(body.detail)) {
    return describeValidationErrors(body.detail);
  }
  return fallback;
}

async function send(path: string, init: RequestInit): Promise<Response> {
  const headers = new Headers(init.headers);
  const token = getToken();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, { ...init, headers });
  } catch {
    throw new ApiError(0, `Could not reach the API at ${API_URL}. Check that the backend server is running.`);
  }

  if (response.status === 401 && token) {
    onUnauthorized();
  }
  if (!response.ok) {
    throw new ApiError(response.status, await readErrorMessage(response));
  }
  return response;
}

export async function getJson<T>(path: string): Promise<T> {
  return (await send(path, { method: "GET" })).json();
}

export async function postJson<T>(path: string, body?: unknown, headers?: Record<string, string>): Promise<T> {
  const response = await send(path, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...headers },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  return response.json();
}

export async function postForm<T>(path: string, form: FormData): Promise<T> {
  return (await send(path, { method: "POST", body: form })).json();
}

export async function getBlob(path: string): Promise<Blob> {
  return (await send(path, { method: "GET" })).blob();
}
