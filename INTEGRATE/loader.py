import os
from datetime import datetime
from typing import Any

from qgis.core import (
    QgsRasterLayer,
    QgsRectangle,
    QgsProject,
    QgsVectorLayer,
    QgsFields,
    QgsField,
    QgsFeature,
    QgsGeometry,
    QgsVectorFileWriter,
    QgsProcessingFeedback
)
from qgis.PyQt.QtCore import QVariant
from qgis.utils import iface

def load_result_into_qgis(image_path: str, extent: QgsRectangle, crs: Any, feedback: QgsProcessingFeedback, display_name: str):
    """Loads the processed raster layer into the QGIS project."""
    try:
        layer_name = f"AI Result - {display_name}"
        result_layer = QgsRasterLayer(image_path, layer_name, "gdal")
        
        if not result_layer.isValid():
            feedback.pushWarning(f"Could not load the result layer: {image_path}")
            return

        result_layer.setCrs(crs)
        
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

def convert_to_geotiff(input_path: str, feedback: QgsProcessingFeedback) -> str:
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

def save_footprint_gpkg(
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
    model_id: str
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
            model_id,
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

def load_vector_layer(gpkg_path: str, feedback: QgsProcessingFeedback):
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