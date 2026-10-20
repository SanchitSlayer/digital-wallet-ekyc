import { getJson } from "./client";
import type { components } from "./schema";

export type LedgerVerification = components["schemas"]["LedgerVerificationResponse"];

export function verifyLedger(): Promise<LedgerVerification> {
  return getJson("/admin/ledger/verify");
}
