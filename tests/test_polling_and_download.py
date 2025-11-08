from __future__ import annotations

import io
import json
import os
from typing import Any, Dict, List, Optional

import pytest

from flux_stylize_tiles import FluxStylizeTiles, HTTPStatusError
from tests.conftest import FakeResp, FakeSession, FakeTime


def _minimal_png_bytes() -> bytes:
    # A minimal valid PNG: 1x1 transparent pixel
    # Pre-generated static bytes to avoid PIL dependency
    return (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
        b"\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
        b"\x00\x00\x00\x0cIDATx\x9cc``\x00\x00\x00\x02\x00\x01"
        b"\xe2!\xbc3\x00\x00\x00\x00IEND\xaeB`\x82"
    )


def test_polling_ready_path_and_download(tmp_path):
    # Arrange
    fs = FluxStylizeTiles(api_key="sk-test-123", time_module=FakeTime())
    session = FakeSession()
    fs.session = session

    # Create job endpoint returns polling URL
    create_url = "https://fake.api/jobs"
    polling_url = "https://fake.api/jobs/123"
    delivery_url = "https://fake.delivery/file.png"

    def create_responder(headers=None, json: Optional[Dict[str, Any]] = None, timeout: int = 30) -> FakeResp:
        # headers contains Authorization; ensure not used in assertions here
        return FakeResp(200, json_data={"polling_url": polling_url})

    session.script_post(create_url, create_responder)

    # Poll sequence: Processing -> Ready with result.sample
    session.script_get_sequence(
        polling_url,
        [
            FakeResp(200, json_data={"status": "Processing"}),
            FakeResp(200, json_data={"status": "Ready", "result": {"sample": delivery_url}}),
        ],
    )

    # Delivery: single 200
    session.script_get_sequence(delivery_url, [FakeResp(200, content=_minimal_png_bytes())])

    # Act
    out_path = tmp_path / "tile.png"
    result = fs.process_tile(
        row=0,
        col=1,
        extent=(0.0, 0.0, 100.0, 100.0),
        N=100,
        prompt="a prompt",
        out_path=str(out_path),
        seed=42,
        image_format="PNG",
        payload={"polling_endpoint": create_url},
    )

    # Assert
    assert result["status"] == "Ready"
    assert result["delivery_url"] == delivery_url
    assert os.path.exists(out_path)
    # Worldfile must exist
    assert os.path.exists(str(out_path) + ".wld")


def test_polling_failed_path_no_worldfile(tmp_path):
    fs = FluxStylizeTiles(time_module=FakeTime())
    session = FakeSession()
    fs.session = session

    create_url = "https://fake.api/jobs"
    polling_url = "https://fake.api/jobs/777"

    def create_responder(headers=None, json: Optional[Dict[str, Any]] = None, timeout: int = 30) -> FakeResp:
        return FakeResp(200, json_data={"polling_url": polling_url})

    session.script_post(create_url, create_responder)

    # Poll returns Failed immediately
    session.script_get_sequence(polling_url, [FakeResp(200, json_data={"status": "Failed"})])

    out_path = tmp_path / "tile.png"
    result = fs.process_tile(
        row=2,
        col=3,
        extent=(0.0, 0.0, 100.0, 100.0),
        N=100,
        prompt="x",
        out_path=str(out_path),
        payload={"polling_endpoint": create_url},
    )

    assert result["status"] == "Failed"
    # No worldfile should be created
    assert not os.path.exists(str(out_path) + ".wld")


def test_polling_timeout(tmp_path):
    # Tick time by large value per call so loop sees timeout fast
    fs = FluxStylizeTiles(time_module=FakeTime(start=0.0, tick_on_time_call=1000.0))
    session = FakeSession()
    fs.session = session

    create_url = "https://fake.api/jobs"

    def create_responder(headers=None, json: Optional[Dict[str, Any]] = None, timeout: int = 30) -> FakeResp:
        # Provide some polling URL, but it should not be used due to immediate timeout
        return FakeResp(200, json_data={"polling_url": "https://fake.api/jobs/never"})

    session.script_post(create_url, create_responder)

    out_path = tmp_path / "tile.png"
    result = fs.process_tile(
        row=0,
        col=0,
        extent=(0.0, 0.0, 100.0, 100.0),
        N=100,
        prompt="timeout",
        out_path=str(out_path),
        payload={"polling_endpoint": create_url},
    )

    assert result["status"] == "Timeout"
    assert not os.path.exists(str(out_path))
    assert not os.path.exists(str(out_path) + ".wld")


