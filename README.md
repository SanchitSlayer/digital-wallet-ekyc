# Digital Wallet & eKYC Prototype

A proof-of-concept digital wallet with electronic identity verification (eKYC). Users register, upload a photo of an ID card, and an admin reviews the OCR result before approving or rejecting it. All money in this project is fake.

## Prerequisites

- Docker Desktop (runs PostgreSQL)
- Python 3.11 or newer
- Node.js 20 or newer
- Tesseract OCR 5

Installing Tesseract:

| OS | Command |
|---|---|
| macOS | `brew install tesseract` |
| Ubuntu / Debian | `sudo apt install tesseract-ocr` |
| Windows | Download the installer from https://github.com/UB-Mannheim/tesseract/wiki, then add `C:\Program Files\Tesseract-OCR` to your `PATH` |

Check it with `tesseract --version`.

## Environment setup

```bash
cp .env.example .env
```

On Windows PowerShell use `Copy-Item .env.example .env`. Then replace `JWT_SECRET_KEY` in `.env` with the output of `openssl rand -hex 32`.

Start the development and test databases:

```bash
docker compose up -d
```

## Backend

From `backend/`:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

On Windows PowerShell activate the virtual environment with `.venv\Scripts\Activate.ps1` and use `python` instead of `python3`.

The API runs at http://localhost:8000 and its interactive documentation at http://localhost:8000/docs.

## Creating an admin

Admins cannot sign up through the API. From `backend/` with the virtual environment active:

```bash
python -m scripts.create_admin --name "Admin User" --email admin@example.com --phone 9000000000
```

You are asked for the password twice. It is never passed on the command line.

## Frontend

From `frontend/`:

```bash
npm install
npm run dev
```

The app runs at http://localhost:5173.

When the backend API changes, regenerate the TypeScript types while the backend is running:

```bash
npm run generate:api
```

## Tests

The tests use the separate test database on port 5433 and replace the Tesseract call with a fixed result. From `backend/`:

```bash
pytest -v
```
