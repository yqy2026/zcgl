"""Certificate files have one scoped public archive entry point."""

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/property-certificates/cert/attachments"),
        ("post", "/property-certificates/cert/attachments"),
        ("put", "/property-certificates/cert/attachments/file"),
        ("delete", "/property-certificates/cert/attachments/file"),
        ("get", "/property-certificates/cert/attachments/file/preview"),
        ("get", "/property-certificates/cert/attachments/file/download"),
    ],
)
def test_retired_attachment_routes_are_not_public(
    client: TestClient, method: str, path: str
) -> None:
    assert not any(
        getattr(route, "path_regex", None) is not None
        and route.path_regex.fullmatch(f"/api/v1{path}") is not None
        for route in client.app.routes
    )
    response = client.request(method, f"/api/v1{path}")
    assert response.status_code == 404
