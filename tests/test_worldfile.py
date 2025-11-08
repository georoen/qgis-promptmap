import pytest

from flux_stylize_tiles import FluxStylizeTiles


def test_worldfile_compute_square_extent():
    # Arrange
    fs = FluxStylizeTiles()
    extent = (0.0, 0.0, 100.0, 100.0)
    N = 100

    # Act
    A, D, B, E, C, F = fs._compute_worldfile_params(extent, N)

    # Assert
    assert pytest.approx(A, rel=0, abs=1e-9) == 1.0
    assert pytest.approx(E, rel=0, abs=1e-9) == -1.0
    assert pytest.approx(C, rel=0, abs=1e-9) == 0.5
    assert pytest.approx(F, rel=0, abs=1e-9) == 99.5
    assert pytest.approx(D, rel=0, abs=1e-9) == 0.0
    assert pytest.approx(B, rel=0, abs=1e-9) == 0.0