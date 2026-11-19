"""Run with QGIS's Python: QT_QPA_PLATFORM=offscreen python3 tests/smoke_qgis.py."""

import importlib.util
import sys
import tempfile
from configparser import ConfigParser
from pathlib import Path
from types import SimpleNamespace

from qgis.core import (
    Qgis, QgsApplication, QgsCoordinateReferenceSystem, QgsRectangle, QgsVectorLayer,
)
from qgis.gui import QgsMapCanvas
from qgis.PyQt.QtGui import QColor, QImage

ROOT = Path(__file__).resolve().parents[1]
app = QgsApplication([], False)
app.initQgis()
sys.path.insert(0, str(Path(QgsApplication.pkgDataPath()) / 'python/plugins'))
spec = importlib.util.spec_from_file_location(
    'promptmap', ROOT / '__init__.py', submodule_search_locations=[str(ROOT)],
)
module = importlib.util.module_from_spec(spec)
sys.modules['promptmap'] = module
spec.loader.exec_module(module)

from promptmap.clients import base

metadata = ConfigParser()
metadata.read(ROOT / 'metadata.txt')
assert metadata['general']['qgisMaximumVersion'] == '4.99'
plugin = module.classFactory(None)
try:
    plugin.initGui()
    algorithms = list(plugin.provider.algorithms())
    assert len(algorithms) == 6
    flux3 = next(a for a in algorithms if a.name() == 'flux_3_editing')
    assert flux3.parameterDefinition('MODEL').options() == ['FLUX 3 Image', 'FLUX 3 Image Klein']
    openai = next(a for a in algorithms if a.name() == 'openai_image_editing')
    assert len(openai.parameterDefinition('MODEL').options()) == 2
    assert openai.parameterDefinition('QUALITY').defaultValue() == 1
    assert openai.parameterDefinition('COMPLEXITY').defaultValue() == 2
    canvas = QgsMapCanvas()
    crs = QgsCoordinateReferenceSystem('EPSG:3857')
    canvas.setDestinationCrs(crs)
    base.iface = SimpleNamespace(mapCanvas=lambda: canvas)
    extent = QgsRectangle(0, 0, 100, 100)
    with tempfile.TemporaryDirectory() as directory:
        path = str(Path(directory) / 'render.png')
        algorithms[0]._render_map(extent, 128, 128, path)
        image = QImage(path)
        assert not image.isNull()
        image.fill(QColor('white'))
        assert image.save(path)
        assert algorithms[0]._apply_watermark(path)
        tif = base.create_geotiff(path, extent, crs)
        gpkg = base.write_metadata_gpkg(tif, extent, crs, {'model': 'smoke test'})
        layer = QgsVectorLayer(gpkg, 'metadata', 'ogr')
        assert layer.isValid()
        assert layer.featureCount() == 1
        assert next(layer.getFeatures())['model'] == 'smoke test'
        del layer
    del canvas
    print(f'PASS: QGIS {Qgis.QGIS_VERSION}: registration, rendering, watermark, GeoTIFF, GeoPackage')
finally:
    plugin.unload()
    app.exitQgis()
