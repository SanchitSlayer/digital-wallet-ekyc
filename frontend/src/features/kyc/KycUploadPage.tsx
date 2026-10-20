import { useEffect, useState, type ChangeEvent, type FormEvent } from "react";
import { useNavigate } from "react-router";

import { errorMessage } from "../../api/client";
import { submitKyc } from "../../api/kyc";
import { ErrorMessage } from "../../components/ErrorMessage";
import { SubmitButton } from "../../components/SubmitButton";

export function KycUploadPage() {
  const navigate = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (file === null) {
      setPreviewUrl(null);
      return;
    }
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
    // Object URLs hold the file in memory until revoked, so each preview is released when replaced.
    return () => URL.revokeObjectURL(url);
  }, [file]);

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    setError(null);
    setFile(event.target.files?.[0] ?? null);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (file === null) {
      setError("Choose an image of your ID card before submitting.");
      return;
    }
    setError(null);
    setIsSubmitting(true);
    try {
      await submitKyc(file);
      navigate("/kyc/status");
    } catch (uploadError) {
      setError(errorMessage(uploadError));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="mx-auto max-w-lg">
      <h1 className="mb-2 text-2xl font-semibold">Upload your ID card</h1>
      <p className="mb-6 text-sm text-slate-600">
        JPEG or PNG, up to 5 MB. Make sure the whole card is visible, sharp and well lit.
      </p>
      <form onSubmit={handleSubmit} className="space-y-4">
        <input
          type="file"
          accept="image/jpeg,image/png"
          onChange={handleFileChange}
          className="block w-full text-sm file:mr-4 file:rounded-md file:border-0 file:bg-indigo-50 file:px-4 file:py-2 file:text-indigo-700"
        />
        {previewUrl && (
          <img src={previewUrl} alt="Preview of the selected ID card" className="max-h-72 rounded-md border" />
        )}
        <ErrorMessage message={error} />
        <SubmitButton isLoading={isSubmitting} loadingLabel="Reading your ID card...">
          Submit for verification
        </SubmitButton>
      </form>
    </div>
  );
}
