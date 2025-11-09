from typing import Dict, Any
from qgis.core import (
    QgsProcessingParameterString,
    QgsProcessingParameterNumber,
    QgsProcessingParameterBoolean,
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
    SAFETY = "SAFETY"
    RAW_MODE = "RAW_MODE"
    IMAGE_PROMPT_STRENGTH = "IMAGE_PROMPT_STRENGTH"
    
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

        self.addParameter(
            QgsProcessingParameterNumber(
                self.SAFETY,
                "Safety Tolerance (0=strict, 6=permissive)",
                type=QgsProcessingParameterNumber.Integer,
                defaultValue=self.api_config.default_payload.get("safety_tolerance", 2),
                minValue=0,
                maxValue=6,
                optional=True
            )
        )

        self.addParameter(
            QgsProcessingParameterBoolean(
                self.RAW_MODE,
                "Enable Raw Mode (more natural aesthetics)",
                defaultValue=self.api_config.default_payload.get("raw", False)
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                self.IMAGE_PROMPT_STRENGTH,
                "Image Prompt Strength (0-1)",
                type=QgsProcessingParameterNumber.Double,
                defaultValue=self.api_config.default_payload.get("image_prompt_strength", 0.8),
                minValue=0.0,
                maxValue=1.0,
                optional=False
            )
        )

    def get_api_specifics(self, parameters: Dict[str, Any], context: QgsProcessingContext) -> (str, Dict[str, Any]):
        """Provides the specific configuration for the API call."""
        prompt = self.parameterAsString(parameters, self.PROMPT, context).strip()
        if not prompt:
            raise QgsProcessingException(f"{self.api_config.prompt_label} is required.")

        safety = self.parameterAsInt(parameters, self.SAFETY, context)
        raw_mode = self.parameterAsBoolean(parameters, self.RAW_MODE, context)
        img_strength = self.parameterAsDouble(parameters, self.IMAGE_PROMPT_STRENGTH, context)

        format_idx = self.parameterAsEnum(parameters, self.IMAGE_FORMAT, context)
        image_format = "png" if format_idx == 0 else "jpeg"
        filename = f"{self.api_config.id}_result.{image_format}"

        payload = {
            "prompt": prompt,
            "safety_tolerance": safety,
            "raw": raw_mode,
            "image_prompt_strength": img_strength,
        }
        
        return filename, payload
