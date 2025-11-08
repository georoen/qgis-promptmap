from qgis.core import QgsProcessingProvider, QgsApplication
from .flux_processing_algorithm import FluxStylizeAlgorithm


class FluxProvider(QgsProcessingProvider):
    """FLUX processing provider for QGIS."""

    def id(self):
        return "flux"

    def name(self):
        return "FLUX Stylize"

    def icon(self):
        return QgsApplication.getThemeIcon("/mActionRasterize.svg")

    def loadAlgorithms(self):
        self.addAlgorithm(FluxStylizeAlgorithm())


def classFactory(iface):
    return FluxPlugin(iface)


class FluxPlugin:
    """Main plugin class."""

    def __init__(self, iface):
        self.iface = iface
        self.provider = None

    def initProcessing(self):
        self.provider = FluxProvider()
        QgsApplication.processingRegistry().addProvider(self.provider)

    def initGui(self):
        self.initProcessing()

    def unload(self):
        if self.provider:
            QgsApplication.processingRegistry().removeProvider(self.provider)