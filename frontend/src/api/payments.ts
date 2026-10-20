import { postJson } from "./client";
import type { components } from "./schema";

export type PaymentQr = components["schemas"]["PaymentQrResponse"];
export type PaymentPreview = components["schemas"]["PaymentPreviewResponse"];
export type Transfer = components["schemas"]["TransferResponse"];
type CreatePaymentQrRequest = components["schemas"]["CreatePaymentQrRequest"];
type QrPayloadRequest = components["schemas"]["QrPayloadRequest"];
type PayWithQrRequest = components["schemas"]["PayWithQrRequest"];

export function createPaymentQr(body: CreatePaymentQrRequest): Promise<PaymentQr> {
  return postJson("/payments/qr", body);
}

export function previewPayment(body: QrPayloadRequest): Promise<PaymentPreview> {
  return postJson("/payments/qr/preview", body);
}

export function payWithQr(body: PayWithQrRequest, idempotencyKey: string): Promise<Transfer> {
  return postJson("/payments/qr/pay", body, { "Idempotency-Key": idempotencyKey });
}
