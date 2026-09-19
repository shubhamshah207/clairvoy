"""
Integration Tests for FastAPI Web Application Endpoints
"""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from clairvoy.core.run_manager import RunManager
from clairvoy.web.app import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def isolate_runs_history(tmp_path, monkeypatch):
    test_runs_file = tmp_path / "test_runs.json"
    orig_init = RunManager.__init__

    def mock_init(self, history_file=None):
        orig_init(self, history_file=history_file or test_runs_file)

    monkeypatch.setattr(RunManager, "__init__", mock_init)
    monkeypatch.setattr(RunManager, "auto_discover_reports", lambda self, search_dirs=None: [])


def test_index_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Clairvoy" in response.text
    assert "runsDropdown" in response.text
    assert "defaultHeader" in response.text
    assert "selectionHeader" in response.text
    assert "photoLightboxModal" in response.text
    assert "gp-check-circle" in response.text
    # Floating bottom dock must NOT exist
    assert "contextualActionBar" not in response.text
    # Left-bottom storage widget and thumbnail size controls
    assert "sideWastedGb" in response.text
    assert "sizeBtn_small" in response.text
    assert "sizeBtn_medium" in response.text
    assert "sizeBtn_large" in response.text
    # Left sidebar category navigation and clear filter cross
    assert "catBtn_PHOTO" in response.text
    assert "catBtn_VIDEO" in response.text
    assert "clearCategoryFilterChip" in response.text
    assert "sidebarClearAllBtn" in response.text


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


def test_media_valid_image(client, sample_images):
    red_img = str(sample_images["red1"])
    response = client.get("/api/media", params={"path": red_img})
    assert response.status_code == 200
    assert "image" in response.headers["content-type"]


def test_media_security_invalid_extension(client, temp_workspace):
    txt_file = temp_workspace / "dummy.txt"
    txt_file.write_text("not media")
    response = client.get("/api/media", params={"path": str(txt_file)})
    assert response.status_code == 403


def test_thumbnail_and_media_video(client, temp_workspace):
    import shutil
    import subprocess

    ffmpeg_bin = shutil.which("ffmpeg") or "/home/shubhamshah207/.local/bin/ffmpeg"
    if not shutil.which("ffmpeg") and not Path(ffmpeg_bin).is_file():
        pytest.skip("ffmpeg not found on system")

    vid_path = temp_workspace / "sample_test.mp4"
    cmd = [
        ffmpeg_bin, "-y", "-f", "lavfi",
        "-i", "testsrc=duration=1:size=64x64:rate=10",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        str(vid_path),
    ]
    res = subprocess.run(cmd, capture_output=True)
    if res.returncode != 0:
        pytest.skip("Failed to generate test video")

    # Test /api/thumbnail on video
    resp_thumb = client.get("/api/thumbnail", params={"path": str(vid_path)})
    assert resp_thumb.status_code == 200
    assert resp_thumb.headers["content-type"] == "image/jpeg"
    assert len(resp_thumb.content) > 0

    # Test /api/media on video
    resp_media = client.get("/api/media", params={"path": str(vid_path)})
    assert resp_media.status_code == 200
    assert resp_media.headers["content-type"] == "video/mp4"
    assert len(resp_media.content) > 0


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


