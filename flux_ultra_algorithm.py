from typing import Dict, Any
from qgis.core import (
    QgsProcessingParameterString,
    QgsProcessingContext,
    QgsProcessingException,
)
from .flux_base_algorithm import BaseAiAlgorithm
from .flux_api_config import FLUX_ULTRA_CONFIG, ApiConfig


class FluxStylizeAlgorithm(BaseAiAlgorithm):
    """
    QGIS Processing Algorithm for FLUX 1.1 [pro] Ultra image stylization.
    This algorithm is defined by the FLUX_ULTRA_CONFIG.
    """
    PROMPT = "PROMPT"
    
    @property
    def api_config(self) -> ApiConfig:
        return FLUX_ULTRA_CONFIG

    def createInstance(self):
        return FluxStylizeAlgorithm()

    def name(self):
        return self.api_config.id

    def displayName(self):
        return self.api_config.display_name

    def shortHelpString(self):
        return self.api_config.short_help

    def initAlgorithm(self, config=None):
        super().initAlgorithm(config)
        self.addParameter(
            QgsProcessingParameterString(
                self.PROMPT,
                self.api_config.prompt_label,
                defaultValue=self.api_config.prompt_default,
                multiLine=True,
                optional=False
            )
        )

    def get_api_specifics(self, parameters: Dict[str, Any], context: QgsProcessingContext) -> (str, Dict[str, Any]):
        """Provides the specific configuration for the API call."""
        prompt = self.parameterAsString(parameters, self.PROMPT, context).strip()
        if not prompt:
            raise QgsProcessingException(f"{self.api_config.prompt_label} is required.")

        format_idx = self.parameterAsEnum(parameters, self.IMAGE_FORMAT, context)
        image_format = "png" if format_idx == 0 else "jpeg"
        filename = f"{self.api_config.id}_result.{image_format}"

        payload = {"prompt": prompt}
        # In the future, other UI parameters like 'image_prompt_strength' would be added here.
        
        return filename, payload