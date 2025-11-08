import os
from typing import Dict, Any, Optional

from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingParameterRasterLayer,
    QgsProcessingParameterString,
    QgsProcessingParameterNumber,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFolderDestination,
    QgsProcessingParameterBoolean,
    QgsProcessingContext,
    QgsProcessingFeedback,
    QgsProcessingException,
    QgsRasterLayer,
    QgsCoordinateReferenceSystem,
    QgsRectangle,
)

from .flux_stylize_tiles import FluxStylizeTiles


class FluxStylizeAlgorithm(QgsProcessingAlgorithm):
    """QGIS Processing Algorithm for FLUX tile stylization."""

    # Parameter constants
    INPUT_RASTER = "INPUT_RASTER"
    API_KEY = "API_KEY"
    PROMPT = "PROMPT"
    TILE_SIZE = "TILE_SIZE"
    OUTPUT_DIR = "OUTPUT_DIR"
    IMAGE_FORMAT = "IMAGE_FORMAT"
    SEED = "SEED"
    CREATE_VRT = "CREATE_VRT"

    def __init__(self):
        super().__init__()

    def createInstance(self):
        return FluxStylizeAlgorithm()

    def name(self):
        return "flux_stylize_tiles"

    def displayName(self):
        return "FLUX Stylize Tiles"

    def group(self):
        return "FLUX AI Processing"

    def groupId(self):
        return "flux_ai"

    def shortHelpString(self):
        return """
Transform raster tiles using FLUX AI stylization.

Parameters:
- Input Raster: Source raster layer to be stylized
- API Key: Your FLUX API key (get one at https://api.flux.dev)
- Prompt: Description of desired style (e.g. "watercolor painting", "cyberpunk neon")
- Tile Size: Size of each tile in pixels (512, 1024)
- Output Directory: Folder to save stylized tiles
- Format: PNG (with transparency) or JPEG
- Seed: Optional random seed for reproducible results
- Create VRT: Build a Virtual Raster mosaic of all tiles

The algorithm divides your raster into tiles, sends them to FLUX API for AI stylization,
and downloads the results with proper world files for georeferencing.
        """

    def initAlgorithm(self, config=None):
        # Input raster layer
        self.addParameter(
            QgsProcessingParameterRasterLayer(
                self.INPUT_RASTER,
                "Input Raster Layer",
                optional=False
            )
        )

        # API Key - sensitive parameter
        self.addParameter(
            QgsProcessingParameterString(
                self.API_KEY,
                "FLUX API Key",
                defaultValue="",
                optional=False
            )
        )

        # Stylization prompt
        self.addParameter(
            QgsProcessingParameterString(
                self.PROMPT,
                "Style Prompt",
                defaultValue="watercolor painting",
                multiLine=True,
                optional=False
            )
        )

        # Tile size
        self.addParameter(
            QgsProcessingParameterEnum(
                self.TILE_SIZE,
                "Tile Size",
                options=["512×512", "1024×1024"],
                defaultValue=0,
                optional=False
            )
        )

        # Output directory
        self.addParameter(
            QgsProcessingParameterFolderDestination(
                self.OUTPUT_DIR,
                "Output Directory",
                optional=False
            )
        )

        # Image format
        self.addParameter(
            QgsProcessingParameterEnum(
                self.IMAGE_FORMAT,
                "Output Format",
                options=["PNG", "JPEG"],
                defaultValue=0,
                optional=False
            )
        )

        # Optional seed
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

        # Create VRT mosaic
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.CREATE_VRT,
                "Create VRT Mosaic",
                defaultValue=True,
                optional=True
            )
        )

    def processAlgorithm(self, parameters, context: QgsProcessingContext, feedback: QgsProcessingFeedback):
        # Get parameters
        raster_layer = self.parameterAsRasterLayer(parameters, self.INPUT_RASTER, context)
        api_key = self.parameterAsString(parameters, self.API_KEY, context).strip()
        prompt = self.parameterAsString(parameters, self.PROMPT, context).strip()
        tile_size_idx = self.parameterAsEnum(parameters, self.TILE_SIZE, context)
        output_dir = self.parameterAsString(parameters, self.OUTPUT_DIR, context)
        format_idx = self.parameterAsEnum(parameters, self.IMAGE_FORMAT, context)
        seed = self.parameterAsInt(parameters, self.SEED, context) if parameters.get(self.SEED) is not None else None
        create_vrt = self.parameterAsBoolean(parameters, self.CREATE_VRT, context)

        # Validate inputs
        if not api_key:
            raise QgsProcessingException("API Key ist erforderlich. Holen Sie sich einen auf https://api.flux.dev")
        if not prompt:
            raise QgsProcessingException("Style Prompt ist erforderlich")

        # Convert parameters
        N = 512 if tile_size_idx == 0 else 1024
        image_format = "PNG" if format_idx == 0 else "JPEG"

        feedback.pushInfo(f"Starte FLUX Tile Stylization...")
        feedback.pushInfo(f"Eingabe: {raster_layer.name()}")
        feedback.pushInfo(f"Tile-Größe: {N}×{N}")
        feedback.pushInfo(f"Format: {image_format}")
        feedback.pushInfo(f"Ausgabe: {output_dir}")

        # Initialize FLUX processor
        log_path = os.path.join(output_dir, "flux_processing.log")
        flux = FluxStylizeTiles(api_key=api_key, log_path=log_path)

        try:
            # ✅ VERWENDE MAP CANVAS statt Layer-Extent!
            from qgis.utils import iface
            canvas = iface.mapCanvas()
            
            # Aktueller Canvas-Extent (was der User sieht)
            extent = canvas.extent()
            crs = canvas.mapSettings().destinationCrs()
            
            feedback.pushInfo(f"Canvas Extent: {extent.toString()}")
            feedback.pushInfo(f"Canvas CRS: {crs.authid()}")
            feedback.pushInfo(f"Sichtbare Layer: {len(canvas.layers())}")

            # ✅ QUADRATISCHEN EXTENT BERECHNEN
            w, h = extent.width(), extent.height()
            cx, cy = extent.center().x(), extent.center().y()
            
            if w > h:
                # Breiter → erweitere Höhe
                half_size = w / 2
                square_extent = QgsRectangle(cx - half_size, cy - half_size, cx + half_size, cy + half_size)
            else:
                # Höher → erweitere Breite
                half_size = h / 2
                square_extent = QgsRectangle(cx - half_size, cy - half_size, cx + half_size, cy + half_size)
                
            feedback.pushInfo(f"Quadratischer Extent: {square_extent.toString()}")
            
            # Single tile processing für aktuellen Canvas
            tile_files = []
            row, col = 0, 0
            extent_tuple = (square_extent.xMinimum(), square_extent.yMinimum(),
                           square_extent.xMaximum(), square_extent.yMaximum())
            
            # Generate filename
            filename = f"flux_tile_{row:03d}_{col:03d}.{image_format.lower()}"
            output_path = os.path.join(output_dir, filename)
            
            feedback.pushInfo(f"Verarbeite Tile {row},{col} -> {filename}")
            
            if feedback.isCanceled():
                return {}

            # Process tile
            result = flux.process_tile(
                row=row,
                col=col,
                extent=extent_tuple,
                N=N,
                prompt=prompt,
                out_path=output_path,
                seed=seed,
                image_format=image_format,
                payload={}  # Default FLUX endpoint
            )
            
            if result["status"] == "Ready":
                tile_files.append(output_path)
                feedback.pushInfo(f"✓ Tile erfolgreich stylisiert: {filename}")
                
                # ✅ AUTOMATISCHES LADEN ALS RASTER-LAYER
                try:
                    layer_name = f"FLUX Stylized - {raster_layer.name()}"
                    raster_layer_result = QgsRasterLayer(output_path, layer_name, "gdal")
                    
                    if raster_layer_result.isValid():
                        # CRS vom Canvas übernehmen
                        target_crs = canvas.mapSettings().destinationCrs()
                        raster_layer_result.setCrs(target_crs)
                        
                        # Layer ins Projekt laden
                        from qgis.core import QgsProject, QgsLayerTreeGroup
                        project = QgsProject.instance()
                        root = project.layerTreeRoot()
                        
                        # FLUX-Gruppe erstellen falls nicht existiert
                        flux_group = root.findGroup("FLUX AI Results")
                        if not flux_group:
                            flux_group = root.insertGroup(0, "FLUX AI Results")
                        
                        # Layer zur Gruppe hinzufügen
                        project.addMapLayer(raster_layer_result, False)  # False = nicht zur Root
                        flux_group.addLayer(raster_layer_result)
                        
                        feedback.pushInfo(f"✅ Raster-Layer geladen: {layer_name}")
                        feedback.pushInfo(f"📍 CRS: {target_crs.authid()}")
                        
                        # Canvas auf den Layer zoomen (optional)
                        canvas.setExtent(square_extent)
                        canvas.refresh()
                        feedback.pushInfo("🗺️ Canvas auf stylisierte Karte zentriert")
                        
                    else:
                        feedback.pushWarning(f"⚠️ Raster-Layer ungültig: {output_path}")
                        
                except Exception as e:
                    feedback.pushWarning(f"⚠️ Automatisches Laden fehlgeschlagen: {e}")
                    feedback.pushInfo(f"💡 Manuell laden: {output_path}")
                
            elif result["status"] == "Failed":
                feedback.reportError(f"✗ Tile Verarbeitung fehlgeschlagen: {result.get('reason', 'Unbekannt')}")
            elif result["status"] == "Timeout":
                feedback.reportError(f"✗ Timeout bei Tile-Verarbeitung")
            
            # Create VRT if requested and tiles were created
            if create_vrt and tile_files:
                try:
                    vrt_path = os.path.join(output_dir, "flux_stylized_mosaic.vrt")
                    flux.build_vrt(vrt_path, tile_files)
                    
                    # VRT auch automatisch laden
                    vrt_layer = QgsRasterLayer(vrt_path, "FLUX Ultra VRT Mosaic", "gdal")
                    if vrt_layer.isValid():
                        project = QgsProject.instance()
                        flux_group = project.layerTreeRoot().findGroup("FLUX AI Results")
                        if flux_group:
                            project.addMapLayer(vrt_layer, False)
                            flux_group.addLayer(vrt_layer)
                    
                    feedback.pushInfo(f"✓ VRT Mosaik erstellt und geladen: flux_stylized_mosaic.vrt")
                except RuntimeError as e:
                    feedback.pushWarning(f"VRT Erstellung übersprungen: {e}")

            feedback.pushInfo(f"🎉 Verarbeitung abgeschlossen. {len(tile_files)} Tiles erstellt und geladen.")
            feedback.pushInfo(f"📂 Log-Datei: {log_path}")
            feedback.pushInfo(f"📁 Output: {output_dir}")
            
            return {"OUTPUT_DIR": output_dir}

        except Exception as e:
            raise QgsProcessingException(f"Fehler bei FLUX Verarbeitung: {str(e)}")

    def flags(self):
        return super().flags() | QgsProcessingAlgorithm.FlagNoThreading