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

    def process_image(self, image_b64, prompt, safety, seed, ref_image_path, feedback) -> Dict[str, Any]:
        payload = {
            'input_image': image_b64,
            'prompt': prompt,
            'safety_tolerance': safety,
            'output_format': 'png'
        }
        
        if seed is not None: 
            payload['seed'] = seed
            
        if ref_image_path:
            try:
                with open(ref_image_path, 'rb') as f:
                    import base64
                    ref_b64 = base64.b64encode(f.read()).decode('ascii')
                    payload['input_image_2'] = ref_b64
                    if feedback: feedback.pushInfo(f"Added reference image: {ref_image_path}")
            except Exception as e:
                if feedback: feedback.reportError(f"Failed to read reference image: {e}")

        return self.post_and_poll(payload, feedback)


class Flux2EditingAlgorithm(BaseAIAlgorithm):
    """FLUX.2 Image Editing Algorithm."""
    
    MODEL = "MODEL"
    SAFETY = "SAFETY"
    SEED = "SEED"
    REF_IMAGE = "REF_IMAGE"
    
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
        
        self.addParameter(QgsProcessingParameterFile(
            self.REF_IMAGE, "Reference Image (Optional)", optional=True, behavior=QgsProcessingParameterFile.File, fileFilter="Images (*.png *.jpg *.jpeg)"
        ))

    def execute_api(self, api_key, input_path, prompt, aspect_ratio, parameters, context, feedback):
        model_idx = self.parameterAsEnum(parameters, self.MODEL, context)
        safety = self.parameterAsInt(parameters, self.SAFETY, context)
        seed = self.parameterAsInt(parameters, self.SEED, context) if parameters.get(self.SEED) else None
        ref_image_path = self.parameterAsString(parameters, self.REF_IMAGE, context)
        
        # Read main input image (map canvas)
        image_b64 = self.read_image_as_base64(input_path)
        
        client = Flux2APIClient(api_key, model_idx)
        return client.process_image(image_b64, prompt, safety, seed, ref_image_path, feedback)

    def name(self): return "flux_2_editing"
    def displayName(self): return "FLUX.2 Image Editing"
    def group(self): return "FLUX AI"
    def groupId(self): return "flux_ai"
    def createInstance(self): return Flux2EditingAlgorithm()
