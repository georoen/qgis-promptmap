import os
from typing import Dict, Any

from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingParameterString,
    QgsProcessingParameterNumber,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFolderDestination,
    QgsProcessingParameterDefinition,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterVectorDestination,
    QgsProcessingContext,
    QgsProcessingFeedback,
    QgsProcessingException,
    QgsRectangle,
)
from qgis.utils import iface

from .PROCESS.flux.engine import FluxEngine
from .PROCESS.flux.config import ApiConfig
from .PREPARE.geometry import extent_with_aspect_ratio, format_aspect_ratio
from .PREPARE.rendering import render_map_tile
from .INTEGRATE.loader import load_result_into_qgis, convert_to_geotiff, save_footprint_gpkg, load_vector_layer
from .INTEGRATE.georeferencing import write_worldfile


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
    SAVE_TIFF = "SAVE_TIFF"
    SAVE_FOOTPRINT = "SAVE_FOOTPRINT"
    FOOTPRINT_PATH = "FOOTPRINT_PATH"

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
        tile_param = QgsProcessingParameterEnum(
            self.TILE_SIZE,
            "Tile Size",
            options=tile_size_options,
            defaultValue=1,
            optional=False
        )
        self._mark_advanced(tile_param)
        self.addParameter(tile_param)

        output_param = QgsProcessingParameterFolderDestination(
            self.OUTPUT_DIR,
            "Output Directory"
        )
        self._mark_advanced(output_param)
        self.addParameter(output_param)

        seed_param = QgsProcessingParameterNumber(
            self.SEED,
            "Random Seed (optional)",
            type=QgsProcessingParameterNumber.Integer,
            optional=True,
            minValue=1,
            maxValue=999999999
        )
        self._mark_advanced(seed_param)
        self.addParameter(seed_param)

        save_tiff_param = QgsProcessingParameterBoolean(
            self.SAVE_TIFF,
            "Also save GeoTIFF to disk",
            defaultValue=False
        )
        self.addParameter(save_tiff_param)

        save_fp_param = QgsProcessingParameterBoolean(
            self.SAVE_FOOTPRINT,
            "Save footprint as GeoPackage polygon",
            defaultValue=False
        )
        self.addParameter(save_fp_param)

        fp_path_param = QgsProcessingParameterVectorDestination(
            self.FOOTPRINT_PATH,
            "Footprint output (GPKG)",
            optional=True
        )
        self.addParameter(fp_path_param)

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
        save_tiff = self.parameterAsBoolean(parameters, self.SAVE_TIFF, context)
        save_fp = self.parameterAsBoolean(parameters, self.SAVE_FOOTPRINT, context)
        fp_path_param = self.parameterAsOutputLayer(parameters, self.FOOTPRINT_PATH, context)
        use_canvas_aspect = tile_size_idx == len(self.TILE_SIZE_CHOICES)
        image_format = "PNG"

        feedback.pushInfo("🎨 Starting AI Processing...")
        feedback.pushInfo(f"Output Directory: {output_dir}")

        # Get canvas extent and derive the processing footprint
        canvas = iface.mapCanvas()
        extent = canvas.extent()
        crs = canvas.mapSettings().destinationCrs()
        current_scale = canvas.scale()
        feedback.pushInfo(f"Processing current canvas view: {extent.toString()} in {crs.authid()}")
        if current_scale and current_scale > 5000:
            # Warn when user is zoomed out beyond the recommended interpretation scale.
            feedback.pushWarning(
                f"Map scale is ~1:{int(current_scale)}. The AI works best closer than 1:5000; consider zooming in."
            )

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
            render_extent = extent_with_aspect_ratio(extent, desired_ratio)

        extent_tuple = (
            render_extent.xMinimum(), render_extent.yMinimum(),
            render_extent.xMaximum(), render_extent.yMaximum()
        )

        aspect_ratio = format_aspect_ratio(tile_width, tile_height)

        label = self.TILE_SIZE_CANVAS_LABEL if use_canvas_aspect else self.TILE_SIZE_CHOICES[tile_size_idx][0]
        feedback.pushInfo(f"Tile Size: {tile_width}×{tile_height} ({label}), Format: {image_format}")

        # --- PROCESS Phase ---

        log_path = os.path.join(output_dir, f"{self.name()}.log")
        engine = FluxEngine(api_key=api_key, log_path=log_path)

        # Subclass provides the specific payload and file naming
        filename, payload = self.get_api_specifics(parameters, context)
        if payload is None:
            payload = {}
        if "aspect_ratio" not in payload:
            payload["aspect_ratio"] = aspect_ratio
        prompt_value = payload.get("prompt", "")
        output_path = os.path.join(output_dir, filename)
        footprint_path = fp_path_param
        if save_fp and not footprint_path:
            footprint_path = os.path.join(output_dir, f"{self.name()}_footprint.gpkg")

        feedback.pushInfo(f"Processing tile -> {filename}")
        if feedback.isCanceled():
            return {}

        try:
            # 1. Render Map
            input_png_path = render_map_tile(extent_tuple, tile_width, tile_height, output_path)
            
            # 2. Send Request
            api_result = engine.send_api_request(
                input_path=input_png_path,
                prompt=payload.pop("prompt"),
                seed=seed,
                image_format=image_format,
                api_config=self.api_config,
                extra_params=payload
            )
            
            if not api_result["success"]:
                raise RuntimeError(api_result.get("error", "Unknown API error"))

            # 3. Poll
            polling_result = engine.poll_until_ready(
                api_result["polling_url"], timeout_s=600
            )

            if polling_result["status"] != "Ready":
                raise RuntimeError(f"Processing did not complete: {polling_result['status']} ({polling_result.get('error','')})")

            # 4. Download
            engine.download_stylized_image(
                polling_result["delivery_url"], output_path, tile_width, tile_height, image_format
            )

            # 5. Georeference
            write_worldfile(output_path, extent_tuple, tile_width, tile_height, image_format)
            
            result_status = "Ready"

        except Exception as e:
            feedback.reportError(f"Processing failed: {e}", fatalError=True)
            return {}

        # --- INTEGRATE Phase ---

        outputs = {"OUTPUT_DIR": output_dir}
        if result_status == "Ready":
            feedback.pushInfo(f"✓ Tile successfully processed: {os.path.basename(output_path)}")
            raster_to_load = output_path
            if save_tiff:
                tiff_path = convert_to_geotiff(output_path, feedback)
                if tiff_path:
                    outputs["OUTPUT_RASTER"] = tiff_path
                    raster_to_load = tiff_path
                    feedback.pushInfo(f"GeoTIFF saved: {tiff_path}")
                else:
                    feedback.pushWarning("GeoTIFF requested but could not be created; keeping PNG.")
            
            load_result_into_qgis(raster_to_load, render_extent, crs, feedback, self.displayName())

            if save_fp:
                fp_saved = save_footprint_gpkg(
                    footprint_path,
                    render_extent,
                    crs,
                    prompt_value,
                    tile_width,
                    tile_height,
                    aspect_ratio,
                    seed,
                    raster_to_load,
                    output_dir,
                    current_scale,
                    self.api_config.id
                )
                if fp_saved:
                    outputs["OUTPUT_FOOTPRINT"] = fp_saved
                    feedback.pushInfo(f"Footprint saved: {fp_saved}")
                    load_vector_layer(fp_saved, feedback)
                else:
                    feedback.pushWarning("Footprint requested but could not be created.")
        
        feedback.pushInfo(f"🎉 Processing complete. Log file: {log_path}")
        return outputs

    def _mark_advanced(self, parameter):
        """Sets the advanced flag on a processing parameter (QGIS < 3.16 compatibility)."""
        if hasattr(parameter, "flags"):
            parameter.setFlags(parameter.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        return parameter

    def get_api_specifics(self, parameters: Dict[str, Any], context: QgsProcessingContext) -> (str, Dict[str, Any]):
        """
        Subclasses must implement this method to provide API-specific details.

        Returns:
            A tuple containing:
            - filename (str): The desired output filename for the tile.
            - payload (Dict[str, Any]): The API-specific parameters. Must include a "prompt" key.
        """
        raise NotImplementedError("Subclasses must implement get_api_specifics.")
