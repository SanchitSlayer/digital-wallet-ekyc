import { useState, type FormEvent } from "react";

import { errorMessage } from "../../api/client";
import { createPaymentQr, type PaymentQr } from "../../api/payments";
import { ErrorMessage } from "../../components/ErrorMessage";
import { FormField } from "../../components/FormField";
import { SubmitButton } from "../../components/SubmitButton";
import { formatPaise, rupeesToPaise } from "../wallet/money";

export function ReceivePage() {
  const [rupees, setRupees] = useState("");
  const [qr, setQr] = useState<PaymentQr | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const amountPaise = rupees.trim() === "" ? null : rupeesToPaise(rupees);
    if (rupees.trim() !== "" && amountPaise === null) {
      setError("Enter the amount in rupees, for example 250 or 99.50, or leave it empty.");
      return;
    }
    setError(null);
    setIsSubmitting(true);
    try {
      setQr(await createPaymentQr({ amount_paise: amountPaise }));
    } catch (createError) {
      setError(errorMessage(createError));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="mx-auto max-w-md space-y-6">
      <h1 className="text-2xl font-semibold">Receive money</h1>
      <form onSubmit={handleSubmit} className="space-y-4">
        <FormField
          id="receive-amount"
          label="Amount in Rs (leave empty to let the payer choose)"
          inputMode="decimal"
          value={rupees}
          onChange={(event) => setRupees(event.target.value)}
        />
        <ErrorMessage message={error} />
        <SubmitButton isLoading={isSubmitting} loadingLabel="Generating...">
          Generate QR code
        </SubmitButton>
      </form>
      {qr && (
        <section className="space-y-2 rounded-lg border border-slate-200 bg-white p-5 text-center">
          <img
            src={`data:image/png;base64,${qr.qr_png_base64}`}
            alt="Payment QR code"
            className="mx-auto w-64"
          />
          <p className="font-medium">{qr.amount_paise === null ? "Any amount" : formatPaise(qr.amount_paise)}</p>
          <p className="text-sm text-slate-500">Valid until {new Date(qr.expires_at).toLocaleTimeString()}</p>
        </section>
      )}
    </div>
  );
}
