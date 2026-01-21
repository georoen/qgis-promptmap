"""
FLUX.1 Kontext [pro] Client.
"""

from typing import Dict, Any, Optional
from qgis.core import QgsProcessingParameterNumber
from .base import BaseAIAlgorithm
from .bfl_base import BFLAPIClient

class Flux1KontextProAPIClient(BFLAPIClient):
    """Handles communication with FLUX.1 Kontext [pro] API."""
    
    def __init__(self, api_key: str):
        super().__init__(
            api_key, 
            "https://api.eu.bfl.ai/v1/flux-kontext-pro"
        )

    def process_image(self, image_b64, prompt, safety, aspect_ratio, seed, feedback) -> Dict[str, Any]:
        payload = {
            'input_image': image_b64,
            'prompt': prompt,
            'safety_tolerance': safety,
            'aspect_ratio': aspect_ratio,
            'output_format': 'png'
        }
        if seed is not None: payload['seed'] = seed

        return self.post_and_poll(payload, feedback)


class Flux1KontextProAlgorithm(BaseAIAlgorithm):
    """FLUX.1 Kontext [pro] Algorithm."""
    
    SAFETY = "SAFETY"
    SEED = "SEED"

    def initAlgorithm(self, config=None):
        super().initAlgorithm(config)
        self.addParameter(QgsProcessingParameterNumber(
            self.SAFETY, "Safety Tolerance", type=QgsProcessingParameterNumber.Integer, defaultValue=2, minValue=0, maxValue=6
        ))
        self.addParameter(QgsProcessingParameterNumber(self.SEED, "Seed", type=QgsProcessingParameterNumber.Integer, optional=True))

    def execute_api(self, api_key, input_path, prompt, aspect_ratio, parameters, context, feedback):
        safety = self.parameterAsInt(parameters, self.SAFETY, context)
        seed = self.parameterAsInt(parameters, self.SEED, context) if parameters.get(self.SEED) else None
        
        # Read image using base class helper
        image_b64 = self.read_image_as_base64(input_path)
        
        client = Flux1KontextProAPIClient(api_key)
        return client.process_image(image_b64, prompt, safety, aspect_ratio, seed, feedback)

    def name(self): return "flux_kontext"
    def displayName(self): return "FLUX.1 Kontext [pro]"
    def group(self): return "FLUX AI"
    def groupId(self): return "flux_ai"
    def createInstance(self): return Flux1KontextProAlgorithm()
