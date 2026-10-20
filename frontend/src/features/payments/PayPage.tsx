import { useState } from "react";
import { Link } from "react-router";

import { errorMessage } from "../../api/client";
import { payWithQr, previewPayment, type PaymentPreview, type Transfer } from "../../api/payments";
import { ErrorMessage } from "../../components/ErrorMessage";
import { FormField } from "../../components/FormField";
import { SubmitButton } from "../../components/SubmitButton";
import { formatPaise, rupeesToPaise } from "../wallet/money";
import { QrScanner } from "./QrScanner";

interface Confirmation {
  qrText: string;
  preview: PaymentPreview;
  // One key per confirmation screen: pressing Pay again after a network error retries the same payment
  // instead of creating a second one.
  idempotencyKey: string;
}

function ConfirmPayment({
  confirmation,
  onPaid,
  onCancel,
}: {
  confirmation: Confirmation;
  onPaid: (transfer: Transfer) => void;
  onCancel: () => void;
}) {
  const { preview } = confirmation;
  const [rupees, setRupees] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isPaying, setIsPaying] = useState(false);

  async function handlePay() {
    const amountPaise = preview.amount_paise ?? rupeesToPaise(rupees);
    if (amountPaise === null) {
      setError("Enter the amount in rupees, for example 250 or 99.50.");
      return;
    }
    setError(null);
    setIsPaying(true);
    try {
      onPaid(
        await payWithQr(
          { qr_payload: confirmation.qrText, amount_paise: preview.amount_paise === null ? amountPaise : null },
          confirmation.idempotencyKey,
        ),
      );
    } catch (payError) {
      setError(errorMessage(payError));
      setIsPaying(false);
    }
  }

  return (
    <section className="space-y-4 rounded-lg border border-slate-200 bg-white p-5">
      <h2 className="text-lg font-semibold">Confirm payment</h2>
      <dl className="grid grid-cols-2 gap-2 text-sm">
        <dt className="text-slate-500">Paying</dt>
        <dd className="font-medium">{preview.receiver_name}</dd>
        <dt className="text-slate-500">Code valid until</dt>
        <dd>{new Date(preview.expires_at).toLocaleTimeString()}</dd>
        {preview.amount_paise !== null && (
          <>
            <dt className="text-slate-500">Amount</dt>
            <dd className="text-xl font-semibold">{formatPaise(preview.amount_paise)}</dd>
          </>
        )}
      </dl>
      {preview.amount_paise === null && (
        <FormField
          id="pay-amount"
          label="Amount (Rs)"
          inputMode="decimal"
          required
          value={rupees}
          onChange={(event) => setRupees(event.target.value)}
        />
      )}
      <ErrorMessage message={error} />
      <div className="flex gap-2">
        <SubmitButton type="button" isLoading={isPaying} loadingLabel="Paying..." onClick={handlePay}>
          Pay
        </SubmitButton>
        <button type="button" onClick={onCancel} disabled={isPaying} className="px-4 py-2 text-slate-600">
          Cancel
        </button>
      </div>
    </section>
  );
}

export function PayPage() {
  const [confirmation, setConfirmation] = useState<Confirmation | null>(null);
  const [transfer, setTransfer] = useState<Transfer | null>(null);
  const [isChecking, setIsChecking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleScan(qrText: string) {
    if (isChecking) {
      return;
    }
    setError(null);
    setIsChecking(true);
    try {
      const preview = await previewPayment({ qr_payload: qrText });
      setConfirmation({ qrText, preview, idempotencyKey: crypto.randomUUID() });
    } catch (previewError) {
      setError(errorMessage(previewError));
    } finally {
      setIsChecking(false);
    }
  }

  if (transfer) {
    return (
      <div className="mx-auto max-w-md space-y-4 rounded-lg border border-emerald-200 bg-emerald-50 p-6 text-center">
        <h1 className="text-2xl font-semibold text-emerald-800">Payment successful</h1>
        <p>
          {formatPaise(transfer.amount_paise)} sent to {transfer.receiver_name}
        </p>
        <p className="text-xs text-slate-500">Reference {transfer.id}</p>
        <Link to="/wallet" className="inline-block text-indigo-600 hover:underline">
          Back to wallet
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-md space-y-6">
      <h1 className="text-2xl font-semibold">Pay</h1>
      {confirmation ? (
        <ConfirmPayment confirmation={confirmation} onPaid={setTransfer} onCancel={() => setConfirmation(null)} />
      ) : (
        <>
          <p className="text-sm text-slate-600">Point your camera at the receiver's payment QR code.</p>
          <QrScanner onScan={handleScan} />
          {isChecking && <p className="text-slate-500">Checking the QR code...</p>}
          <ErrorMessage message={error} />
        </>
      )}
    </div>
  );
}
