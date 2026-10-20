# Security Review

This review covers the prototype as built: a local, fake-money proof of concept. Each OWASP Top 10 (2021) category is listed with what the project does and what is out of scope. The last sections cover personal data and the changes needed before any production use.

## OWASP Top 10

### A01 Broken Access Control
- Every endpoint except `/auth/register`, `/auth/login` and `/health` requires a valid JWT through the `CurrentUser` dependency.
- Admin endpoints (`/admin/kyc/...`, `/admin/ledger/verify`) use the `AdminUser` dependency, which returns 403 for non-admins. A parametrized test checks every admin endpoint with a normal user's token.
- The role is read from the database on each request, not trusted from the token, so a demotion takes effect immediately.
- Users only ever act on their own wallet: the sender wallet is always derived from the authenticated user, never taken from the request body.
- Admins cannot review their own KYC submission.
- Admins can only be created with the server-side `scripts/create_admin.py`; the API always creates the `user` role.
- The frontend hides admin links and blocks admin routes for normal users, but the backend is the real enforcement point.

### A02 Cryptographic Failures
- Passwords are hashed with bcrypt (cost 12, random salt per password). Passwords longer than bcrypt's 72-byte limit are rejected instead of silently truncated.
- JWTs are signed with HS256 using `JWT_SECRET_KEY`, and decoding pins the accepted algorithm.
- QR payment requests are signed with HMAC-SHA256 using a separate `QR_SIGNING_KEY` and compared in constant time.
- Ledger entries are chained with SHA-256.
- Secrets come from environment variables. `.env` is git-ignored and `.env.example` holds only placeholders.
- Out of scope: TLS. The prototype runs over plain HTTP on localhost. Production must terminate HTTPS in front of both the API and the frontend.

### A03 Injection
- All database access goes through SQLAlchemy with bound parameters. No SQL is built from user input.
- The only raw SQL is fixed text: migrations, the advisory lock call, and test-only statements.
- React escapes all rendered values. The app never sets `dangerouslySetInnerHTML`.
- Uploaded filenames are ignored; stored files get a random `uuid4().hex` name, so path traversal through the filename is not possible.

### A04 Insecure Design
- Money is stored as integer paise, never floats.
- Transfers are atomic: both wallets are locked with `SELECT ... FOR UPDATE` in a consistent order, and all writes commit together or not at all.
- Database constraints back up the service rules: non-negative balance, positive amounts, distinct sender and receiver, unique idempotency key per sender, one active KYC submission per user, one wallet per user.
- Payments require verified KYC; unverified users get a clear 403 on every wallet and payment endpoint.
- Idempotency keys prevent double charges on retries.
- The ledger is append-only (database trigger) and tamper-evident (hash chain with an admin verification endpoint).
- QR codes carry an expiry inside the signed payload, and the payer sees the receiver's name from the database before confirming.
- Known design limits: fixed-amount QR codes can be paid more than once until they expire, and the dev top-up endpoint creates money. It is disabled unless `ENABLE_DEV_TOPUP=true`.

### A05 Security Misconfiguration
- CORS allows exactly one origin (`CORS_ORIGIN`), not `*`.
- The settings class fails at startup if any required variable is missing.
- Uploaded images live outside any publicly served folder and are only readable through an admin endpoint.
- Error responses carry specific messages but never stack traces. Exceptions re-raised as HTTP errors use `from None`, so internal details are not chained into responses.
- Out of scope: the interactive API docs at `/docs` are enabled. Production should disable them or put them behind authentication. Security headers (CSP, HSTS) are not configured.

### A06 Vulnerable and Outdated Components
- All Python and npm dependencies are pinned to exact versions in `requirements.txt` and `package.json`, with `package-lock.json` committed.
- `npm install` reported 0 known vulnerabilities at the time of writing.
- Out of scope: automated dependency scanning (for example Dependabot or `pip-audit` in CI).

