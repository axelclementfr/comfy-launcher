"""FastAPI agent app with Bearer auth middleware."""
from __future__ import annotations
import os
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


class BearerAuthMiddleware(BaseHTTPMiddleware):
    """Reject any request without `Authorization: Bearer <LAUNCHER_AGENT_TOKEN>`."""

    async def dispatch(self, request: Request, call_next):
        expected = os.environ.get("LAUNCHER_AGENT_TOKEN", "").strip()
        if not expected:
            return JSONResponse(
                {"error": "agent not configured: LAUNCHER_AGENT_TOKEN missing"},
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        header = request.headers.get("authorization", "")
        if not header.startswith("Bearer "):
            return JSONResponse(
                {"error": "missing or invalid Authorization header"},
                status_code=status.HTTP_401_UNAUTHORIZED,
            )
        provided = header.removeprefix("Bearer ").strip()
        if provided != expected:
            return JSONResponse(
                {"error": "invalid token"},
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        return await call_next(request)


def build_app() -> FastAPI:
    from launcher.agent.routes_install import router as install_router
    app = FastAPI(title="comfy-launcher agent", version="0.1.0")
    app.add_middleware(BearerAuthMiddleware)
    app.include_router(install_router)

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app


# For uvicorn: launcher.agent.app:app
app = build_app()
