import { Navigate, Route, Routes } from "react-router";

import { NavBar } from "./components/NavBar";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { LoginPage } from "./features/auth/LoginPage";
import { RegisterPage } from "./features/auth/RegisterPage";
import { AdminKycReviewPage } from "./features/kyc/AdminKycReviewPage";
import { KycStatusPage } from "./features/kyc/KycStatusPage";
import { KycUploadPage } from "./features/kyc/KycUploadPage";

export function App() {
  return (
    <>
      <NavBar />
      <main className="mx-auto max-w-4xl px-4 py-8">
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route element={<ProtectedRoute />}>
            <Route path="/" element={<Navigate to="/kyc/status" replace />} />
            <Route path="/kyc/status" element={<KycStatusPage />} />
            <Route path="/kyc/upload" element={<KycUploadPage />} />
          </Route>
          <Route element={<ProtectedRoute requireAdmin />}>
            <Route path="/admin/kyc" element={<AdminKycReviewPage />} />
          </Route>
          <Route path="*" element={<p>Page not found.</p>} />
        </Routes>
      </main>
    </>
  );
}
