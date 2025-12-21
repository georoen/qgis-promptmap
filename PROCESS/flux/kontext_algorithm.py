from typing import Dict, Any
from qgis.core import (
    QgsProcessingParameterString,
    QgsProcessingParameterNumber,
    QgsProcessingContext,
    QgsProcessingException,
)
from ...base_ai_algorithm import BaseAiAlgorithm
from .config import FLUX_KONTEXT_CONFIG, ApiConfig


class FluxKontextAlgorithm(BaseAiAlgorithm):
    """
    QGIS Processing Algorithm for FLUX.1 Kontext [pro] image editing.
    This algorithm is defined by the FLUX_KONTEXT_CONFIG.
    """
    PROMPT = "PROMPT"
    SAFETY = "SAFETY"
    
    @property
    def api_config(self) -> ApiConfig:
        return FLUX_KONTEXT_CONFIG

    def createInstance(self):
        return FluxKontextAlgorithm()

    def name(self):
        return self.api_config.id

    def displayName(self):
        return self.api_config.display_name

    def shortHelpString(self):
        return self.api_config.short_help

    def initAlgorithm(self, config=None):
        super().initAlgorithm(config)
        prompt_param = QgsProcessingParameterString(
            self.PROMPT,
            self.api_config.prompt_label,
            defaultValue=self.api_config.prompt_default,
            multiLine=True,
            optional=False
        )
        self.addParameter(prompt_param)

        safety_param = QgsProcessingParameterNumber(
            self.SAFETY,
            "Safety Tolerance (0=strict, 6=permissive)",
            type=QgsProcessingParameterNumber.Integer,
            defaultValue=self.api_config.default_payload.get("safety_tolerance", 2),
            minValue=0,
            maxValue=6,
            optional=True
        )
        self._mark_advanced(safety_param)
        self.addParameter(safety_param)

    def get_api_specifics(self, parameters: Dict[str, Any], context: QgsProcessingContext) -> (str, Dict[str, Any]):
        """Provides the specific configuration for the API call."""
        prompt = self.parameterAsString(parameters, self.PROMPT, context).strip()
        if not prompt:
            raise QgsProcessingException(f"{self.api_config.prompt_label} is required.")
        
        safety = self.parameterAsInt(parameters, self.SAFETY, context)

        filename = f"{self.api_config.id}_result.png"

        payload = {
            "prompt": prompt,
            "safety_tolerance": safety,
        }
        
        return filename, payload