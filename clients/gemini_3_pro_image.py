"""
Gemini 3 Pro Image Client.
"""

import logging
from typing import Dict, Any, Optional

from .base import BaseAIAlgorithm

class Gemini3ProImageAPIClient:
    """Handles communication with Google Gemini 3 Pro Image API."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.endpoint = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3-pro-image-preview:generateContent"

    def process_image(self, image_b64, prompt, aspect_ratio, feedback) -> Dict[str, Any]:
        try: import requests
        except ImportError: return {"success": False, "error": "Python 'requests' library not found."}

        def log(msg):
            if feedback: feedback.pushInfo(msg)

        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {
                        "inlineData": {
                            "mimeType": "image/png",
                            "data": image_b64
                        }
                    }
                ]
            }],
            "generationConfig": {
                "imageConfig": {
                    "aspectRatio": aspect_ratio,
                    "imageSize": "2K"
                }
            }
        }

        log("🚀 Sending request to Gemini API...")
        try:
            response = requests.post(
                self.endpoint,
                json=payload,
                headers={'x-goog-api-key': self.api_key, 'Content-Type': 'application/json'},
                timeout=120
            )
            
            if response.status_code != 200:
                return {"success": False, "error": f"API Error {response.status_code}: {response.text}"}
            
            result = response.json()
            try:
                candidate = result["candidates"][0]
                parts = candidate["content"]["parts"]
                image_part = next((p for p in parts if "inlineData" in p), None)
                
                if not image_part: return {"success": False, "error": "No image found in response."}
                
                return {"success": True, "data": image_part["inlineData"]["data"]}
                
            except (KeyError, IndexError) as e:
                return {"success": False, "error": f"Failed to parse response: {e}"}
            
        except Exception as e:
            return {"success": False, "error": f"Request failed: {e}"}


class Gemini3ProImageAlgorithm(BaseAIAlgorithm):
    """Gemini 3 Pro Image Algorithm."""
    
    def execute_api(self, api_key, input_path, prompt, aspect_ratio, parameters, context, feedback):
        image_b64 = self.read_image_as_base64(input_path)
        client = Gemini3ProImageAPIClient(api_key)
        return client.process_image(image_b64, prompt, aspect_ratio, feedback)

    def name(self): return "gemini_3_image"
    def displayName(self): return "Gemini 3 Pro Image"
    def group(self): return "Google Gemini API"
    def groupId(self): return "promptmap_gemini"
    def createInstance(self): return Gemini3ProImageAlgorithm()
