import { useEffect, useState } from "react";
import { Link } from "react-router";

import { errorMessage } from "../../api/client";
import { fetchMySubmission, type KycStatus, type KycSubmission } from "../../api/kyc";
import { ErrorMessage } from "../../components/ErrorMessage";

const STATUS_STYLES: Record<KycStatus, string> = {
  PENDING: "bg-amber-100 text-amber-800",
  VERIFIED: "bg-emerald-100 text-emerald-800",
  REJECTED: "bg-red-100 text-red-800",
};

const STATUS_MESSAGES: Record<KycStatus, string> = {
  PENDING: "Your ID is waiting for an admin to review it.",
  VERIFIED: "Your identity is verified.",
  REJECTED: "Your ID was rejected. Fix the issue below and upload a new image.",
};

export function KycStatusPage() {
  const [submission, setSubmission] = useState<KycSubmission | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchMySubmission()
      .then(setSubmission)
      .catch((loadError) => setError(errorMessage(loadError)))
      .finally(() => setIsLoading(false));
  }, []);

  if (isLoading) {
    return <p className="text-slate-500">Loading your KYC status...</p>;
  }

  return (
    <div className="mx-auto max-w-lg space-y-4">
      <h1 className="text-2xl font-semibold">KYC status</h1>
      <ErrorMessage message={error} />
      {submission === null && error === null && (
        <p>
          You have not submitted an ID yet.{" "}
          <Link to="/kyc/upload" className="text-indigo-600 hover:underline">
            Upload your ID card
          </Link>
        </p>
      )}
      {submission && (
        <div className="space-y-3 rounded-lg border border-slate-200 bg-white p-5">
          <span className={`inline-block rounded-full px-3 py-1 text-sm font-medium ${STATUS_STYLES[submission.status]}`}>
            {submission.status}
          </span>
          <p>{STATUS_MESSAGES[submission.status]}</p>
          <dl className="grid grid-cols-2 gap-2 text-sm">
            <dt className="text-slate-500">ID number</dt>
            <dd>{submission.id_number ?? "Not detected"}</dd>
            <dt className="text-slate-500">Name match</dt>
            <dd>{submission.name_match_score}%</dd>
            <dt className="text-slate-500">Submitted</dt>
            <dd>{new Date(submission.created_at).toLocaleString()}</dd>
          </dl>
          {submission.status === "REJECTED" && (
            <>
              <p className="rounded-md bg-red-50 p-3 text-sm text-red-800">Reason: {submission.rejection_reason}</p>
              <Link to="/kyc/upload" className="text-indigo-600 hover:underline">
                Upload a new image
              </Link>
            </>
          )}
        </div>
      )}
    </div>
  );
}
