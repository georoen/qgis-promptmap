from __future__ import annotations

import pytest

from flux_stylize_tiles import FluxStylizeTiles


def test_build_vrt_with_fake_gdal(monkeypatch, tmp_path):
    fs = FluxStylizeTiles()
    called = {}

    # Build a fake GDAL module with BuildVRT function
    class FakeGdal:
        @staticmethod
        def BuildVRT(out_vrt, inputs):
            called["args"] = (out_vrt, inputs)
            return True

    # Inject fake into module global
    monkeypatch.setattr("flux_stylize_tiles._gdal", FakeGdal, raising=False)

    output_vrt = tmp_path / " mosaic.vrt "
    inputs = [str(tmp_path / "a.tif"), str(tmp_path / "b.tif")]
    fs.build_vrt(str(output_vrt), inputs)

    assert "args" in called
    out_arg, in_arg = called["args"]
    assert out_arg == str(output_vrt)
    assert in_arg == inputs


def test_build_vrt_without_gdal(monkeypatch, tmp_path):
    fs = FluxStylizeTiles()
    # Simulate missing GDAL
    monkeypatch.setattr("flux_stylize_tiles._gdal", None, raising=False)

    with pytest.raises(RuntimeError) as ei:
        fs.build_vrt(str(tmp_path / "out.vrt"), [str(tmp_path / "a.tif")])

    assert "GDAL (osgeo.gdal) ist nicht verfügbar" in str(ei.value)