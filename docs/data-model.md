# Data Model

All tables are created by Alembic migrations in `backend/alembic/versions/`. Primary keys are UUIDs, except `ledger_entries`, which uses a sequential identity column because the hash chain needs a strict order. All timestamps are timezone-aware. Money is stored as integer paise in `BIGINT` columns.

## Entity relationship diagram

```mermaid
erDiagram
    users ||--o{ kyc_submissions : "submits"
    users ||--o{ kyc_submissions : "reviews"
    users ||--o| wallets : "owns"
    wallets ||--o{ transfers : "sends"
    wallets ||--o{ transfers : "receives"
    wallets ||--o{ ledger_entries : "records"
    transfers ||--o{ ledger_entries : "produces"

    users {
        uuid id PK
        varchar full_name
        varchar email UK
        varchar phone UK
        varchar password_hash
        varchar role "user | admin"
        timestamptz created_at
    }
    kyc_submissions {
        uuid id PK
        uuid user_id FK
        varchar status "PENDING | VERIFIED | REJECTED"
        varchar image_filename
        text ocr_text "ID number masked"
        varchar id_number
        varchar extracted_name
        float name_match_score
        varchar rejection_reason
        uuid reviewed_by_id FK
        timestamptz reviewed_at
        timestamptz created_at
    }
    wallets {
        uuid id PK
        uuid user_id FK, UK
        bigint balance_paise "CHECK >= 0"
        timestamptz created_at
    }
    transfers {
        uuid id PK
        uuid sender_wallet_id FK
        uuid receiver_wallet_id FK
        bigint amount_paise "CHECK > 0"
        varchar idempotency_key
        timestamptz created_at
    }
    ledger_entries {
        bigint id PK
        uuid wallet_id FK
        uuid transfer_id FK "null for top-ups"
        varchar entry_type "TOP_UP | TRANSFER_DEBIT | TRANSFER_CREDIT"
        bigint amount_paise "signed"
        bigint balance_after_paise
        timestamptz created_at
        varchar previous_hash
        varchar entry_hash UK
    }
```

## Tables

### users
| Column | Notes |
|---|---|
| `id` | UUID primary key. |
| `email` | Unique, stored lowercase. |
| `phone` | Unique, 10 to 15 digits with optional leading `+`. |
| `password_hash` | bcrypt hash (60 characters). The plaintext password is never stored. |
| `role` | `user` or `admin`, stored as text with a CHECK constraint so new roles do not need an `ALTER TYPE`. |

### kyc_submissions
One row per attempt, so rejected history is kept.

| Column | Notes |
|---|---|
| `user_id` | Foreign key to `users`, indexed. |
| `status` | `PENDING`, `VERIFIED` or `REJECTED`. |
| `image_filename` | Random name of the file in `backend/uploads/`. |
| `ocr_text` | Tesseract output with the ID number already masked. |
| `id_number` | Full extracted ID number. Masked in every API response and log line. |
| `name_match_score` | 0 to 100 similarity between the registered name and the best matching OCR line. |
| `reviewed_by_id` | Foreign key to the admin in `users`. |

Constraint: partial unique index `uq_kyc_submissions_one_active_per_user` on `user_id` where `status IN ('PENDING', 'VERIFIED')`, so a user has at most one active submission but any number of rejected ones.

### wallets
| Column | Notes |
|---|---|
| `user_id` | Unique foreign key: one wallet per user. The row is created when KYC is approved. |
| `balance_paise` | `CHECK (balance_paise >= 0)`. |

### transfers
| Column | Notes |
|---|---|
| `sender_wallet_id`, `receiver_wallet_id` | Foreign keys to `wallets`, both indexed. `CHECK (sender_wallet_id <> receiver_wallet_id)`. |
| `amount_paise` | `CHECK (amount_paise > 0)`. |
| `idempotency_key` | Unique together with `sender_wallet_id`, so a retried payment cannot be applied twice. |

### ledger_entries
Append-only record of every balance change.

| Column | Notes |
|---|---|
| `id` | `BIGINT` identity. Defines the chain order. |
| `transfer_id` | Foreign key to `transfers`, null for top-ups. Each transfer produces one debit and one credit entry. |
| `amount_paise` | Signed: positive for money in, negative for money out. |
| `balance_after_paise` | Wallet balance immediately after this entry. |
| `previous_hash` | `entry_hash` of the previous entry, or 64 zeros for the first entry. |
| `entry_hash` | `SHA-256(previous_hash + canonical JSON of wallet_id, transfer_id, entry_type, amount_paise, balance_after_paise, created_at)`. Unique. |

Trigger: `ledger_entries_append_only` runs `BEFORE UPDATE OR DELETE ... FOR EACH ROW` and raises an exception, so existing entries cannot be changed or removed through SQL.

## Migrations

| Revision | Creates |
|---|---|
| `0001` | `users` |
| `0002` | `kyc_submissions` and its partial unique index |
| `0003` | `wallets`, `transfers`, `ledger_entries`, the append-only trigger, and wallets for users already verified in Phase 1 |
