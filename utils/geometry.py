"""
Geometry utilities for QGIS FLUX.
"""

from math import gcd
from qgis.core import QgsRectangle

def extent_with_aspect_ratio(extent: QgsRectangle, desired_ratio: float) -> QgsRectangle:
    """
    Crops the current extent to match the desired width/height ratio.
    """
    if desired_ratio <= 0:
        return extent

    w = extent.width()
    h = extent.height()
    if w <= 0 or h <= 0:
        return extent

    current_ratio = w / h
    cx, cy = extent.center().x(), extent.center().y()

    if desired_ratio > current_ratio:
        # Requested aspect is wider than the current view -> crop vertically
        new_width = w
        new_height = min(h, w / desired_ratio)
    else:
        # Requested aspect is taller -> crop horizontally
        new_height = h
        new_width = min(w, h * desired_ratio)

    half_w = new_width / 2
    half_h = new_height / 2
    return QgsRectangle(cx - half_w, cy - half_h, cx + half_w, cy + half_h)


def format_aspect_ratio(width: int, height: int) -> str:
    """
    Returns a simplified aspect ratio string (e.g., '16:9').
    """
    if width <= 0 or height <= 0:
        return "1:1"
    ratio_gcd = gcd(width, height)
    if ratio_gcd == 0:
        return "1:1"
    normalized_w = max(1, width // ratio_gcd)
    normalized_h = max(1, height // ratio_gcd)
    return f"{normalized_w}:{normalized_h}"
