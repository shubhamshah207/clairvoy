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
    assert "runsDropdown" in response.text


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


def test_scan_multiple_directories(client, multi_root_dataset):
    root_a = str(multi_root_dataset["root_a"])
    root_b = str(multi_root_dataset["root_b"])

    response = client.post("/api/scan", json={"paths": [root_a, root_b]})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "started"
    assert data["count"] == 2


def test_runs_list_and_load_endpoints(client, tmp_path):
    import json

    from clairvoy.core.run_manager import RunManager

    summary_file = tmp_path / "clairvoy_summary.json"
    data = {
        "scanned_paths": [str(tmp_path)],
        "scanned_dir": str(tmp_path),
        "total_files_scanned": 40,
        "media_files_scanned": 20,
        "exact_duplicate_groups": 4,
        "visual_ai_groups": 1,
        "content_duplicate_groups": 0,
        "total_duplicate_groups": 5,
        "wasted_bytes": 1048576,
        "wasted_mb": 1.0,
        "wasted_gb": 0.001,
        "duration_seconds": 1.5,
        "summary_json": str(summary_file),
        "groups": [],
    }
    summary_file.write_text(json.dumps(data), encoding="utf-8")

    manager = RunManager()
    rec = manager.register_run(data)

    # 1. GET /api/runs
    res = client.get("/api/runs")
    assert res.status_code == 200
    runs = res.json()
    assert isinstance(runs, list)
    assert any(r["run_id"] == rec.run_id for r in runs)

    # 2. POST /api/runs/load
    load_res = client.post("/api/runs/load", json={"run_id": rec.run_id})
    assert load_res.status_code == 200
    loaded_data = load_res.json()
    assert loaded_data["status"] == "loaded"
    assert loaded_data["summary"]["total_files_scanned"] == 40

    # 3. GET /api/status should now reflect completed with loaded summary
    status_res = client.get("/api/status")
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert status_data["status"] == "completed"
    assert status_data["summary"]["total_duplicate_groups"] == 5
