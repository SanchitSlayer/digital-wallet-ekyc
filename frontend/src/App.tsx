import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router";

import { NavBar } from "./components/NavBar";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { LoginPage } from "./features/auth/LoginPage";
import { RegisterPage } from "./features/auth/RegisterPage";
import { AdminKycReviewPage } from "./features/kyc/AdminKycReviewPage";
import { KycStatusPage } from "./features/kyc/KycStatusPage";
import { KycUploadPage } from "./features/kyc/KycUploadPage";
import { AdminLedgerPage } from "./features/ledger/AdminLedgerPage";
import { ReceivePage } from "./features/payments/ReceivePage";
import { WalletPage } from "./features/wallet/WalletPage";

// The QR scanner library is large, so it is downloaded only when someone opens the Pay page.
const PayPage = lazy(() => import("./features/payments/PayPage").then((module) => ({ default: module.PayPage })));

export function App() {
  return (
    <>
      <NavBar />
      <main className="mx-auto max-w-4xl px-4 py-8">
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route element={<ProtectedRoute />}>
            <Route path="/" element={<Navigate to="/wallet" replace />} />
            <Route path="/kyc/status" element={<KycStatusPage />} />
            <Route path="/kyc/upload" element={<KycUploadPage />} />
            <Route path="/wallet" element={<WalletPage />} />
            <Route path="/receive" element={<ReceivePage />} />
            <Route
              path="/pay"
              element={
                <Suspense fallback={<p className="text-slate-500">Loading the scanner...</p>}>
                  <PayPage />
                </Suspense>
              }
            />
          </Route>
          <Route element={<ProtectedRoute requireAdmin />}>
            <Route path="/admin/kyc" element={<AdminKycReviewPage />} />
            <Route path="/admin/ledger" element={<AdminLedgerPage />} />
          </Route>
          <Route path="*" element={<p>Page not found.</p>} />
        </Routes>
      </main>
    </>
  );
}
