from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.config import settings
from app.core import logging
# from app.api.v1.router import api_router  # Will import later

logger = logging.logger

def create_application() -> FastAPI:
    application = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        openapi_url="/openapi.json",
        docs_url="/docs",
    )

    # Set up Rate Limiter
    limiter = Limiter(key_func=get_remote_address)
    application.state.limiter = limiter
    application.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # Set up CORS
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Event Handlers
    @application.on_event("startup")
    async def startup_event():
        logger.info("Application starting up...")
        # Initialize resources here (Redis, etc.)

    @application.on_event("shutdown")
    async def shutdown_event():
        logger.info("Application shutting down...")

    # Include Router
    from app.api.v1.router import api_router
    application.include_router(api_router, prefix=settings.API_V1_STR)
    
    @application.get("/")
    async def root():
        return {
            "name": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "docs": "/docs",
            "health": "/health",
            "api": settings.API_V1_STR,
        }

    @application.get("/health")
    async def health_check():
        return {"status": "ok", "version": settings.VERSION}

    @application.get("/favicon.ico", include_in_schema=False)
    async def favicon():
        """Avoid 404 when browsers request favicon.ico."""
        return Response(status_code=204)

    return application

app = create_application()