### A07 Identification and Authentication Failures
- Access tokens expire after 15 minutes.
- Login returns the same message for an unknown email and a wrong password, and runs bcrypt against a placeholder hash for unknown emails so response timing does not reveal which emails are registered.
- Expired, invalid and missing tokens each get a specific 401 message. Tests cover the missing and expired cases.
- Out of scope: rate limiting and account lockout after repeated failed logins, refresh tokens, token revocation, multi-factor authentication, password reset.

### A08 Software and Data Integrity Failures
- The ledger hash chain detects any modified or reordered entry, and a test proves tampering is reported at the exact entry.
- The append-only trigger blocks UPDATE and DELETE at the database level.
- QR payloads are HMAC-signed, so changing the receiver, amount or expiry invalidates the code. A test proves a forged amount is rejected.
- Out of scope: anchoring the latest ledger hash outside the database. Someone with full database access could still rewrite the chain from the edited entry onward.

### A09 Security Logging and Monitoring Failures
- Registrations, KYC submissions, approvals, rejections, top-ups and transfers are logged with ids only.
- Passwords, tokens and full ID numbers are never logged; ID numbers appear masked.
- Out of scope: log shipping, alerting, and an audit trail of failed logins and authorization failures.

### A10 Server-Side Request Forgery
- The backend never fetches URLs supplied by users. QR scanning happens in the browser, and the backend only verifies the decoded text. Not applicable to this design.

## Personal data (PII)

| Data | Where it is stored | How it is protected |
|---|---|---|
| Full name, email, phone | `users` table | Returned only to the user themself and to admins reviewing KYC. |
| Password | Never stored | Only the bcrypt hash is stored. |
| ID card image | `backend/uploads/<random>.jpg/png` | Random filename, folder not publicly served, readable only through an admin-only endpoint, folder git-ignored. |
| ID number | `kyc_submissions.id_number` | Masked to the last 4 characters in every API response (Pydantic serializer) and every log line. Masked inside the stored OCR text. |
| OCR text | `kyc_submissions.ocr_text` | Stored with the ID number masked; shown only to admins. |
| Wallet and transaction history | `wallets`, `transfers`, `ledger_entries` | Each user sees only their own wallet; admins see only the ledger verification result. |

**Retention and deletion.** The prototype keeps all data indefinitely and has no deletion endpoint. Rejected submissions and their images are kept as history. Ledger entries cannot be deleted by design, which conflicts with erasure requests. A production system would need:
- a documented retention period per data type;
- scheduled deletion of ID images once verification is complete and the regulatory retention period has passed;
- account deletion that removes or pseudonymizes personal fields while keeping the financial ledger intact, for example by keeping the wallet id and removing the link to the user's identity.

## What would change for production

1. **Token storage.** Move the JWT from sessionStorage to an `httpOnly`, `Secure`, `SameSite` cookie, so injected JavaScript cannot read it, and add CSRF protection (a synchronizer or double-submit token) because cookies are sent automatically. Add short-lived access tokens with rotating refresh tokens and server-side revocation.
2. **Encrypted document storage.** Store ID images in an object store with server-side encryption and short-lived signed URLs, or encrypt them with a key held in a key management service. Encrypt the `id_number` column at rest, and keep a keyed hash of it for duplicate detection.
3. **Rate limiting.** Limit login, registration, KYC upload, QR creation and payment attempts per IP and per account, and lock or slow down accounts after repeated failed logins.
4. **Orphan file cleanup.** An image is written before the database commit, so a failed commit can leave an orphan file. Add a scheduled job that deletes files with no matching `kyc_submissions` row, or write to a temporary location and move the file only after commit.
5. **Transport and headers.** HTTPS everywhere, HSTS, a strict Content-Security-Policy, and the interactive API docs disabled or protected.
6. **Secrets.** Load secrets from a secrets manager instead of a `.env` file, and rotate the JWT and QR signing keys on a schedule.
7. **Money movement controls.** Remove the dev top-up endpoint entirely, add per-transaction and daily limits, one-time QR invoices, fraud monitoring, and notifications for every debit.
8. **Ledger anchoring.** Periodically sign or publish the latest ledger hash to an external, append-only location so that a full chain rewrite would also be detected.
9. **Monitoring.** Centralized logs, alerts on repeated authorization failures and broken ledger verification, and dependency scanning in CI.
