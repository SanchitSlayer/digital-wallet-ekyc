import { useState } from "react";

import { errorMessage } from "../../api/client";
import { verifyLedger, type LedgerVerification } from "../../api/ledger";
import { ErrorMessage } from "../../components/ErrorMessage";
import { SubmitButton } from "../../components/SubmitButton";

export function AdminLedgerPage() {
  const [result, setResult] = useState<LedgerVerification | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isChecking, setIsChecking] = useState(false);

  async function handleVerify() {
    setError(null);
    setIsChecking(true);
    try {
      setResult(await verifyLedger());
    } catch (verifyError) {
      setError(errorMessage(verifyError));
    } finally {
      setIsChecking(false);
    }
  }

  return (
    <div className="mx-auto max-w-lg space-y-4">
      <h1 className="text-2xl font-semibold">Ledger verification</h1>
      <p className="text-sm text-slate-600">
        Recomputes the SHA-256 hash of every ledger entry in order and checks that each one links to the entry
        before it.
      </p>
      <SubmitButton type="button" isLoading={isChecking} loadingLabel="Verifying..." onClick={handleVerify}>
        Verify ledger
      </SubmitButton>
      <ErrorMessage message={error} />
      {result &&
        (result.intact ? (
          <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4">
            <p className="font-semibold text-emerald-800">Chain intact</p>
            <p className="text-sm text-emerald-700">{result.entries_checked} entries checked.</p>
          </div>
        ) : (
          <div className="rounded-lg border border-red-200 bg-red-50 p-4">
            <p className="font-semibold text-red-800">Broken at entry {result.broken_entry_id}</p>
            <p className="text-sm text-red-700">{result.reason}</p>
          </div>
        ))}
    </div>
  );
}
