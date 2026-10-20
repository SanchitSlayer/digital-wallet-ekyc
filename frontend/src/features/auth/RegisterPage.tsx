import { useState, type FormEvent } from "react";
import { Link, Navigate } from "react-router";

import { register, type RegisterRequest } from "../../api/auth";
import { errorMessage } from "../../api/client";
import { ErrorMessage } from "../../components/ErrorMessage";
import { FormField } from "../../components/FormField";
import { SubmitButton } from "../../components/SubmitButton";
import { useAuth } from "./AuthContext";

const EMPTY_FORM: RegisterRequest = { full_name: "", email: "", phone: "", password: "" };

export function RegisterPage() {
  const { user, login } = useAuth();
  const [form, setForm] = useState<RegisterRequest>(EMPTY_FORM);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Registering logs the user in, so this redirect is also what moves a new user on to the upload page.
  if (user) {
    return <Navigate to="/kyc/upload" replace />;
  }

  function updateField(field: keyof RegisterRequest, value: string) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await register(form);
      await login({ email: form.email, password: form.password });
    } catch (registerError) {
      setError(errorMessage(registerError));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="mx-auto max-w-sm">
      <h1 className="mb-6 text-2xl font-semibold">Create an account</h1>
      <form onSubmit={handleSubmit} className="space-y-4">
        <FormField
          id="full_name"
          label="Full name (as printed on your ID)"
          autoComplete="name"
          required
          value={form.full_name}
          onChange={(event) => updateField("full_name", event.target.value)}
        />
        <FormField
          id="email"
          label="Email"
          type="email"
          autoComplete="email"
          required
          value={form.email}
          onChange={(event) => updateField("email", event.target.value)}
        />
        <FormField
          id="phone"
          label="Phone (10 to 15 digits, optional leading +)"
          type="tel"
          autoComplete="tel"
          required
          value={form.phone}
          onChange={(event) => updateField("phone", event.target.value)}
        />
        <FormField
          id="password"
          label="Password (at least 8 characters)"
          type="password"
          autoComplete="new-password"
          required
          value={form.password}
          onChange={(event) => updateField("password", event.target.value)}
        />
        <ErrorMessage message={error} />
        <SubmitButton isLoading={isSubmitting} loadingLabel="Creating account...">
          Register
        </SubmitButton>
      </form>
      <p className="mt-4 text-sm text-slate-600">
        Already registered?{" "}
        <Link to="/login" className="text-indigo-600 hover:underline">
          Log in
        </Link>
      </p>
    </div>
  );
}
