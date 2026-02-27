"""
QGIS Plugin Entry Point — PromptMap.
"""

import os
from qgis.core import QgsApplication, QgsProcessingProvider
from qgis.PyQt.QtGui import QIcon

from .clients.flux_1_kontext_pro import Flux1KontextProAlgorithm
from .clients.flux_1_1_ultra_pro import Flux1_1UltraProAlgorithm
from .clients.gemini_3_pro_image import Gemini3ProImageAlgorithm
from .clients.flux_2_editing import Flux2EditingAlgorithm


class PromptMapProvider(QgsProcessingProvider):
    """Processing provider for PromptMap AI algorithms."""

    def __init__(self):
        super().__init__()

    def loadAlgorithms(self):
        self.addAlgorithm(Flux1KontextProAlgorithm())
        self.addAlgorithm(Flux1_1UltraProAlgorithm())
        self.addAlgorithm(Gemini3ProImageAlgorithm())
        self.addAlgorithm(Flux2EditingAlgorithm())

    def id(self):
        return 'promptmap'

    def name(self):
        return 'PromptMap'

    def icon(self):
        return QIcon(os.path.join(os.path.dirname(__file__), 'icon.png'))


class PromptMapPlugin:
    """Main plugin class."""

    def __init__(self, iface):
        self.iface = iface
        self.provider = None

    def initGui(self):
        self.provider = PromptMapProvider()
        QgsApplication.processingRegistry().addProvider(self.provider)

    def unload(self):
        if self.provider:
            QgsApplication.processingRegistry().removeProvider(self.provider)
