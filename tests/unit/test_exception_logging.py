"""Regression guard: unhandled exceptions must be logged, not swallowed.

core/exceptions.py's catch-all handler used to return a clean 500 response
with zero server-side trace of what happened -- invisible once the app runs
on a remote box where `docker logs` is the only window in.
"""

import logging

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.exceptions import register_exception_handlers


def _build_app_with_broken_route() -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/boom")
    async def boom() -> None:
        raise RuntimeError("unexpected failure for logging test")

    return app


def test_unhandled_exception_is_logged_with_traceback(caplog) -> None:
    app = _build_app_with_broken_route()
    client = TestClient(app, raise_server_exceptions=False)

    with caplog.at_level(logging.ERROR, logger="atelier_lens.exceptions"):
        response = client.get("/boom")

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "INTERNAL_ERROR"

    records = [r for r in caplog.records if r.name == "atelier_lens.exceptions"]
    assert len(records) == 1
    assert "RuntimeError" in caplog.text
    assert "unexpected failure for logging test" in caplog.text
    assert records[0].exc_info is not None  # traceback attached, not just a message
