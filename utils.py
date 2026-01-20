"""
Essential utilities for QGIS FLUX.
Contains only critical geometry and georeferencing logic.
"""

import os
from math import gcd
from typing import Tuple
from qgis.core import QgsRectangle

def extent_with_aspect_ratio(extent: QgsRectangle, desired_ratio: float) -> QgsRectangle:
    """
    Crops the current extent to match the desired width/height ratio.
    Essential for ensuring the map sent to the AI matches the requested aspect ratio.
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
    Required by Flux/Gemini APIs.
    """
    if width <= 0 or height <= 0:
        return "1:1"
    ratio_gcd = gcd(width, height)
    if ratio_gcd == 0:
        return "1:1"
    normalized_w = max(1, width // ratio_gcd)
    normalized_h = max(1, height // ratio_gcd)
    return f"{normalized_w}:{normalized_h}"


def write_worldfile(image_path: str, extent: Tuple[float, float, float, float], width: int, height: int):
    """
    Writes a georeferencing world file (.pgw) for the given image.
    Essential for QGIS to know where to place the returned image.
    """
    xmin, ymin, xmax, ymax = extent
    
    # Calculate pixel size
    # Note: Y pixel size is negative because images start from top-left
    x_pixel_size = (xmax - xmin) / width
    y_pixel_size = -((ymax - ymin) / height)
    
    # Calculate center of top-left pixel
    top_left_x = xmin + x_pixel_size / 2
    top_left_y = ymax + y_pixel_size / 2
    
    # Determine extension (.pgw for PNG)
    worldfile_path = os.path.splitext(image_path)[0] + ".pgw"
    
    with open(worldfile_path, 'w') as wf:
        # Format:
        # X pixel size
        # Rotation (0)
        # Rotation (0)
        # Y pixel size
        # X coordinate of upper-left pixel center
        # Y coordinate of upper-left pixel center
        wf.write(f"{x_pixel_size}\n0.0\n0.0\n{y_pixel_size}\n{top_left_x}\n{top_left_y}\n")
