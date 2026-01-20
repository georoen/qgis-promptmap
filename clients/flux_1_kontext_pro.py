"""
FLUX.1 Kontext [pro] Client.
"""

import time
import base64
import logging
from typing import Dict, Any, Optional

from qgis.core import QgsProcessingParameterNumber
from .base import BaseAIAlgorithm

class Flux1KontextProAPIClient:
    """Handles communication with FLUX.1 Kontext [pro] API."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.endpoint = "https://api.eu.bfl.ai/v1/flux-kontext-pro"
        self.poll_endpoint = "https://api.eu.bfl.ai/v1/get_result"
        self.logger = logging.getLogger("FluxKontext")

    def process_image(self, input_path, prompt, safety, aspect_ratio, seed, feedback) -> Dict[str, Any]:
        try: import requests
        except ImportError: return {"success": False, "error": "Python 'requests' library not found."}

        def log(msg):
            if feedback: feedback.pushInfo(msg)

        try:
            with open(input_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('ascii')
        except Exception as e:
            return {"success": False, "error": f"Failed to read input image: {e}"}

        payload = {
            'input_image': image_data,
            'prompt': prompt,
            'safety_tolerance': safety,
            'aspect_ratio': aspect_ratio,
            'output_format': 'png'
        }
        if seed is not None: payload['seed'] = seed

        log("🚀 Sending request to FLUX API...")
        try:
            response = requests.post(self.endpoint, json=payload, headers={'x-key': self.api_key}, timeout=60)
            response.raise_for_status()
            result = response.json()
            task_id = result.get("id")
            polling_url = result.get("polling_url") or f"{self.poll_endpoint}?id={task_id}"
            log(f"✅ Request accepted. Task ID: {task_id}")
        except Exception as e:
            return {"success": False, "error": f"API Request failed: {e}"}

        log("⏳ Waiting for processing...")
        start_time = time.time()
        while time.time() - start_time < 600:
            if feedback and feedback.isCanceled(): return {"success": False, "error": "Canceled."}
            try:
                poll_resp = requests.get(polling_url, headers={'x-key': self.api_key}, timeout=30)
                poll_data = poll_resp.json()
                status = poll_data.get("status")
                if status == "Ready":
                    log("✨ Processing complete!")
                    return {"success": True, "url": poll_data["result"]["sample"]}
                elif status == "Failed":
                    return {"success": False, "error": f"API Error: {poll_data.get('message')}"}
                time.sleep(1)
            except Exception: time.sleep(2)
        return {"success": False, "error": "Timeout."}


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
        
        client = Flux1KontextProAPIClient(api_key)
        return client.process_image(input_path, prompt, safety, aspect_ratio, seed, feedback)

    def name(self): return "flux_kontext"
    def displayName(self): return "FLUX.1 Kontext [pro]"
    def group(self): return "FLUX AI"
    def groupId(self): return "flux_ai"
    def createInstance(self): return Flux1KontextProAlgorithm()
