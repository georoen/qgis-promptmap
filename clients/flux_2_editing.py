"""
FLUX.2 Image Editing Client.
"""

from typing import Dict, Any, Optional
from qgis.core import (
    QgsProcessingParameterNumber,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFile
)
from .base import BaseAIAlgorithm
from .bfl_base import BFLAPIClient

class Flux2APIClient(BFLAPIClient):
    """Handles communication with FLUX.2 API."""
    
    ENDPOINTS = {
        0: "https://api.eu.bfl.ai/v1/flux-2-pro",
        1: "https://api.eu.bfl.ai/v1/flux-2-max",
        2: "https://api.eu.bfl.ai/v1/flux-2-flex",
        3: "https://api.eu.bfl.ai/v1/flux-2-klein-4b",
        4: "https://api.eu.bfl.ai/v1/flux-2-klein-9b"
    }

    def __init__(self, api_key: str, model_idx: int):
        endpoint = self.ENDPOINTS.get(model_idx, self.ENDPOINTS[0])
        super().__init__(api_key, endpoint)

    def process_image(self, image_b64, prompt, safety, seed, feedback) -> Dict[str, Any]:
        payload = {
            'input_image': image_b64,
            'prompt': prompt,
            'safety_tolerance': safety,
            'output_format': 'png'
        }
        
        if seed is not None: 
            payload['seed'] = seed
            
        return self.post_and_poll(payload, feedback)


class Flux2EditingAlgorithm(BaseAIAlgorithm):
    """FLUX.2 Image Editing Algorithm."""
    
    MODEL = "MODEL"
    SAFETY = "SAFETY"
    SEED = "SEED"
    
    MODEL_OPTIONS = [
        "FLUX.2 [pro] (Balanced)",
        "FLUX.2 [max] (Highest Quality)",
        "FLUX.2 [flex] (Control)",
        "FLUX.2 [klein] 4B (Fastest)",
        "FLUX.2 [klein] 9B (Fast/Quality)"
    ]

    def initAlgorithm(self, config=None):
        super().initAlgorithm(config)
        
        self.addParameter(QgsProcessingParameterEnum(
            self.MODEL, "Model Variant", options=self.MODEL_OPTIONS, defaultValue=0
        ))
        
        self.addParameter(QgsProcessingParameterNumber(
            self.SAFETY, "Safety Tolerance", type=QgsProcessingParameterNumber.Integer, defaultValue=2, minValue=0, maxValue=5
        ))
        
        self.addParameter(QgsProcessingParameterNumber(
            self.SEED, "Seed", type=QgsProcessingParameterNumber.Integer, optional=True
        ))

    def execute_api(self, api_key, input_path, prompt, aspect_ratio, parameters, context, feedback):
        model_idx = self.parameterAsEnum(parameters, self.MODEL, context)
        safety = self.parameterAsInt(parameters, self.SAFETY, context)
        seed = self.parameterAsInt(parameters, self.SEED, context) if parameters.get(self.SEED) else None
        
        # Read main input image (map canvas)
        image_b64 = self.read_image_as_base64(input_path)
        
        client = Flux2APIClient(api_key, model_idx)
        return client.process_image(image_b64, prompt, safety, seed, feedback)

    def name(self): return "flux_2_editing"
    def displayName(self): return "FLUX.2 Image Editing"
    def group(self): return "Black Forest Labs API"
    def groupId(self): return "promptmap_bfl"
    def createInstance(self): return Flux2EditingAlgorithm()
