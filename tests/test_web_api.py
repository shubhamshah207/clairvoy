"""
Integration Tests for FastAPI Web Application Endpoints
"""

import pytest
from fastapi.testclient import TestClient

from clairvoy.web.app import app


@pytest.fixture
def client():
    return TestClient(app)


def test_index_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Clairvoy" in response.text


def test_status_endpoint(client):
    response = client.get("/api/status")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data


def test_thumbnail_security_traversal(client):
    # Try reading /etc/passwd or a restricted system file
    response = client.get("/api/thumbnail", params={"path": "/etc/passwd"})
    assert response.status_code in [403, 404]


def test_thumbnail_security_invalid_extension(client, temp_workspace):
    txt_file = temp_workspace / "dummy.txt"
    txt_file.write_text("not an image")
    response = client.get("/api/thumbnail", params={"path": str(txt_file)})
    assert response.status_code == 403


def test_thumbnail_valid_image(client, sample_images):
    red_img = str(sample_images["red1"])
    response = client.get("/api/thumbnail", params={"path": red_img})
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"


def test_scan_invalid_directory(client):
    response = client.post("/api/scan", json={"directory": "/non/existent/path/here"})
    assert response.status_code == 400
