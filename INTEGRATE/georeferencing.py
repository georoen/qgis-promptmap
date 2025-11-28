import os
import logging
from typing import Tuple, List

logger = logging.getLogger(__name__)

try:
    from osgeo import gdal
    gdal.UseExceptions()
except ImportError:
    gdal = None

def write_worldfile(image_path: str, extent: Tuple[float, float, float, float], width: int, height: int, image_format: str):
    """Writes a georeferencing world file for the given image."""
    xmin, ymin, xmax, ymax = extent
    A = (xmax - xmin) / width      # X pixel size
    E = -((ymax - ymin) / height)   # Y pixel size (negative)
    C = xmin + A / 2           # X coordinate of upper-left pixel center
    F = ymax + E / 2           # Y coordinate of upper-left pixel center
    
    ext = ".pgw" if image_format.upper() == "PNG" else ".jgw"
    worldfile_path = os.path.splitext(image_path)[0] + ext
    
    with open(worldfile_path, 'w') as wf:
        wf.write(f"{A}\n0.0\n0.0\n{E}\n{C}\n{F}\n")
    logger.debug(f"World file created: {worldfile_path}")

def build_vrt(vrt_path: str, tile_paths: List[str]) -> None:
    """Creates a VRT mosaic from the processed tiles."""
    if not gdal:
        raise RuntimeError("GDAL is not available. Cannot create VRT.")
    
    if not tile_paths:
        logger.warning("No tile paths provided to build VRT.")
        return

    missing_files = [p for p in tile_paths if not os.path.exists(p)]
    if missing_files:
        raise RuntimeError(f"Cannot create VRT, missing files: {missing_files}")
    
    try:
        gdal.BuildVRT(vrt_path, tile_paths)
        logger.info(f"VRT mosaic created: {vrt_path}")
    except Exception as e:
        raise RuntimeError(f"VRT creation failed: {e}")