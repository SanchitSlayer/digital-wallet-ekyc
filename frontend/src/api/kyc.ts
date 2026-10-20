import { getBlob, getJson, postForm, postJson } from "./client";
import type { components } from "./schema";

export type KycStatus = components["schemas"]["KycStatus"];
export type KycSubmission = components["schemas"]["KycSubmissionResponse"];
export type AdminKycSubmission = components["schemas"]["AdminKycSubmissionResponse"];
type RejectKycRequest = components["schemas"]["RejectKycRequest"];

export function submitKyc(image: File): Promise<KycSubmission> {
  const form = new FormData();
  form.append("image", image);
  return postForm("/kyc/submissions", form);
}

export function fetchMySubmission(): Promise<KycSubmission | null> {
  return getJson("/kyc/submissions/me");
}

export function fetchSubmissions(status: KycStatus): Promise<AdminKycSubmission[]> {
  return getJson(`/admin/kyc/submissions?status=${status}`);
}

export function fetchSubmissionImage(submissionId: string): Promise<Blob> {
  return getBlob(`/admin/kyc/submissions/${submissionId}/image`);
}

export function approveSubmission(submissionId: string): Promise<AdminKycSubmission> {
  return postJson(`/admin/kyc/submissions/${submissionId}/approve`);
}

export function rejectSubmission(submissionId: string, body: RejectKycRequest): Promise<AdminKycSubmission> {
  return postJson(`/admin/kyc/submissions/${submissionId}/reject`, body);
}
