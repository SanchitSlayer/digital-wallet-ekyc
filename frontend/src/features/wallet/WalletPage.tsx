import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router";

import { errorMessage } from "../../api/client";
import { fetchTransactions, fetchWallet, topUp, type LedgerEntry, type Wallet } from "../../api/wallet";
import { ErrorMessage } from "../../components/ErrorMessage";
import { FormField } from "../../components/FormField";
import { SubmitButton } from "../../components/SubmitButton";
import { formatPaise, rupeesToPaise } from "./money";

const ENTRY_LABELS: Record<LedgerEntry["entry_type"], string> = {
  TOP_UP: "Top-up",
  TRANSFER_DEBIT: "Paid to",
  TRANSFER_CREDIT: "Received from",
};

function TopUpForm({ onToppedUp }: { onToppedUp: () => void }) {
  const [rupees, setRupees] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const amountPaise = rupeesToPaise(rupees);
    if (amountPaise === null) {
      setError("Enter the amount in rupees, for example 500 or 99.50.");
      return;
    }
    setError(null);
    setIsSubmitting(true);
    try {
      await topUp({ amount_paise: amountPaise });
      setRupees("");
      onToppedUp();
    } catch (topUpError) {
      setError(errorMessage(topUpError));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3 rounded-lg border border-dashed border-amber-300 bg-amber-50 p-4">
      <p className="text-sm text-amber-800">Development only: add fake money to test payments.</p>
      <div className="flex items-end gap-2">
        <div className="flex-1">
          <FormField
            id="top-up-amount"
            label="Amount (Rs)"
            inputMode="decimal"
            required
            value={rupees}
            onChange={(event) => setRupees(event.target.value)}
          />
        </div>
        <SubmitButton isLoading={isSubmitting} loadingLabel="Adding...">
          Top up
        </SubmitButton>
      </div>
      <ErrorMessage message={error} />
    </form>
  );
}

export function WalletPage() {
  const [wallet, setWallet] = useState<Wallet | null>(null);
  const [entries, setEntries] = useState<LedgerEntry[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [loadedWallet, loadedEntries] = await Promise.all([fetchWallet(), fetchTransactions()]);
      setWallet(loadedWallet);
      setEntries(loadedEntries);
      setError(null);
    } catch (loadError) {
      setError(errorMessage(loadError));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  if (isLoading) {
    return <p className="text-slate-500">Loading your wallet...</p>;
  }
  if (wallet === null) {
    return (
      <div className="mx-auto max-w-lg space-y-4">
        <h1 className="text-2xl font-semibold">Wallet</h1>
        <ErrorMessage message={error} />
        <Link to="/kyc/status" className="text-indigo-600 hover:underline">
          Check your KYC status
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <section className="rounded-lg bg-indigo-600 p-6 text-white">
        <p className="text-sm text-indigo-100">Available balance</p>
        <p className="text-4xl font-semibold">{formatPaise(wallet.balance_paise)}</p>
        <div className="mt-4 flex gap-3">
          <Link to="/receive" className="rounded-md bg-white px-4 py-2 font-medium text-indigo-700">
            Receive
          </Link>
          <Link to="/pay" className="rounded-md bg-indigo-500 px-4 py-2 font-medium text-white">
            Pay
          </Link>
        </div>
      </section>
      <ErrorMessage message={error} />
      {wallet.top_up_enabled && <TopUpForm onToppedUp={load} />}
      <section>
        <h2 className="mb-3 text-lg font-semibold">Transactions</h2>
        {entries.length === 0 ? (
          <p className="text-slate-600">No transactions yet.</p>
        ) : (
          <ul className="divide-y divide-slate-200 rounded-lg border border-slate-200 bg-white">
            {entries.map((entry) => (
              <li key={entry.id} className="flex items-center justify-between px-4 py-3">
                <div>
                  <p className="font-medium">
                    {ENTRY_LABELS[entry.entry_type]} {entry.counterparty_name}
                  </p>
                  <p className="text-xs text-slate-500">{new Date(entry.created_at).toLocaleString()}</p>
                </div>
                <div className="text-right">
                  <p className={entry.amount_paise > 0 ? "font-semibold text-emerald-700" : "font-semibold text-slate-900"}>
                    {entry.amount_paise > 0 ? "+" : ""}
                    {formatPaise(entry.amount_paise)}
                  </p>
                  <p className="text-xs text-slate-500">Balance {formatPaise(entry.balance_after_paise)}</p>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