def test_override_keeper_endpoint(client, tmp_path):
    import json

    from clairvoy.core.run_manager import RunManager

    summary_file = tmp_path / "clairvoy_summary.json"
    data = {
        "scanned_paths": [str(tmp_path)],
        "total_files_scanned": 2,
        "total_duplicate_groups": 1,
        "wasted_bytes": 1024,
        "wasted_mb": 0.001,
        "wasted_gb": 0.0,
        "summary_json": str(summary_file),
        "groups": [
            {
                "group_id": 1,
                "match_type": "EXACT_HASH",
                "action": "KEEP",
                "similarity": "100%",
                "similarity_score": 1.0,
                "size_mb": 0.001,
                "path": str(tmp_path / "file_a.txt"),
                "category": "FILE",
            },
            {
                "group_id": 1,
                "match_type": "EXACT_HASH",
                "action": "DUPLICATE",
                "similarity": "100%",
                "similarity_score": 1.0,
                "size_mb": 0.001,
                "path": str(tmp_path / "file_b.txt"),
                "category": "FILE",
            },
        ],
    }
    summary_file.write_text(json.dumps(data), encoding="utf-8")

    manager = RunManager()
    rec = manager.register_run(data)

    # Load into active state
    load_res = client.post("/api/runs/load", json={"run_id": rec.run_id})
    assert load_res.status_code == 200

    # Override keeper to file_b.txt
    override_res = client.post(
        "/api/clusters/override-keeper",
        json={"group_id": 1, "new_keeper_path": str(tmp_path / "file_b.txt")},
    )
    assert override_res.status_code == 200
    res_data = override_res.json()
    assert res_data["status"] == "updated"

    # Check that file_b.txt is now KEEP and file_a.txt is DUPLICATE
    status_res = client.get("/api/status")
    groups = status_res.json()["summary"]["groups"]
    file_a = next(g for g in groups if g["path"] == str(tmp_path / "file_a.txt"))
    file_b = next(g for g in groups if g["path"] == str(tmp_path / "file_b.txt"))
    assert file_b["action"] == "KEEP"
    assert file_a["action"] == "DUPLICATE"


def test_download_reports_endpoints(client, tmp_path):
    # With active summary loaded from previous test or newly loaded
    csv_res = client.get("/api/reports/csv")
    assert csv_res.status_code == 200
    assert "group_id" in csv_res.text
    assert "file_a.txt" in csv_res.text or "file_b.txt" in csv_res.text

    sh_res = client.get("/api/reports/script")
    assert sh_res.status_code == 200
    assert "#!/usr/bin/env bash" in sh_res.text
    assert "mv -n --" in sh_res.text


def test_delete_endpoints(client, tmp_path):
    # Setup test duplicate files
    keeper = tmp_path / "keep_img.jpg"
    keeper.write_text("keeper content")
    dupe = tmp_path / "dupe_img.jpg"
    dupe.write_text("dupe content")

    summary_file = tmp_path / "clairvoy_summary.json"
    data = {
        "scanned_paths": [str(tmp_path)],
        "scanned_dir": str(tmp_path),
        "total_files_scanned": 2,
        "total_duplicate_groups": 1,
        "wasted_bytes": len(dupe.read_bytes()),
        "wasted_mb": 0.001,
        "wasted_gb": 0.0,
        "summary_json": str(summary_file),
        "groups": [
            {
                "group_id": 1,
                "match_type": "EXACT_HASH",
                "action": "KEEP",
                "similarity": "100%",
                "similarity_score": 1.0,
                "size_mb": 0.001,
                "path": str(keeper),
                "category": "FILE",
            },
            {
                "group_id": 1,
                "match_type": "EXACT_HASH",
                "action": "DUPLICATE",
                "similarity": "100%",
                "similarity_score": 1.0,
                "size_mb": 0.001,
                "path": str(dupe),
                "category": "FILE",
            },
        ],
    }
    summary_file.write_text(json.dumps(data), encoding="utf-8")

    manager = RunManager()
    rec = manager.register_run(data)
    load_res = client.post("/api/runs/load", json={"run_id": rec.run_id})
    assert load_res.status_code == 200

    # 1. Test GET /api/reports/delete-script
    script_res = client.get("/api/reports/delete-script?mode=permanent")
    assert script_res.status_code == 200
    assert "rm -f --" in script_res.text

    # 2. Test POST /api/delete/execute (trash mode)
    del_res = client.post(
        "/api/delete/execute",
        json={"paths": [str(dupe)], "mode": "trash", "base_dir": str(tmp_path)},
    )
    assert del_res.status_code == 200
    del_data = del_res.json()
    assert del_data["total_files_deleted"] == 1
    assert not dupe.exists()
    assert keeper.exists()

    # 3. Test POST /api/delete/restore
    manifest_path = del_data["audit_file"]
    restore_res = client.post("/api/delete/restore", json={"manifest_file": manifest_path})
    assert restore_res.status_code == 200
    assert restore_res.json()["restored_files_count"] == 1
    assert dupe.exists()


