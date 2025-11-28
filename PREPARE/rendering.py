import os
import logging
from typing import Tuple

logger = logging.getLogger(__name__)

def render_map_tile(extent_tuple: Tuple[float, float, float, float], width: int, height: int, base_path: str) -> str:
    """Renders the QGIS map canvas to a PNG file for the AI service."""
    output_path = base_path.replace('.png', '_input.png').replace('.jpeg', '_input.png')
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    logger.info(f"Rendering map canvas to: {output_path}")
    
    try:
        from qgis.core import (
            QgsMapSettings, QgsRectangle, QgsMapRendererParallelJob
        )
        from qgis.utils import iface
        from PyQt5.QtCore import QSize, Qt

        canvas = iface.mapCanvas()
        if not canvas:
            raise RuntimeError("Map Canvas is not available.")
            
        settings = QgsMapSettings()
        render_extent = QgsRectangle(*extent_tuple)
        settings.setExtent(render_extent)
        settings.setOutputSize(QSize(width, height))
        
        layers = canvas.layers()
        if not layers:
            raise RuntimeError("No visible layers in canvas to render.")
            
        settings.setLayers(layers)
        settings.setDestinationCrs(canvas.mapSettings().destinationCrs())
        settings.setBackgroundColor(Qt.transparent)
        
        job = QgsMapRendererParallelJob(settings)
        job.start()
        job.waitForFinished()
        
        rendered_image = job.renderedImage()
        if rendered_image.isNull() or not rendered_image.save(output_path, 'PNG'):
            raise RuntimeError(f"Failed to render or save map tile to {output_path}")

        return output_path
        
    except Exception as e:
        logger.error(f"QGIS map rendering failed: {e}. Falling back to demo tile.")
        try:
            return create_demo_tile_fallback(width, height, output_path)
        except Exception as fe:
            logger.error(f"Demo tile fallback also failed: {fe}")
            raise RuntimeError(f"Map rendering and fallback failed. Original error: {e}")

def create_demo_tile_fallback(width: int, height: int, output_path: str) -> str:
    """Creates a placeholder map tile if QGIS rendering fails."""
    try:
        from PIL import Image, ImageDraw
        img = Image.new('RGBA', (width, height), (100, 150, 200, 255))
        draw = ImageDraw.Draw(img)
        draw.text((width // 2 - 50, height // 2), "DEMO MAP", fill="white")
        img.save(output_path, 'PNG')
        return output_path
    except ImportError:
        with open(output_path, 'wb') as f:
            f.write(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc`\x00\x00\x00\x02\x00\x01\xe2\x21\xbc\x33\x00\x00\x00\x00IEND\xaeB`\x82')
        return output_path