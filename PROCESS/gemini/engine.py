import os
import json
import base64
import logging
import copy
from typing import Dict, Any, Optional

from .config import ApiConfig

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
except ImportError:
    requests = None

class GeminiEngine:
    """
    Handles communication with the Google Gemini 3 API.
    """

    def __init__(self, api_key: str, log_path: Optional[str] = None, endpoint: str = "https://generativelanguage.googleapis.com"):
        if not api_key:
            raise ValueError("A valid API Key is required.")

        self.api_key = api_key
        self.endpoint = endpoint.rstrip('/')
        self.log_path = log_path
        
        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

        if not requests:
            raise ImportError("The 'requests' library is required for API communication.")
        
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            backoff_factor=1
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def process_workflow(
        self, input_path: str, prompt: str, seed: Optional[int],
        image_format: str, api_config: ApiConfig, extra_params: Dict[str, Any],
        output_path: str
    ) -> Dict[str, Any]:
        """
        Executes the full Gemini workflow: Request -> Response -> Save Image.
        """
        
        # 1. Read Input Image
        with open(input_path, 'rb') as f:
            image_data = base64.b64encode(f.read()).decode('ascii')
            
        # 2. Build Payload
        # Gemini 3 structure:
        # {
        #   "contents": [{
        #     "parts": [
        #       { "text": prompt },
        #       { "inlineData": { "mimeType": "image/png", "data": ... } }
        #     ]
        #   }],
        #   "generationConfig": { ... }
        # }
        
        mime_type = "image/png" # Input is always PNG from QGIS render
        
        contents = {
            "parts": [
                { "text": prompt },
                {
                    "inlineData": {
                        "mimeType": mime_type,
                        "data": image_data
                    }
                }
            ]
        }
        
        payload = {
            "contents": [contents],
            "generationConfig": api_config.default_payload.get("generationConfig", {}).copy()
        }
        
        # Merge extra params into generationConfig if present
        if "generationConfig" in extra_params:
            payload["generationConfig"].update(extra_params["generationConfig"])
        
        # Handle Aspect Ratio mapping if needed (Gemini expects "16:9", "1:1", etc.)
        if "aspect_ratio" in extra_params:
             if "imageConfig" not in payload["generationConfig"]:
                 payload["generationConfig"]["imageConfig"] = {}
             payload["generationConfig"]["imageConfig"]["aspectRatio"] = extra_params["aspect_ratio"]

        full_url = f"{self.endpoint}{api_config.endpoint_path}"
        headers = {
            "x-goog-api-key": self.api_key,
            "Content-Type": "application/json"
        }

        self.logger.info(f"Sending request to {full_url}")
        
        # Log payload (debug)
        debug_payload = copy.deepcopy(payload)
        # Truncate base64 for logging
        try:
            debug_payload["contents"][0]["parts"][1]["inlineData"]["data"] = "<base64_data>"
        except (KeyError, IndexError):
            pass # Structure might be different, ignore
            
        self.logger.info(f"Payload: {json.dumps(debug_payload)}")

        response = self.session.post(full_url, json=payload, headers=headers, timeout=120)
        
        if response.status_code != 200:
            self.logger.error(f"Gemini API Error {response.status_code}: {response.text}")
            return {"success": False, "error": f"API Error {response.status_code}: {response.text}"}

        result = response.json()
        
        # 3. Parse Response
        # Response structure:
        # {
        #   "candidates": [
        #     {
        #       "content": {
        #         "parts": [
        #           { "inlineData": { "mimeType": "image/jpeg", "data": "..." } }
        #         ]
        #       }
        #     }
        #   ]
        # }
        
        try:
            candidate = result["candidates"][0]
            parts = candidate["content"]["parts"]
            image_part = next((p for p in parts if "inlineData" in p), None)
            
            if not image_part:
                return {"success": False, "error": "No image data found in response."}
                
            b64_data = image_part["inlineData"]["data"]
            img_bytes = base64.b64decode(b64_data)
            
            with open(output_path, 'wb') as f:
                f.write(img_bytes)
                
            self.logger.info(f"Image saved to {output_path}")
            return {"success": True, "output_path": output_path}
            
        except (KeyError, IndexError, ValueError) as e:
            self.logger.error(f"Failed to parse Gemini response: {e}")
            return {"success": False, "error": f"Response parsing failed: {e}"}
