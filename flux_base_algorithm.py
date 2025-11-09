import os
from math import gcd
from typing import Dict, Any

from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingParameterString,
    QgsProcessingParameterNumber,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFolderDestination,
    QgsProcessingContext,
    QgsProcessingFeedback,
    QgsProcessingException,
    QgsRasterLayer,
    QgsRectangle,
)
from qgis.utils import iface

from .remote_ai_engine import RemoteAiEngine
from .flux_api_config import ApiConfig


class BaseAiAlgorithm(QgsProcessingAlgorithm):
    """
    Abstract base class for QGIS Processing algorithms that use a remote AI engine.

    This class handles the common logic for:
    1. PREPARE: Defining common UI parameters and rendering the map canvas.
    2. INTEGRATE: Loading the georeferenced result back into QGIS.

    Subclasses must implement the API-specific logic.
    """

    # Common parameter constants
    API_KEY = "API_KEY"
    TILE_SIZE = "TILE_SIZE"
    OUTPUT_DIR = "OUTPUT_DIR"
    SEED = "SEED"

    TILE_SIZE_CHOICES = [
        ("512×512 (1:1)", (512, 512)),
        ("1024×1024 (1:1)", (1024, 1024)),
        ("2048×2048 (1:1)", (2048, 2048)),
        ("1280×720 (16:9)", (1280, 720)),
    ]
    TILE_SIZE_CANVAS_LABEL = "Map Canvas (Full Extent)"

    @property
    def api_config(self) -> ApiConfig:
        """Subclasses must provide their specific API configuration."""
        raise NotImplementedError("Subclasses must define api_config.")

    def name(self):
        return self.api_config.id

    def displayName(self):
        return self.api_config.display_name

    def shortHelpString(self):
        return self.api_config.short_help
        
    def group(self):
        return "FLUX AI Processing"

    def groupId(self):
        return "flux_ai"

    def flags(self):
        # Prevent threading issues with QGIS canvas rendering
        return super().flags() | QgsProcessingAlgorithm.FlagNoThreading

    def initAlgorithm(self, config=None):
        """Initializes the common UI parameters."""
        self.addParameter(
            QgsProcessingParameterString(
                self.API_KEY,
                "FLUX API Key",
                defaultValue="",
                optional=False
            )
        )

        # The 'PROMPT' parameter will be added by subclasses
        # (this is now handled by the subclass initAlgorithm)

        tile_size_options = [label for label, _ in self.TILE_SIZE_CHOICES]
        tile_size_options.append(self.TILE_SIZE_CANVAS_LABEL)
        self.addParameter(
            QgsProcessingParameterEnum(
                self.TILE_SIZE,
                "Tile Size",
                options=tile_size_options,
                defaultValue=1,  # Default to 1024×1024 for better quality
                optional=False
            )
        )

        self.addParameter(
            QgsProcessingParameterFolderDestination(
                self.OUTPUT_DIR,
                "Output Directory"
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                self.SEED,
                "Random Seed (optional)",
                type=QgsProcessingParameterNumber.Integer,
                optional=True,
                minValue=1,
                maxValue=999999999
            )
        )

    def processAlgorithm(self, parameters: Dict[str, Any], context: QgsProcessingContext, feedback: QgsProcessingFeedback):
        """Orchestrates the PREPARE -> PROCESS -> INTEGRATE workflow."""
        
        # --- PREPARE Phase ---
        
        api_key = self.parameterAsString(parameters, self.API_KEY, context).strip()
        if not api_key:
            raise QgsProcessingException("API Key is required. Get one from https://api.bfl.ai")

        # Get common parameters
        tile_size_idx = self.parameterAsEnum(parameters, self.TILE_SIZE, context)
        output_dir = self.parameterAsString(parameters, self.OUTPUT_DIR, context)
        seed = self.parameterAsInt(parameters, self.SEED, context) if parameters.get(self.SEED) is not None else None
        use_canvas_aspect = tile_size_idx == len(self.TILE_SIZE_CHOICES)
        image_format = "PNG"

        feedback.pushInfo("🎨 Starting AI Processing...")
        feedback.pushInfo(f"Output Directory: {output_dir}")

        # Get canvas extent and derive the processing footprint
        canvas = iface.mapCanvas()
        extent = canvas.extent()
        crs = canvas.mapSettings().destinationCrs()
        feedback.pushInfo(f"Processing current canvas view: {extent.toString()} in {crs.authid()}")

        canvas_size = canvas.mapSettings().outputSize()
        canvas_width_px = max(canvas_size.width(), 1)
        canvas_height_px = max(canvas_size.height(), 1)

        if use_canvas_aspect:
            render_extent = extent
            tile_width = canvas_width_px
            tile_height = canvas_height_px
        else:
            tile_width, tile_height = self.TILE_SIZE_CHOICES[tile_size_idx][1]
            tile_width = max(1, int(tile_width))
            tile_height = max(1, int(tile_height))
            desired_ratio = tile_width / tile_height if tile_height else 1.0
            render_extent = self._extent_with_aspect_ratio(extent, desired_ratio)

        extent_tuple = (
            render_extent.xMinimum(), render_extent.yMinimum(),
            render_extent.xMaximum(), render_extent.yMaximum()
        )

        aspect_ratio = self._format_aspect_ratio(tile_width, tile_height)

        label = self.TILE_SIZE_CANVAS_LABEL if use_canvas_aspect else self.TILE_SIZE_CHOICES[tile_size_idx][0]
        feedback.pushInfo(f"Tile Size: {tile_width}×{tile_height} ({label}), Format: {image_format}")

        # --- PROCESS Phase (delegated to subclass) ---

        log_path = os.path.join(output_dir, f"{self.name()}.log")
        remote_engine = RemoteAiEngine(api_key=api_key, log_path=log_path)

        # Subclass provides the specific payload and file naming
        filename, payload = self.get_api_specifics(parameters, context)
        if payload is None:
            payload = {}
        if "aspect_ratio" not in payload:
            payload["aspect_ratio"] = aspect_ratio
        output_path = os.path.join(output_dir, filename)

        feedback.pushInfo(f"Processing tile -> {filename}")
        if feedback.isCanceled():
            return {}

        result = remote_engine.process_tile(
            row=0, col=0,
            extent=extent_tuple,
            size=(tile_width, tile_height),
            prompt=payload.pop("prompt"),  # Remove prompt so it's not duplicated
            out_path=output_path,
            seed=seed,
            image_format=image_format,
            api_config=self.api_config,
            payload=payload
        )

        # --- INTEGRATE Phase ---

        if result["status"] == "Ready":
            feedback.pushInfo(f"✓ Tile successfully processed: {os.path.basename(output_path)}")
            self.load_result_into_qgis(result["output_path"], render_extent, crs, feedback)
        else:
            feedback.reportError(f"Processing failed: {result.get('reason', 'Unknown error')}", fatalError=True)
            return {}
        
        feedback.pushInfo(f"🎉 Processing complete. Log file: {log_path}")
        return {"OUTPUT_DIR": output_dir}

    def _extent_with_aspect_ratio(self, extent: QgsRectangle, desired_ratio: float) -> QgsRectangle:
        """Crops the current extent to match the desired width/height ratio."""
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
            if new_height <= 0:
                new_height = h
        else:
            # Requested aspect is taller -> crop horizontally
            new_height = h
            new_width = min(w, h * desired_ratio)
            if new_width <= 0:
                new_width = w

        half_w = new_width / 2
        half_h = new_height / 2
        return QgsRectangle(cx - half_w, cy - half_h, cx + half_w, cy + half_h)

    def _format_aspect_ratio(self, width: int, height: int) -> str:
        """Returns a simplified aspect ratio string (e.g., '16:9')."""
        if width <= 0 or height <= 0:
            return "1:1"
        ratio_gcd = gcd(width, height)
        if ratio_gcd == 0:
            return "1:1"
        normalized_w = max(1, width // ratio_gcd)
        normalized_h = max(1, height // ratio_gcd)
        return f"{normalized_w}:{normalized_h}"

    def load_result_into_qgis(self, image_path: str, extent: QgsRectangle, crs: Any, feedback: QgsProcessingFeedback):
        """Loads the processed raster layer into the QGIS project."""
        try:
            layer_name = f"AI Result - {self.displayName()}"
            result_layer = QgsRasterLayer(image_path, layer_name, "gdal")
            
            if not result_layer.isValid():
                feedback.pushWarning(f"Could not load the result layer: {image_path}")
                return

            result_layer.setCrs(crs)
            
            from qgis.core import QgsProject
            project = QgsProject.instance()
            root = project.layerTreeRoot()
            
            ai_group = root.findGroup("AI Results")
            if not ai_group:
                ai_group = root.insertGroup(0, "AI Results")
            
            project.addMapLayer(result_layer, False)
            ai_group.addLayer(result_layer)
            
            feedback.pushInfo(f"✅ Result layer loaded: {layer_name}")
            
            # Recenter view on the new layer
            iface.mapCanvas().setExtent(extent)
            iface.mapCanvas().refresh()

        except Exception as e:
            feedback.pushWarning(f"Failed to auto-load layer: {e}")
            feedback.pushInfo(f"You can manually load the result from: {image_path}")

    def get_api_specifics(self, parameters: Dict[str, Any], context: QgsProcessingContext) -> (str, Dict[str, Any]):
        """
        Subclasses must implement this method to provide API-specific details.

        Returns:
            A tuple containing:
            - filename (str): The desired output filename for the tile.
            - payload (Dict[str, Any]): The API-specific parameters. Must include a "prompt" key.
        """
        raise NotImplementedError("Subclasses must implement get_api_specifics.")
