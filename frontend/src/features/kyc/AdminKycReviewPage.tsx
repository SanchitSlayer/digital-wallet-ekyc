import { useEffect, useState } from "react";

import { errorMessage } from "../../api/client";
import {
  approveSubmission,
  fetchSubmissionImage,
  fetchSubmissions,
  rejectSubmission,
  type AdminKycSubmission,
} from "../../api/kyc";
import { ErrorMessage } from "../../components/ErrorMessage";
import { SubmitButton } from "../../components/SubmitButton";

function SubmissionImage({ submissionId }: { submissionId: string }) {
  const [url, setUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let objectUrl: string | null = null;
    // The image endpoint needs the admin's token, which an <img src> cannot send, so it is fetched as a blob.
    fetchSubmissionImage(submissionId)
      .then((blob) => {
        objectUrl = URL.createObjectURL(blob);
        setUrl(objectUrl);
      })
      .catch((loadError) => setError(errorMessage(loadError)));
    return () => {
      if (objectUrl) {
        URL.revokeObjectURL(objectUrl);
      }
    };
  }, [submissionId]);

  if (error) {
    return <ErrorMessage message={error} />;
  }
  if (url === null) {
    return <p className="text-sm text-slate-500">Loading image...</p>;
  }
  return <img src={url} alt="Uploaded ID card" className="max-h-64 rounded-md border" />;
}

function SubmissionCard({ submission, onReviewed }: { submission: AdminKycSubmission; onReviewed: () => void }) {
  const [reason, setReason] = useState("");
  const [pendingAction, setPendingAction] = useState<"approve" | "reject" | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function review(action: "approve" | "reject") {
    setError(null);
    setPendingAction(action);
    try {
      if (action === "approve") {
        await approveSubmission(submission.id);
      } else {
        await rejectSubmission(submission.id, { reason });
      }
      onReviewed();
    } catch (reviewError) {
      setError(errorMessage(reviewError));
      setPendingAction(null);
    }
  }

  return (
    <article className="grid gap-4 rounded-lg border border-slate-200 bg-white p-5 md:grid-cols-2">
      <SubmissionImage submissionId={submission.id} />
      <div className="space-y-3 text-sm">
        <div>
          <p className="font-semibold">{submission.user.full_name}</p>
          <p className="text-slate-500">{submission.user.email}</p>
        </div>
        <dl className="grid grid-cols-2 gap-1">
          <dt className="text-slate-500">ID number</dt>
          <dd>{submission.id_number ?? "Not detected"}</dd>
          <dt className="text-slate-500">Name on card</dt>
          <dd>{submission.extracted_name ?? "Not detected"}</dd>
          <dt className="text-slate-500">Name match</dt>
          <dd>{submission.name_match_score}%</dd>
          <dt className="text-slate-500">Submitted</dt>
          <dd>{new Date(submission.created_at).toLocaleString()}</dd>
        </dl>
        <details>
          <summary className="cursor-pointer text-slate-600">OCR text</summary>
          <pre className="mt-2 whitespace-pre-wrap rounded bg-slate-100 p-2 text-xs">{submission.ocr_text}</pre>
        </details>
        <textarea
          value={reason}
          onChange={(event) => setReason(event.target.value)}
          placeholder="Rejection reason shown to the user (at least 5 characters)"
          className="w-full rounded-md border border-slate-300 p-2"
          rows={2}
        />
        <ErrorMessage message={error} />
        <div className="flex gap-2">
          <SubmitButton
            type="button"
            isLoading={pendingAction === "approve"}
            loadingLabel="Approving..."
            disabled={pendingAction !== null}
            onClick={() => review("approve")}
          >
            Approve
          </SubmitButton>
          <SubmitButton
            type="button"
            variant="danger"
            isLoading={pendingAction === "reject"}
            loadingLabel="Rejecting..."
            disabled={pendingAction !== null}
            onClick={() => review("reject")}
          >
            Reject
          </SubmitButton>
        </div>
      </div>
    </article>
  );
}

export function AdminKycReviewPage() {
  const [submissions, setSubmissions] = useState<AdminKycSubmission[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchSubmissions("PENDING")
      .then(setSubmissions)
      .catch((loadError) => setError(errorMessage(loadError)))
      .finally(() => setIsLoading(false));
  }, []);

  function removeSubmission(submissionId: string) {
    setSubmissions((current) => current.filter((submission) => submission.id !== submissionId));
  }

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Pending KYC submissions</h1>
      <ErrorMessage message={error} />
      {isLoading && <p className="text-slate-500">Loading submissions...</p>}
      {!isLoading && submissions.length === 0 && error === null && (
        <p className="text-slate-600">No submissions are waiting for review.</p>
      )}
      {submissions.map((submission) => (
        <SubmissionCard
          key={submission.id}
          submission={submission}
          onReviewed={() => removeSubmission(submission.id)}
        />
      ))}
    </div>
  );
}
