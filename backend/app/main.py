import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth.router import router as auth_router
from app.core.config import settings
from app.kyc.router import admin_router as kyc_admin_router
from app.kyc.router import router as kyc_router
from app.ledger.router import admin_router as ledger_admin_router
from app.payments.router import router as payments_router
from app.wallet.router import router as wallet_router

logging.basicConfig(level=logging.INFO, format="%(levelname)s [%(name)s] %(message)s")

app = FastAPI(title="Digital Wallet eKYC API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.cors_origin],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(kyc_router)
app.include_router(kyc_admin_router)
app.include_router(wallet_router)
app.include_router(payments_router)
app.include_router(ledger_admin_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
