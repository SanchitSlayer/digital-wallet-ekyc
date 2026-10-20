# Digital Wallet & eKYC Prototype

A proof-of-concept digital wallet with electronic identity verification (eKYC). Users register, verify their identity by uploading an ID card that is read with OCR and reviewed by an admin, and then send fake money to each other by scanning signed QR codes. Every balance change is recorded in an append-only, SHA-256 hash-chained ledger that an admin can verify.

All money in this project is fake. It is a learning and portfolio project, not a production payment system.

## Features

- **Accounts:** registration with name, email, phone and password (bcrypt), JWT login, `user` and `admin` roles, and a command-line script to create admins.
- **eKYC:**
  - JPEG/PNG upload with type and size validation.
  - Grayscale and Otsu-threshold preprocessing, then Tesseract OCR.
  - ID number extraction by regex and fuzzy name matching against the registered name.
  - Admin approve or reject with a reason; resubmission only after rejection.
- **Privacy:** ID numbers are masked to the last 4 characters in every response and log line, and ID images are stored outside any public folder under random names.
- **Wallets:** one per user, opened when KYC is approved. Balances are integer paise. Top-up is dev-only and behind an env flag.
- **Atomic transfers:** both wallet rows are locked with `SELECT ... FOR UPDATE` in a consistent order, and the debit, credit and ledger entries commit together or not at all. Idempotency keys prevent double payments on retry.
- **Hash-chained ledger:** each entry stores `SHA-256(previous hash + entry data)`. A Postgres trigger blocks UPDATE and DELETE, and an admin endpoint reports "chain intact" or the first broken entry.
- **QR payments:** the receiver generates a QR holding the wallet id, an optional amount and an expiry, signed with HMAC-SHA256. The payer scans it with the camera (or uploads an image), confirms the receiver and amount, and pays.

## Tech stack

| Area | Technology |
|---|---|
| Backend | Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2.0, Alembic, PyJWT, bcrypt, pytesseract, Pillow, qrcode |
| Database | PostgreSQL 16 via Docker Compose (separate development and test databases) |
| Frontend | React 19, TypeScript (strict), Vite, React Router, Tailwind CSS, html5-qrcode |
| API types | openapi-typescript, generated from the backend's OpenAPI schema |
| Tests | pytest and httpx against the test database, with the OCR call mocked |

More detail: [docs/architecture.md](docs/architecture.md), [docs/data-model.md](docs/data-model.md), [docs/security-review.md](docs/security-review.md).

## Prerequisites

- Docker Desktop
- Python 3.11 or newer
- Node.js 20 or newer
- Tesseract OCR 5

| OS | Install Tesseract |
|---|---|
| macOS | `brew install tesseract` |
| Ubuntu / Debian | `sudo apt install tesseract-ocr` |
| Windows | Run the installer from https://github.com/UB-Mannheim/tesseract/wiki, then add `C:\Program Files\Tesseract-OCR` to `PATH` |

Check it with `tesseract --version`.

## Setup

From the project root:

```bash
cp .env.example .env
```

On Windows PowerShell use `Copy-Item .env.example .env`. Then generate two different secrets with `openssl rand -hex 32` and put them in `.env` as `JWT_SECRET_KEY` and `QR_SIGNING_KEY`.

Start both databases:

```bash
docker compose up -d
```

`docker compose ps` should show `db` and `db_test` as `healthy`.

## Environment variables

| Variable | Purpose |
|---|---|
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_TEST_DB` | Credentials and database names used by Docker Compose |
| `DATABASE_URL` | SQLAlchemy URL of the development database (port 5432) |
| `TEST_DATABASE_URL` | SQLAlchemy URL of the test database (port 5433) |
| `JWT_SECRET_KEY` | Secret used to sign access tokens |
| `JWT_ALGORITHM` | JWT signing algorithm (`HS256`) |
| `JWT_EXPIRE_MINUTES` | Access token lifetime |
| `CORS_ORIGIN` | The one browser origin allowed to call the API (the frontend URL) |
| `UPLOAD_DIR` | Folder for ID images, relative to `backend/` |
| `MAX_UPLOAD_BYTES` | Maximum ID image size |
| `ENABLE_DEV_TOPUP` | `true` enables the fake-money top-up endpoint; keep `false` outside development |
| `QR_SIGNING_KEY` | Secret used to sign QR payment requests |
| `QR_EXPIRE_MINUTES` | How long a payment QR stays valid |
| `VITE_API_URL` | API base URL used by the frontend |

## Running the backend

From `backend/`:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

On Windows PowerShell, activate with `.venv\Scripts\Activate.ps1` and use `python` instead of `python3`.

The API runs at http://localhost:8000, with interactive docs at http://localhost:8000/docs.

## Running the frontend

From `frontend/`:

```bash
npm install
npm run dev
```

The app runs at http://localhost:5173. Other scripts:

| Script | What it does |
|---|---|
| `npm run build` | Type-checks and builds the production bundle into `dist/` |
| `npm run generate:api` | Regenerates `src/api/schema.ts` from the running backend's `/openapi.json` |

## Creating an admin

Admins cannot sign up through the API. From `backend/` with the virtual environment active:

```bash
python -m scripts.create_admin --name "Admin User" --email admin@example.com --phone 9000000000
```

The password is typed twice at a hidden prompt.

## Running the tests

From `backend/` with the test database running:

```bash
pytest -v
```

The suite runs the real Alembic migrations against the test database, empties every table before each test, and replaces only the Tesseract call with a fixed result. It covers:
- registration and login;
- expired and missing tokens;
- KYC upload, review and resubmission rules;
- admin-only access;
- payments before KYC, successful payments and insufficient balance;
- expired and tampered QR codes;
- idempotent retries and transfer atomicity;
- the append-only trigger, ledger verification and tamper detection.

## Demo walkthrough

1. Start the databases, backend and frontend as above, and create an admin.
2. Open http://localhost:5173 and register a user, using the name printed on the test ID card.
3. Upload an image of a fake ID card that contains lines such as `Name: JANE DOE` and `ID No: AB12345678`. The KYC status page shows PENDING, the masked ID number and the name match score.
4. In a private window, log in as the admin, open **KYC review**, check the image and OCR result, and approve.
5. Back as the user, open **Wallet** and top up some fake money.
6. Register and verify a second user the same way. As that user, open **Receive**, enter an amount and generate a QR code.
7. As the first user, open **Pay**, scan the QR code with the camera or upload a screenshot of it, check the receiver and amount, and pay. Both wallets update and show the transaction.
8. As the admin, open **Ledger** and click **Verify ledger** to see "Chain intact".
