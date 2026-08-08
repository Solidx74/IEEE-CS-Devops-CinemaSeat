import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.booking.router import router as booking_router
from app.catalog.router import router as catalog_router
from app.config import get_settings
from app.db import SessionLocal
from app.payment.router import router as payment_router
from app.payment.service import payment_recovery_loop


settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    recovery_task = asyncio.create_task(
        payment_recovery_loop(session_factory=SessionLocal, settings=settings),
        name="payment-recovery-loop",
    )
    try:
        yield
    finally:
        recovery_task.cancel()
        with suppress(asyncio.CancelledError):
            await recovery_task


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["operations"])
async def health() -> dict[str, str]:
    # Intentionally local-only: gateway (or even Redis/DB) outages must not
    # make the API process unhealthy or trigger a restart storm.
    return {"status": "ok", "service": "cinemaseat-api"}


app.include_router(catalog_router, prefix="/api/v1")
app.include_router(booking_router, prefix="/api/v1")
app.include_router(payment_router, prefix="/api/v1")
