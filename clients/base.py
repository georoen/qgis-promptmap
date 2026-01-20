"""
Base classes for FLUX/Gemini clients.
"""

import os
import time
from typing import Dict, Any, Optional

from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingParameterString,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFolderDestination,
    QgsProcessingParameterNumber,
    QgsProcessingException,
    QgsMapSettings,
    QgsMapRendererParallelJob,
    QgsRasterLayer,
    QgsProject
)
from qgis.utils import iface
from PyQt5.QtCore import QSize, Qt

from ..utils import extent_with_aspect_ratio, format_aspect_ratio, write_worldfile

class BaseAIAlgorithm(QgsProcessingAlgorithm):
    """Base class for AI processing algorithms."""

    API_KEY = "API_KEY"
    PROMPT = "PROMPT"
    TILE_SIZE = "TILE_SIZE"
    OUTPUT_DIR = "OUTPUT_DIR"
    
    TILE_OPTIONS = [
        ("512×512 (1:1)", 512, 512),
        ("1024×1024 (1:1)", 1024, 1024),
        ("2048×2048 (1:1)", 2048, 2048),
        ("1280×720 (16:9)", 1280, 720),
        ("Map Canvas (Full Extent)", 0, 0)
    ]

    def initAlgorithm(self, config=None):
        """Initialize common parameters."""
        self.addParameter(QgsProcessingParameterString(self.API_KEY, "API Key", optional=False))
        self.addParameter(QgsProcessingParameterString(self.PROMPT, "Prompt", multiLine=True, optional=False))
        
        self.addParameter(QgsProcessingParameterEnum(
            self.TILE_SIZE, "Tile Size", options=[t[0] for t in self.TILE_OPTIONS], defaultValue=1
        ))
        
        self.addParameter(QgsProcessingParameterFolderDestination(self.OUTPUT_DIR, "Output Directory"))
        
        # Subclasses can add more parameters here

    def processAlgorithm(self, parameters, context, feedback):
        """Common processing logic."""
        # 1. Extract Common Parameters
        api_key = self.parameterAsString(parameters, self.API_KEY, context)
        prompt = self.parameterAsString(parameters, self.PROMPT, context)
        tile_idx = self.parameterAsEnum(parameters, self.TILE_SIZE, context)
        output_dir = self.parameterAsString(parameters, self.OUTPUT_DIR, context)

        # 2. Setup Geometry
        canvas = iface.mapCanvas()
        extent = canvas.extent()
        crs = canvas.mapSettings().destinationCrs()
        target_w, target_h = self.TILE_OPTIONS[tile_idx][1], self.TILE_OPTIONS[tile_idx][2]
        
        if target_w == 0:  # Using "Map Canvas (Full Extent)"
            size = canvas.mapSettings().outputSize()
            target_w, target_h = size.width(), size.height()
            render_extent = extent
        else:
            ratio = target_w / target_h
            render_extent = extent_with_aspect_ratio(extent, ratio)  # TODO: Explain why we do this

        aspect_ratio_str = format_aspect_ratio(target_w, target_h)
        feedback.pushInfo(f"Image geometry: {target_w}x{target_h} ({aspect_ratio_str})")

        # 3. Export Map Canvas to Image
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        input_path = os.path.join(output_dir, f"{self.name()}_input.png") # TODO: Reduce filename to input.png only
        self._render_map(render_extent, target_w, target_h, input_path)
        
        if not os.path.exists(input_path):
            raise QgsProcessingException(f"Failed to render input map to {input_path}")

        if feedback.isCanceled(): return {}

        # 4. Execute Subclass Logic (API Call)
        result = self.execute_api(api_key, input_path, prompt, aspect_ratio_str, parameters, context, feedback)
        
        if not result["success"]:
            raise QgsProcessingException(result["error"])

        # 5. Download/Save generated result
        # The API method should return either a URL (for download) or raw data (for save)
        output_path = os.path.join(output_dir, f"{self.name()}_{int(time.time())}.png") # TODO: Reduce filename to output.png only
        
        if "url" in result:
            if not self.download_result(result["url"], output_path):
                raise QgsProcessingException("Download failed.")
        elif "data" in result:
            if not self.save_result(result["data"], output_path):
                raise QgsProcessingException("Save failed.")
            
        if os.path.exists(output_path):
            feedback.pushInfo(f"Saved generated image to {output_path}")
        else:
            raise QgsProcessingException(f"Failed to save result to {output_path}")
        
        # 6. Georeference
        feedback.pushInfo(f"Georeferencing image...")

        # Write worldfile
        write_worldfile(output_path, (render_extent.xMinimum(), render_extent.yMinimum(), render_extent.xMaximum(), render_extent.yMaximum()), target_w, target_h)
        
        # Load Raster Layer
        self._load_raster_layer(output_path, crs, feedback)
        
        # 7. Export & Load Metadata (GPKG)
        metadata = {
            "timestamp": str(int(time.time())),
            "model": self.displayName(),
            "prompt": prompt,
            "tile_size": self.TILE_OPTIONS[tile_idx][0]
        }
        
        try:
            gpkg_path = self._export_metadata_gpkg(output_path, render_extent, crs, metadata)
            self._load_vector_layer(gpkg_path, crs, feedback)
        except Exception as e:
            feedback.reportError(f"Metadata export failed: {e}")
            
        return {"OUTPUT": output_path}

    def execute_api(self, api_key, input_path, prompt, aspect_ratio, parameters, context, feedback):
        """Subclasses must implement this."""
        raise NotImplementedError

    def _render_map(self, extent, width, height, path):
        settings = QgsMapSettings()
        settings.setLayers(iface.mapCanvas().layers())
        settings.setDestinationCrs(iface.mapCanvas().mapSettings().destinationCrs())
        settings.setExtent(extent)
        settings.setOutputSize(QSize(width, height))
        settings.setBackgroundColor(Qt.transparent)
        job = QgsMapRendererParallelJob(settings)
        job.start()
        job.waitForFinished()
        if not job.renderedImage().save(path, "PNG"):
            raise QgsProcessingException(f"Failed to save rendered image to {path}")

    def _load_raster_layer(self, path, crs, feedback):
        layer = QgsRasterLayer(path, f"{self.displayName()} Result", "gdal")
        if layer.isValid():
            layer.setCrs(crs)
            QgsProject.instance().addMapLayer(layer)
        else:
            feedback.reportError("Failed to load result layer.")

    def download_result(self, url: str, output_path: str) -> bool:
        import requests
        try:
            response = requests.get(url, timeout=60)
            response.raise_for_status()
            with open(output_path, 'wb') as f: f.write(response.content)
            return True
        except Exception: return False

    def save_result(self, b64_data: str, output_path: str) -> bool:
        import base64
        try:
            img_bytes = base64.b64decode(b64_data)
            with open(output_path, 'wb') as f: f.write(img_bytes)
            return True
        except Exception: return False
