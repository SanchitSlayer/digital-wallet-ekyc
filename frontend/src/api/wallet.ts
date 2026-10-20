import { getJson, postJson } from "./client";
import type { components } from "./schema";

export type Wallet = components["schemas"]["WalletResponse"];
export type LedgerEntry = components["schemas"]["LedgerEntryResponse"];
type TopUpRequest = components["schemas"]["TopUpRequest"];

export function fetchWallet(): Promise<Wallet> {
  return getJson("/wallet");
}

export function fetchTransactions(): Promise<LedgerEntry[]> {
  return getJson("/wallet/transactions");
}

export function topUp(body: TopUpRequest): Promise<Wallet> {
  return postJson("/wallet/top-up", body);
}
