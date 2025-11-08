from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

import pytest

from flux_stylize_tiles import FluxStylizeTiles
from tests.conftest import FakeResp, FakeSession, FakeTime


def _minimal_png_bytes() -> bytes:
    # Minimal valid PNG (1x1) to avoid PIL dependency
    return (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
        b"\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
        b"\x00\x00\x00\x0cIDATx\x9cc``\x00\x00\x00\x02\x00\x01"
        b"\xe2!\xbc3\x00\x00\x00\x00IEND\xaeB`\x82"
    )


def _happy_path(session: FakeSession, create_url: str, polling_url: str, delivery_url: str) -> None:
    session.script_post(create_url, lambda headers=None, json=None, timeout=30: FakeResp(200, json_data={"polling_url": polling_url}))
    session.script_get_sequence(
        polling_url,
        [
            FakeResp(200, json_data={"status": "Processing"}),
            FakeResp(200, json_data={"status": "Ready", "result": {"sample": delivery_url}}),
        ],
    )
    session.script_get_sequence(delivery_url, [FakeResp(200, content=_minimal_png_bytes())])


def test_logging_privacy_in_memory_and_required_fields(tmp_path):
    api_key = "sk-secret-key-1234567890"
    fs = FluxStylizeTiles(api_key=api_key, time_module=FakeTime())
    session = FakeSession()
    fs.session = session

    create_url = "https://fake.api/jobs"
    polling_url = "https://fake.api/jobs/fields"
    delivery_url = "https://fake.delivery/file.png"
    _happy_path(session, create_url, polling_url, delivery_url)

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
    # Authorization header should be redacted
    assert "Bearer ***" in serialized or "***" in serialized

    # Required fields presence
    start = next(rec for rec in fs.logs if rec.get("event") == "tile_start")
    done = next(rec for rec in fs.logs if rec.get("event") == "tile_done")

    for rec in (start, done):
        assert "timestamp" in rec
        assert rec.get("N") == 100
        assert rec.get("extent") == (0.0, 0.0, 100.0, 100.0)
        assert "xres" in rec and "yres" in rec
        assert "prompt_hash" in rec
        # seed is optional but present here
        assert rec.get("seed") in (11, None)

    assert "delivery_url" in done
    assert "path" in done


def test_logging_privacy_on_disk(tmp_path):
    api_key = "sk-secret-key-9876543210"
    log_file = tmp_path / "flux_logs.jsonl"
    fs = FluxStylizeTiles(api_key=api_key, log_path=str(log_file), time_module=FakeTime())
    session = FakeSession()
    fs.session = session

    create_url = "https://fake.api/jobs"
    polling_url = "https://fake.api/jobs/logfile"
    delivery_url = "https://fake.delivery/file.png"
    _happy_path(session, create_url, polling_url, delivery_url)

    out_path = tmp_path / "tile.png"
    result = fs.process_tile(
        row=1,
        col=2,
        extent=(0.0, 0.0, 100.0, 100.0),
        N=100,
        prompt="write to file",
        out_path=str(out_path),
        payload={"polling_endpoint": create_url},
    )
    assert result["status"] == "Ready"

    # Read JSONL and ensure no API key leak
    assert os.path.exists(log_file)
    with open(log_file, "r", encoding="utf-8") as f:
        content = f.read()

    assert api_key not in content
    # Expect redacted Authorization somewhere
    assert "Bearer ***" in content or "***" in content