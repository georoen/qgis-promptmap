import os
from typing import Dict, Any

from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingParameterString,
    QgsProcessingParameterNumber,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFolderDestination,
    QgsProcessingParameterBoolean,
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
    IMAGE_FORMAT = "IMAGE_FORMAT"
    SEED = "SEED"
    CREATE_VRT = "CREATE_VRT"
    PRESERVE_CANVAS_ASPECT = "PRESERVE_CANVAS_ASPECT"

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

        self.addParameter(
            QgsProcessingParameterEnum(
                self.TILE_SIZE,
                "Tile Size",
                options=["512×512", "1024×1024"],
                defaultValue=1,  # Default to 1024 for better quality
                optional=False
            )
        )

        self.addParameter(
            QgsProcessingParameterBoolean(
                self.PRESERVE_CANVAS_ASPECT,
                "Use Canvas Aspect Ratio",
                defaultValue=False
            )
        )

        self.addParameter(
            QgsProcessingParameterFolderDestination(
                self.OUTPUT_DIR,
                "Output Directory"
            )
        )

        self.addParameter(
            QgsProcessingParameterEnum(
                self.IMAGE_FORMAT,
                "Output Format",
                options=["PNG", "JPEG"],
                defaultValue=0,
                optional=False
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

        self.addParameter(
            QgsProcessingParameterBoolean(
                self.CREATE_VRT,
                "Create VRT Mosaic",
                defaultValue=True
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
        format_idx = self.parameterAsEnum(parameters, self.IMAGE_FORMAT, context)
        seed = self.parameterAsInt(parameters, self.SEED, context) if parameters.get(self.SEED) is not None else None
        create_vrt = self.parameterAsBoolean(parameters, self.CREATE_VRT, context)
        preserve_aspect = self.parameterAsBoolean(parameters, self.PRESERVE_CANVAS_ASPECT, context)

        N = 512 if tile_size_idx == 0 else 1024
        image_format = "PNG" if format_idx == 0 else "JPEG"

        feedback.pushInfo("🎨 Starting AI Processing...")
        feedback.pushInfo(f"Output Directory: {output_dir}")

        # Get canvas extent and calculate a square processing area
        canvas = iface.mapCanvas()
        extent = canvas.extent()
        crs = canvas.mapSettings().destinationCrs()
        feedback.pushInfo(f"Processing current canvas view: {extent.toString()} in {crs.authid()}")

        w, h = extent.width(), extent.height()
        canvas_size = canvas.mapSettings().outputSize()
        canvas_width_px = max(canvas_size.width(), 1)
        canvas_height_px = max(canvas_size.height(), 1)

        if preserve_aspect:
            render_extent = extent
            scale = N / max(canvas_width_px, canvas_height_px)
            tile_width = max(1, int(round(canvas_width_px * scale)))
            tile_height = max(1, int(round(canvas_height_px * scale)))
        else:
            cx, cy = extent.center().x(), extent.center().y()
            half_size = max(w, h) / 2
            render_extent = QgsRectangle(cx - half_size, cy - half_size, cx + half_size, cy + half_size)
            tile_width = tile_height = N

        extent_tuple = (
            render_extent.xMinimum(), render_extent.yMinimum(),
            render_extent.xMaximum(), render_extent.yMaximum()
        )

        feedback.pushInfo(f"Tile Size: {tile_width}×{tile_height}, Format: {image_format}")
        if preserve_aspect:
            feedback.pushInfo("Canvas aspect ratio preserved (experimental mode)")

        # --- PROCESS Phase (delegated to subclass) ---

        log_path = os.path.join(output_dir, f"{self.name()}.log")
        remote_engine = RemoteAiEngine(api_key=api_key, log_path=log_path)

        # Subclass provides the specific payload and file naming
        filename, payload = self.get_api_specifics(parameters, context)
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
