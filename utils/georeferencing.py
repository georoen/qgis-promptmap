"""
Georeferencing utilities for QGIS FLUX.
"""

import os
from typing import Tuple

def write_worldfile(image_path: str, extent: Tuple[float, float, float, float], width: int, height: int):
    """
    Writes a georeferencing world file (.pgw) for the given image.
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
