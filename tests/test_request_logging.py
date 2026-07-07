import json
import logging

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.middleware import RequestIDMiddleware, logger


def test_request_json_is_logged_at_debug_level(caplog):
    app = FastAPI()
    app.add_middleware(RequestIDMiddleware)

    @app.post("/test")
    async def test_endpoint(payload: dict) -> dict:
        return payload

    client = TestClient(app)
    logger.setLevel(logging.DEBUG)
    caplog.set_level(logging.DEBUG, logger="app.core.middleware")

    payload = {"city": "Pune", "property_type": "flat"}
    response = client.post("/test", json=payload)

    assert response.status_code == 200
    assert response.json() == payload
    assert any(
        record.message == "request_received"
        and record.levelname == "DEBUG"
        and record.__dict__.get("request_json") == payload
        for record in caplog.records
    )
