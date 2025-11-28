import os
from math import gcd
from datetime import datetime
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
    QgsRasterLayer,
    QgsRectangle,
    QgsVectorLayer,
    QgsProject,
    QgsFields,
    QgsField,
    QgsFeature,
    QgsGeometry,
    QgsVectorFileWriter,
)
from qgis.PyQt.QtCore import QVariant
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
        prompt_value = payload.get("prompt", "")
        output_path = os.path.join(output_dir, filename)
        footprint_path = fp_path_param
        if save_fp and not footprint_path:
            footprint_path = os.path.join(output_dir, f"{self.name()}_footprint.gpkg")

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

        outputs = {"OUTPUT_DIR": output_dir}
        if result["status"] == "Ready":
            feedback.pushInfo(f"✓ Tile successfully processed: {os.path.basename(output_path)}")
            raster_to_load = result["output_path"]
            if save_tiff:
                tiff_path = self._convert_to_geotiff(result["output_path"], feedback)
                if tiff_path:
                    outputs["OUTPUT_RASTER"] = tiff_path
                    raster_to_load = tiff_path
                    feedback.pushInfo(f"GeoTIFF saved: {tiff_path}")
                else:
                    feedback.pushWarning("GeoTIFF requested but could not be created; keeping PNG.")
            self.load_result_into_qgis(raster_to_load, render_extent, crs, feedback)

            if save_fp:
                fp_saved = self._save_footprint_gpkg(
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
                    current_scale
                )
                if fp_saved:
                    outputs["OUTPUT_FOOTPRINT"] = fp_saved
                    feedback.pushInfo(f"Footprint saved: {fp_saved}")
                    self._load_vector_layer(fp_saved, feedback)
                else:
                    feedback.pushWarning("Footprint requested but could not be created.")
        else:
            feedback.reportError(f"Processing failed: {result.get('reason', 'Unknown error')}", fatalError=True)
            return {}
        
        feedback.pushInfo(f"🎉 Processing complete. Log file: {log_path}")
        return outputs

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

    def _mark_advanced(self, parameter):
        """Sets the advanced flag on a processing parameter (QGIS < 3.16 compatibility)."""
        if hasattr(parameter, "flags"):
            parameter.setFlags(parameter.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        return parameter

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

    def _convert_to_geotiff(self, input_path: str, feedback: QgsProcessingFeedback) -> str:
        """Converts the PNG (with worldfile) to GeoTIFF if GDAL is available."""
        try:
            from osgeo import gdal  # type: ignore
        except Exception:
            feedback.pushWarning("GDAL not available; cannot write GeoTIFF.")
            return ""

        try:
            base, _ = os.path.splitext(input_path)
            tiff_path = f"{base}.tif"
            ds = gdal.Open(input_path)
            if not ds:
                feedback.pushWarning(f"Could not open {input_path} for GeoTIFF conversion.")
                return ""
            translate_options = gdal.TranslateOptions(format="GTiff")
            gdal.Translate(tiff_path, ds, options=translate_options)
            return tiff_path
        except Exception as e:
            feedback.pushWarning(f"GeoTIFF conversion failed: {e}")
            return ""

    def _save_footprint_gpkg(
        self,
        footprint_path: str,
        extent: QgsRectangle,
        crs: Any,
        prompt: str,
        tile_width: int,
        tile_height: int,
        aspect_ratio: str,
        seed: Any,
        output_raster_path: str,
        output_dir: str,
        scale: Any,
    ) -> str:
        """Writes the render extent as a polygon GPKG with processing metadata."""
        try:
            fields = QgsFields()
            fields.append(QgsField("prompt", QVariant.String))
            fields.append(QgsField("timestamp", QVariant.String))
            fields.append(QgsField("tile_w", QVariant.Int))
            fields.append(QgsField("tile_h", QVariant.Int))
            fields.append(QgsField("aspect", QVariant.String))
            fields.append(QgsField("seed", QVariant.Int))
            fields.append(QgsField("model", QVariant.String))
            fields.append(QgsField("output", QVariant.String))
            fields.append(QgsField("output_dir", QVariant.String))
            fields.append(QgsField("scale", QVariant.Double))

            mem = QgsVectorLayer(f"Polygon?crs={crs.toWkt()}", "footprint", "memory")
            prov = mem.dataProvider()
            prov.addAttributes(fields)
            mem.updateFields()

            feat = QgsFeature()
            feat.setGeometry(QgsGeometry.fromRect(extent))
            feat.setAttributes([
                prompt,
                datetime.utcnow().isoformat(),
                tile_width,
                tile_height,
                aspect_ratio,
                seed if seed is not None else 0,
                self.api_config.id,
                output_raster_path,
                output_dir,
                float(scale) if scale else 0.0,
            ])
            prov.addFeature(feat)
            mem.updateExtents()

            err, _ = QgsVectorFileWriter.writeAsVectorFormat(
                mem, footprint_path, "UTF-8", crs, "GPKG"
            )
            if err != QgsVectorFileWriter.NoError:
                return ""
            return footprint_path
        except Exception:
            return ""

    def _load_vector_layer(self, gpkg_path: str, feedback: QgsProcessingFeedback):
        """Loads the generated GPKG footprint into the AI Results group."""
        try:
            if not gpkg_path or not os.path.exists(gpkg_path):
                feedback.pushWarning("Footprint path missing; cannot load footprint.")
                return
            layer = QgsVectorLayer(gpkg_path, "AI Result Footprint", "ogr")
            if not layer.isValid():
                feedback.pushWarning(f"Footprint layer invalid: {gpkg_path}")
                return
            project = QgsProject.instance()
            root = project.layerTreeRoot()
            ai_group = root.findGroup("AI Results")
            if not ai_group:
                ai_group = root.insertGroup(0, "AI Results")
            project.addMapLayer(layer, False)
            ai_group.addLayer(layer)
            feedback.pushInfo("Footprint layer loaded to AI Results group.")
        except Exception as e:
            feedback.pushWarning(f"Could not load footprint layer: {e}")

    def get_api_specifics(self, parameters: Dict[str, Any], context: QgsProcessingContext) -> (str, Dict[str, Any]):
        """
        Subclasses must implement this method to provide API-specific details.

        Returns:
            A tuple containing:
            - filename (str): The desired output filename for the tile.
            - payload (Dict[str, Any]): The API-specific parameters. Must include a "prompt" key.
        """
        raise NotImplementedError("Subclasses must implement get_api_specifics.")
