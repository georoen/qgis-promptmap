import pytest

from flux_stylize_tiles import FluxStylizeTiles, SimpleImage


def test_expected_size():
    fs = FluxStylizeTiles()
    assert fs._expected_size(100) == (100, 100)


def test_needs_resample_for_off_by_one():
    fs = FluxStylizeTiles()
    # 101x99 with N=100 and tol=1 must trigger resample
    assert fs._needs_resample(101, 99, 100, tol=1) is True


def test_resample_stub_png_preserves_alpha_and_size():
    fs = FluxStylizeTiles()
    img = SimpleImage(width=101, height=99, mode="RGBA", fmt="PNG")
    out = fs._resample_qimage_like(img, 100, "PNG")
    # Using the SimpleImage stub ensures deterministic behavior without PIL/Qt
    assert isinstance(out, SimpleImage)
    assert (out.width, out.height) == (100, 100)
    # Alpha should be preserved for PNG
    assert out.mode == "RGBA"
    assert out.fmt.upper() == "PNG"


def test_resample_stub_jpeg_forces_rgb_and_size():
    fs = FluxStylizeTiles()
    # Start with an alpha image
    img = SimpleImage(width=101, height=99, mode="RGBA", fmt="PNG")
    out = fs._resample_qimage_like(img, 100, "JPEG")
    # Using the SimpleImage stub ensures deterministic behavior without PIL/Qt
    assert isinstance(out, SimpleImage)
    assert (out.width, out.height) == (100, 100)
    # JPEG must not have alpha; expect RGB (white-bg is implied for real encoders)
    assert out.mode == "RGB"
    assert out.fmt.upper() == "JPEG"