"""
FLUX 1.1 [pro] Ultra Client.
"""

from typing import Dict, Any, Optional
from qgis.core import QgsProcessingParameterNumber
from .base import BaseAIAlgorithm
from .bfl_base import BFLAPIClient

class Flux1_1UltraProAPIClient(BFLAPIClient):
    """Handles communication with FLUX 1.1 [pro] Ultra API."""
    
    def __init__(self, api_key: str):
        super().__init__(api_key, "https://api.eu.bfl.ai/v1/flux-pro-1.1-ultra")

    def process_image(self, image_b64, prompt, strength, safety, aspect_ratio, seed, feedback) -> Dict[str, Any]:
        payload = {
            'image_prompt': image_b64,
            'prompt': prompt,
            'image_prompt_strength': strength,
            'safety_tolerance': safety,
            'aspect_ratio': aspect_ratio,
            'output_format': 'png'
        }
        if seed is not None: payload['seed'] = seed

        return self.post_and_poll(payload, feedback)


class Flux1_1UltraProAlgorithm(BaseAIAlgorithm):
    """FLUX 1.1 [pro] Ultra Algorithm."""
    
    STRENGTH = "STRENGTH"
    SAFETY = "SAFETY"
    SEED = "SEED"

    def initAlgorithm(self, config=None):
        super().initAlgorithm(config)
        self.addParameter(QgsProcessingParameterNumber(
            self.STRENGTH, "Image Strength (0.1-1.0)", type=QgsProcessingParameterNumber.Double, defaultValue=0.8, minValue=0.1, maxValue=1.0
        ))
        self.addParameter(QgsProcessingParameterNumber(
            self.SAFETY, "Safety Tolerance", type=QgsProcessingParameterNumber.Integer, defaultValue=2, minValue=0, maxValue=6
        ))
        self.addParameter(QgsProcessingParameterNumber(self.SEED, "Seed", type=QgsProcessingParameterNumber.Integer, optional=True))

    def execute_api(self, api_key, input_path, prompt, aspect_ratio, parameters, context, feedback):
        strength = self.parameterAsDouble(parameters, self.STRENGTH, context)
        safety = self.parameterAsInt(parameters, self.SAFETY, context)
        seed = self.parameterAsInt(parameters, self.SEED, context) if parameters.get(self.SEED) else None
        
        image_b64 = self.read_image_as_base64(input_path)
        
        client = Flux1_1UltraProAPIClient(api_key)
        return client.process_image(image_b64, prompt, strength, safety, aspect_ratio, seed, feedback)

    def name(self): return "flux_ultra"
    def displayName(self): return "FLUX 1.1 [pro] Ultra"
    def group(self): return "FLUX AI"
    def groupId(self): return "flux_ai"
    def createInstance(self): return Flux1_1UltraProAlgorithm()
