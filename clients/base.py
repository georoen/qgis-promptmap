"""
Base classes for FLUX/Gemini clients.
"""

import os
import time
from os import environ
from math import gcd
from typing import Dict, Any, Optional, Tuple

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
    QgsProject,
    QgsVectorFileWriter,
    QgsVectorLayer,
    QgsFields,
    QgsField,
    QgsFeature,
    QgsGeometry,
    QgsWkbTypes,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransformContext,
    QgsRectangle
)
from qgis import processing
from qgis.utils import iface
from PyQt5.QtCore import QSize, Qt, QVariant
from PyQt5.QtGui import QImage, QPainter

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
        # Read API key from environment variable if set; the user can override
        # it in the dialog.  Supported env vars (checked in order):
        #   BFL_API_KEY   – Black Forest Labs models
        #   GEMINI_API_KEY – Google Gemini models
        #   PROMPTMAP_API_KEY – generic fallback for any PromptMap model
        default_key = (
            environ.get("BFL_API_KEY")
            or environ.get("GEMINI_API_KEY")
            or environ.get("PROMPTMAP_API_KEY")
            or ""
        )
        self.addParameter(QgsProcessingParameterString(
            self.API_KEY, "API Key", defaultValue=default_key, optional=False
        ))
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
            # Crop the canvas extent to the exact aspect ratio of the target tile size.
            # Without this, the rendered PNG would be letterboxed / pillarboxed and the
            # georeferencing would map the full (uncropped) extent onto a distorted image.
            render_extent = extent_with_aspect_ratio(extent, ratio)

        aspect_ratio_str = format_aspect_ratio(target_w, target_h)
        feedback.pushInfo(f"Image geometry: {target_w}x{target_h} ({aspect_ratio_str})")

        # 3. Export Map Canvas to Image
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        input_path = os.path.join(output_dir, "input.png")
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
        output_path = os.path.join(output_dir, "output.png")
        
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

        # 5b. Burn watermark (plugin icon, lower-right corner, proportionally scaled)
        if self._apply_watermark(output_path):
            feedback.pushInfo("Watermark applied.")
        else:
            feedback.reportError("Watermark skipped: docs/watermark.png not found or image unreadable.")

        # 6. Georeference
        feedback.pushInfo(f"Georeferencing image...")

        # Create GeoTIFF instead of Worldfile
        # Note: We use render_extent because the AI output covers the same geographic area 
        # as the input, even if the pixel resolution (e.g. 2048x2048 vs 512x512) changes.
        geotiff_path = create_geotiff(output_path, render_extent, crs)
        
        # Load Raster Layer
        self._load_raster_layer(geotiff_path, crs, feedback)
        
        # 7. Export & Load Metadata (GPKG)
        metadata = {
            "timestamp": str(int(time.time())),
            "model": self.displayName(),
            "prompt": prompt,
            "tile_size": self.TILE_OPTIONS[tile_idx][0]
        }
        
        try:
            gpkg_path = write_metadata_gpkg(geotiff_path, render_extent, crs, metadata)
            self._load_vector_layer(gpkg_path, crs, feedback)
        except Exception as e:
            feedback.reportError(f"Metadata export failed: {e}")
            
        return {"OUTPUT": geotiff_path}

    def execute_api(self, api_key, input_path, prompt, aspect_ratio, parameters, context, feedback):
        """Subclasses must implement this."""
        raise NotImplementedError

    def read_image_as_base64(self, path: str) -> str:
        """Reads an image file and returns its base64 encoded string."""
        import base64
        with open(path, 'rb') as f:
            return base64.b64encode(f.read()).decode('ascii')

    def log(self, feedback, message: str):
        """Logs a message to the feedback object if available."""
        if feedback:
            feedback.pushInfo(message)

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

    def _load_vector_layer(self, path, crs, feedback):
        layer = QgsVectorLayer(path, f"{self.displayName()} Metadata", "ogr")
        if layer.isValid():
            layer.setCrs(crs)
            QgsProject.instance().addMapLayer(layer)
        else:
            feedback.reportError("Failed to load metadata layer.")

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

    def _apply_watermark(self, image_path: str, opacity: float = 0.5) -> bool:
        """
        Burns the plugin icon as a watermark into the lower-right corner of the image.

        The watermark is scaled proportionally to 12 % of the shorter image dimension,
        so it looks consistent across 512×512, 1024×1024, 2048×2048 and 1280×720 outputs.
        A padding of 2 % of the shorter dimension keeps it away from the edge.

        Uses only PyQt5 (bundled with QGIS) – no additional dependencies required.

        Args:
            image_path: Path to the PNG to modify in-place.
            opacity: Watermark opacity (0.0–1.0).

        Returns:
            True if the watermark was applied, False if skipped (missing file or
            null image).  The pipeline continues either way; the caller decides
            whether to surface a warning.
        """
        _WATERMARK_RATIO = 0.12  # watermark size relative to shorter image side
        _PADDING_RATIO   = 0.02  # margin from image edge

        # --- load target image -------------------------------------------------
        image = QImage(image_path)
        if image.isNull():
            return False  # output image unreadable – skip without breaking pipeline

        # QPainter requires a 32-bit ARGB format for correct alpha / opacity blending
        image = image.convertToFormat(QImage.Format_ARGB32_Premultiplied)

        # --- load watermark icon -----------------------------------------------
        # base.py lives in  <plugin_root>/clients/base.py  →  go up one level
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs", "watermark.png")
        watermark = QImage(icon_path)
        if watermark.isNull():
            return False  # docs/watermark.png missing – skip without breaking pipeline

        # --- scale proportionally to the shorter image side --------------------
        short_side = min(image.width(), image.height())
        wm_size  = max(16, int(short_side * _WATERMARK_RATIO))  # at least 16 px
        padding  = max(4,  int(short_side * _PADDING_RATIO))    # at least  4 px

        watermark = watermark.scaled(
            wm_size, wm_size,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )

        # --- position: bottom-right corner -------------------------------------
        x = image.width()  - watermark.width()  - padding
        y = image.height() - watermark.height() - padding

        # --- composite with opacity --------------------------------------------
        painter = QPainter(image)
        painter.setOpacity(opacity)
        painter.drawImage(x, y, watermark)
        painter.end()

        # --- overwrite the PNG in-place ----------------------------------------
        image.save(image_path, "PNG")
        return True


