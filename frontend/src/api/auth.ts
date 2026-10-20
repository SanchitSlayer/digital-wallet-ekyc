import { getJson, postJson } from "./client";
import type { components } from "./schema";

export type UserResponse = components["schemas"]["UserResponse"];
export type RegisterRequest = components["schemas"]["RegisterRequest"];
export type LoginRequest = components["schemas"]["LoginRequest"];
type TokenResponse = components["schemas"]["TokenResponse"];

export function register(body: RegisterRequest): Promise<UserResponse> {
  return postJson("/auth/register", body);
}

export function login(body: LoginRequest): Promise<TokenResponse> {
  return postJson("/auth/login", body);
}

export function fetchCurrentUser(): Promise<UserResponse> {
  return getJson("/auth/me");
}
