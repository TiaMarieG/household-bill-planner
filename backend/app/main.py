from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import bills, earners, household, summary


def create_app() -> FastAPI:
    """Build the FastAPI application with middleware and routes attached."""
    settings = get_settings()
    app = FastAPI(title="Household Bill Planner", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    def health() -> dict[str, str]:
        """Report that the API is running and which environment it is in."""
        return {"status": "ok", "env": settings.app_env}

    app.include_router(bills.router)
    app.include_router(earners.router)
    app.include_router(household.router)
    app.include_router(summary.router)
    return app


app = create_app()