# =============================================================================
# Utility Functions
# =============================================================================

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


def create_geotiff(image_path: str, extent: QgsRectangle, crs: QgsCoordinateReferenceSystem) -> str:
    """
    Converts the image to a GeoTIFF with the specified extent and CRS.
    """
    from osgeo import gdal
    
    geotiff_path = os.path.splitext(image_path)[0] + ".tif"
    
    # Use gdal.Translate with -a_ullr to assign bounds and -a_srs for CRS
    ds = gdal.Translate(
        geotiff_path,
        image_path,
        format='GTiff',
        outputSRS=crs.toWkt(),
        options=f"-a_ullr {extent.xMinimum()} {extent.yMaximum()} {extent.xMaximum()} {extent.yMinimum()}"
    )
    
    if ds is None:
        raise Exception(f"Failed to create GeoTIFF at {geotiff_path}")
        
    ds = None # Explicitly close dataset
    
    return geotiff_path


def write_metadata_gpkg(output_path: str, extent: QgsRectangle, crs, metadata: dict) -> str:
    """
    Writes a GPKG containing a vector layer with the extent and metadata.
    """
    gpkg_path = os.path.splitext(output_path)[0] + ".gpkg"
    
    # 1. Define Fields
    fields = QgsFields()
    for key in metadata.keys():
        fields.append(QgsField(key, QVariant.String))
        
    # 2. Initialize Writer
    save_options = QgsVectorFileWriter.SaveVectorOptions()
    save_options.driverName = "GPKG"
    save_options.layerName = "metadata"
    
    writer = QgsVectorFileWriter.create(
        gpkg_path,
        fields,
        QgsWkbTypes.Polygon,
        crs,
        QgsCoordinateTransformContext(),
        save_options
    )
    
    if writer.hasError() != QgsVectorFileWriter.NoError:
        raise Exception(f"Failed to create GPKG: {writer.errorMessage()}")
        
    # 3. Add Feature
    feat = QgsFeature()
    feat.setGeometry(QgsGeometry.fromRect(extent))
    
    # Ensure attributes match fields order
    attrs = [str(metadata.get(field.name(), "")) for field in fields]
    feat.setAttributes(attrs)
    
    writer.addFeature(feat)
    del writer # Explicitly delete to flush/close file
    
    return gpkg_path
