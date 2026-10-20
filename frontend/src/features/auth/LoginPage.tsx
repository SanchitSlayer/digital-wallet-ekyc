import { useState, type FormEvent } from "react";
import { Link, Navigate, useLocation } from "react-router";

import { errorMessage } from "../../api/client";
import { ErrorMessage } from "../../components/ErrorMessage";
import { FormField } from "../../components/FormField";
import { SubmitButton } from "../../components/SubmitButton";
import { useAuth } from "./AuthContext";

export function LoginPage() {
  const { user, login } = useAuth();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const redirectTo: string = location.state?.from ?? "/";

  if (user) {
    return <Navigate to={redirectTo} replace />;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await login({ email, password });
    } catch (loginError) {
      setError(errorMessage(loginError));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="mx-auto max-w-sm">
      <h1 className="mb-6 text-2xl font-semibold">Log in</h1>
      <form onSubmit={handleSubmit} className="space-y-4">
        <FormField
          id="email"
          label="Email"
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(event) => setEmail(event.target.value)}
        />
        <FormField
          id="password"
          label="Password"
          type="password"
          autoComplete="current-password"
          required
          value={password}
          onChange={(event) => setPassword(event.target.value)}
        />
        <ErrorMessage message={error} />
        <SubmitButton isLoading={isSubmitting} loadingLabel="Logging in...">
          Log in
        </SubmitButton>
      </form>
      <p className="mt-4 text-sm text-slate-600">
        No account yet?{" "}
        <Link to="/register" className="text-indigo-600 hover:underline">
          Register
        </Link>
      </p>
    </div>
  );
}