def test_polling_429_backoff_sequence_and_then_ready(tmp_path):
    time = FakeTime(start=0.0, tick_on_time_call=0.0)
    fs = FluxStylizeTiles(time_module=time)
    session = FakeSession()
    fs.session = session

    create_url = "https://fake.api/jobs"
    polling_url = "https://fake.api/jobs/backoff"
    delivery_url = "https://fake.delivery/file.png"

    def create_responder(headers=None, json: Optional[Dict[str, Any]] = None, timeout: int = 30) -> FakeResp:
        return FakeResp(200, json_data={"polling_url": polling_url})

    session.script_post(create_url, create_responder)

    # 429 -> 429 -> 200 Ready
    session.script_get_sequence(
        polling_url,
        [
            FakeResp(429),
            FakeResp(429),
            FakeResp(200, json_data={"status": "Ready", "result": {"sample": delivery_url}}),
        ],
    )
    session.script_get_sequence(delivery_url, [FakeResp(200, content=_minimal_png_bytes())])

    out_path = tmp_path / "tile.png"
    result = fs.process_tile(
        row=5,
        col=7,
        extent=(0.0, 0.0, 100.0, 100.0),
        N=100,
        prompt="x",
        out_path=str(out_path),
        payload={"polling_endpoint": create_url},
    )

    assert result["status"] == "Ready"
    # Validate backoff delays logged as 1, 2 (third would be 4 if needed)
    delays = [rec["delay"] for rec in fs.logs if rec.get("event") == "poll_backoff"]
    assert delays[:2] == [1, 2]
    # Ensure max cap would be 16 if continued (not directly asserted here)


@pytest.mark.parametrize("first_code", [403, 404])
def test_download_retry_on_403_404_then_200(tmp_path, first_code: int):
    fs = FluxStylizeTiles(time_module=FakeTime())
    session = FakeSession()
    fs.session = session

    create_url = "https://fake.api/jobs"
    polling_url = "https://fake.api/jobs/ok"
    delivery_url = "https://fake.delivery/file.png"

    session.script_post(create_url, lambda headers=None, json=None, timeout=30: FakeResp(200, json_data={"polling_url": polling_url}))
    session.script_get_sequence(polling_url, [FakeResp(200, json_data={"status": "Ready", "result": {"sample": delivery_url}})])
    # First 403/404, then success 200
    session.script_get_sequence(delivery_url, [FakeResp(first_code), FakeResp(200, content=_minimal_png_bytes())])

    out_path = tmp_path / "tile.png"
    result = fs.process_tile(
        row=1,
        col=1,
        extent=(0.0, 0.0, 1.0, 1.0),
        N=100,
        prompt="y",
        out_path=str(out_path),
        payload={"polling_endpoint": create_url},
    )
    assert result["status"] == "Ready"
    assert os.path.exists(out_path)


def test_logging_privacy_and_required_fields(tmp_path):
    api_key = "sk-secret-key-1234567890"
    fs = FluxStylizeTiles(api_key=api_key, time_module=FakeTime())
    session = FakeSession()
    fs.session = session

    create_url = "https://fake.api/jobs"
    polling_url = "https://fake.api/jobs/fields"
    delivery_url = "https://fake.delivery/file.png"

    session.script_post(create_url, lambda headers=None, json=None, timeout=30: FakeResp(200, json_data={"polling_url": polling_url}))
    session.script_get_sequence(
        polling_url,
        [
            FakeResp(200, json_data={"status": "Processing"}),
            FakeResp(200, json_data={"status": "Ready", "result": {"sample": delivery_url}}),
        ],
    )
    session.script_get_sequence(delivery_url, [FakeResp(200, content=_minimal_png_bytes())])

    out_path = tmp_path / "tile.png"
    result = fs.process_tile(
        row=9,
        col=8,
        extent=(0.0, 0.0, 100.0, 100.0),
        N=100,
        prompt="privacy check",
        out_path=str(out_path),
        seed=11,
        payload={"polling_endpoint": create_url},
    )

    assert result["status"] == "Ready"

    # Privacy: API key must not appear in serialized logs
    serialized = json.dumps(fs.logs)
    assert api_key not in serialized
    assert "Bearer ***" in serialized or "***" in serialized

    # Required fields presence in at least one relevant record
    # Look for tile_start and tile_done records
    start = next(rec for rec in fs.logs if rec.get("event") == "tile_start")
    done = next(rec for rec in fs.logs if rec.get("event") == "tile_done")

    for rec in (start, done):
        assert "timestamp" in rec
        assert rec.get("N") == 100
        assert rec.get("extent") == (0.0, 0.0, 100.0, 100.0)
        assert "xres" in rec and "yres" in rec
        assert "prompt_hash" in rec
        # seed is optional but should be present here
        assert rec.get("seed") in (11, None)

    # delivery_url and path should be present in 'done'
    assert "delivery_url" in done
    assert "path" in done

def test_backoff_sequence_default():
    from flux_stylize_tiles import FluxStylizeTiles

    fs = FluxStylizeTiles()
    assert fs._backoff_delays() == [1, 2, 4, 8, 16]