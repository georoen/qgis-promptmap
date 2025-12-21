from typing import Dict, Any
from qgis.core import (
    QgsProcessingParameterString,
    QgsProcessingContext,
    QgsProcessingException,
)
from ...base_ai_algorithm import BaseAiAlgorithm
from .config import GEMINI_3_IMAGE_CONFIG, ApiConfig
from .engine import GeminiEngine

class GeminiImageAlgorithm(BaseAiAlgorithm):
    """
    QGIS Processing Algorithm for Gemini 3 Pro Image generation.
    """
    PROMPT = "PROMPT"
    
    @property
    def api_config(self) -> ApiConfig:
        return GEMINI_3_IMAGE_CONFIG

    def createInstance(self):
        return GeminiImageAlgorithm()

    def name(self):
        return self.api_config.id

    def displayName(self):
        return self.api_config.display_name

    def shortHelpString(self):
        return self.api_config.short_help

    def group(self):
        return "Gemini AI Processing"

    def groupId(self):
        return "gemini_ai"

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

    def get_engine(self, api_key: str, log_path: str):
        return GeminiEngine(api_key=api_key, log_path=log_path)

    def get_api_specifics(self, parameters: Dict[str, Any], context: QgsProcessingContext) -> (str, Dict[str, Any]):
        """Provides the specific configuration for the API call."""
        prompt = self.parameterAsString(parameters, self.PROMPT, context).strip()
        if not prompt:
            raise QgsProcessingException(f"{self.api_config.prompt_label} is required.")
        
        filename = f"{self.api_config.id}_result.png"

        payload = {
            "prompt": prompt,
            # Add other Gemini specific params here if exposed in UI
        }
        
        return filename, payload