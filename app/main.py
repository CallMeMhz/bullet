"""Bullet - FastAPI application for webhook relay."""

import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

import uvicorn
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.router import AlertRouter, load_routes_config
from app.sources.grafana import GrafanaSource
from app.sources.base import BaseSource

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Global router instance
router: AlertRouter | None = None

# Source parsers registry
sources: dict[str, BaseSource] = {}


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler for startup/shutdown."""
    global router

    settings = get_settings()

    # Configure logging level
    logging.getLogger().setLevel(settings.log_level.upper())

    # Register source parsers
    sources["grafana"] = GrafanaSource()
    logger.info(f"Registered {len(sources)} source parser(s): {list(sources.keys())}")

    # Load routes configuration
    try:
        routes_config = load_routes_config(settings.routes_config_path)
        router = AlertRouter(routes_config)
        logger.info(
            f"Loaded {len(routes_config.routes)} route(s) from {settings.routes_config}"
        )
    except FileNotFoundError:
        logger.error(
            f"Routes config not found: {settings.routes_config}. "
            "Create a routes.yaml file or set ROUTES_CONFIG environment variable."
        )
        router = None
    except Exception as e:
        logger.exception(f"Failed to load routes config: {e}")
        router = None

    logger.info("Bullet started")

    yield

    # Cleanup on shutdown
    router = None
    sources.clear()
    logger.info("Bullet stopped")


app = FastAPI(
    title="Bullet",
    description="Webhook relay service for alerts with source-based and label-based routing",
    version="0.3.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/sources")
async def list_sources() -> dict[str, list[str]]:
    """List registered alert sources."""
    return {"sources": list(sources.keys())}


@app.get("/routes")
async def list_routes() -> dict[str, list[dict]]:
    """List configured routing rules."""
    if not router:
        return {"routes": []}

    return {
        "routes": [
            {
                "name": route.name,
                "match": route.match.model_dump(),
                "channels": [ch.model_dump() for ch in route.channels],
            }
            for route in router.routes
        ]
    }


async def _process_webhook(source_name: str, payload: dict[str, Any]) -> JSONResponse:
    """Process webhook from a specific source."""
    logger.info(f"Received webhook from source: {source_name}")

    if not router:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Router not configured. Check routes.yaml file.",
        )

    source = sources.get(source_name)
    if not source:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown source: {source_name}",
        )

    # Parse payload to unified format
    try:
        alert_group = source.parse(payload)
    except Exception as e:
        logger.exception(f"Failed to parse {source_name} payload: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid payload: {e}",
        )

    logger.info(
        f"Parsed {source_name} webhook: status={alert_group.status}, "
        f"alerts={len(alert_group.alerts)}"
    )

    # Route the alert (internally wrapped into a generic Event)
    results = await router.route_alert(alert_group)

    # No matching route - discard
    if not results:
        logger.info("No matching route, alert discarded")
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "discarded",
                "message": "No matching route found",
                "source": source_name,
                "results": {},
            },
        )

    # Check if at least one channel succeeded
    any_success = any(results.values())

    if not any_success:
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={
                "status": "error",
                "message": "Failed to send to all matched channels",
                "source": source_name,
                "results": results,
            },
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": "ok",
            "message": "Alert routed successfully",
            "source": source_name,
            "results": results,
        },
    )


@app.post("/webhook/grafana")
async def grafana_webhook(request: Request) -> JSONResponse:
    """Receive Grafana alert webhook."""
    payload = await request.json()
    return await _process_webhook("grafana", payload)


@app.post("/webhook/{source_name}")
async def generic_webhook(source_name: str, request: Request) -> JSONResponse:
    """Receive webhook from any registered source."""
    payload = await request.json()
    return await _process_webhook(source_name, payload)


def run() -> None:
    """Run the application using uvicorn."""
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
        reload=False,
    )


if __name__ == "__main__":
    run()

