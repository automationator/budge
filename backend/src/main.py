import re
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from src.accounts.router import router as accounts_router
from src.admin.router import router as admin_router
from src.allocation_rules.router import router as allocation_rules_router
from src.allocations.router import router as allocations_router
from src.auth.router import router as auth_router
from src.budgets.router import router as budgets_router
from src.config import settings
from src.data_transfer.router import router as data_transfer_router
from src.database import e2e_schema_context
from src.envelope_groups.router import router as envelope_groups_router
from src.envelopes.router import router as envelopes_router
from src.locations.router import router as locations_router
from src.logging import get_logger, setup_logging
from src.notifications.router import router as notifications_router
from src.payees.router import router as payees_router
from src.public.router import router as public_router
from src.recurring_transactions.router import router as recurring_transactions_router
from src.reports.router import router as reports_router
from src.start_fresh.router import router as start_fresh_router
from src.transactions.router import router as transactions_router
from src.users.router import router as users_router

setup_logging()
logger = get_logger(__name__)


class E2ESchemaMiddleware(BaseHTTPMiddleware):
    """Middleware to set search_path for E2E tests based on X-E2E-Schema header."""

    async def dispatch(self, request: Request, call_next):
        schema = request.headers.get("X-E2E-Schema")
        token = None

        if schema and settings.env == "e2e":
            # Validate schema name format (e2e_w0, e2e_w1, etc.)
            if re.match(r"^e2e_w\d+$", schema):
                token = e2e_schema_context.set(schema)
                logger.debug("E2E schema set to: %s", schema)
            else:
                logger.warning("Invalid E2E schema format: %s", schema)

        try:
            response = await call_next(request)
            return response
        finally:
            if token:
                e2e_schema_context.reset(token)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    logger.info("Starting %s", settings.app_name)
    yield
    logger.info("Shutting down %s", settings.app_name)


app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins + settings.extra_cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)

# Add E2E schema middleware (only has effect when ENV=e2e)
if settings.env == "e2e":
    app.add_middleware(E2ESchemaMiddleware)

app.include_router(accounts_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")
app.include_router(allocation_rules_router, prefix="/api/v1")
app.include_router(allocations_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(data_transfer_router, prefix="/api/v1")
app.include_router(envelope_groups_router, prefix="/api/v1")
app.include_router(envelopes_router, prefix="/api/v1")
app.include_router(locations_router, prefix="/api/v1")
app.include_router(notifications_router, prefix="/api/v1")
app.include_router(payees_router, prefix="/api/v1")
app.include_router(public_router, prefix="/api/v1")
app.include_router(recurring_transactions_router, prefix="/api/v1")
app.include_router(reports_router, prefix="/api/v1")
app.include_router(start_fresh_router, prefix="/api/v1")
app.include_router(budgets_router, prefix="/api/v1")
app.include_router(transactions_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")


# Mount test router only in e2e environment
if settings.env == "e2e":
    from src.testing.router import router as testing_router

    app.include_router(testing_router, prefix="/test")


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "healthy"}
