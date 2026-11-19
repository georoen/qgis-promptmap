"""Gemini image editing through the Interactions API."""

import base64
import binascii

from qgis.core import QgsProcessingParameterEnum
from qgis.PyQt.QtCore import QBuffer, QIODevice
from qgis.PyQt.QtGui import QImage

from .base import BaseAIAlgorithm


# Keep Pro first so existing Processing workflows retain their model family.
MODELS = (
    ("Nano Banana Pro — Gemini 3 Pro Image", "gemini-3-pro-image", "2K"),
    ("Nano Banana 2.1 — Balanced", "gemini-nano-banana-2.1", "2K"),
    ("Nano Banana 2 — Gemini 3.1 Flash Image", "gemini-3.1-flash-image", "2K"),
    ("Nano Banana 2 Lite — Fast previews", "gemini-3.1-flash-lite-image", "1024px"),
    ("Nano Banana — Gemini 2.5 Flash Image (Legacy)", "gemini-2.5-flash-image", None),
)
STANDARD_RATIOS = {"1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"}


class Gemini3ProImageAPIClient:
    """Shared client; the original class name is retained for compatibility."""

    def __init__(self, api_key: str, model_idx: int = 0):
        self.api_key = api_key
        if not 0 <= model_idx < len(MODELS):
            raise ValueError("Invalid Gemini model selection.")
        self.model = MODELS[model_idx][1]
        self.image_size = MODELS[model_idx][2]
        self.endpoint = "https://generativelanguage.googleapis.com/v1beta/interactions"

    def process_image(self, image_b64, prompt, aspect_ratio, feedback):
        try:
            import requests
        except ImportError:
            return {"success": False, "error": "Python 'requests' library not found."}

        ratios = STANDARD_RATIOS
        if self.model in {"gemini-nano-banana-2.1", "gemini-3.1-flash-image"}:
            ratios = ratios | {"1:4", "4:1", "1:8", "8:1"}
        if aspect_ratio not in ratios:
            return {"success": False, "error": (
                f"Aspect ratio {aspect_ratio} is not supported by {self.model}. "
                "Choose the Square or Widescreen input framing preset."
            )}
        if feedback and feedback.isCanceled():
            return {"success": False, "error": "Canceled."}

        image_format = {"type": "image", "mime_type": "image/jpeg", "aspect_ratio": aspect_ratio}
        if self.image_size:
            image_format["image_size"] = self.image_size
        payload = {
            "model": self.model,
            "input": [
                {"type": "text", "text": prompt},
                {"type": "image", "mime_type": "image/png", "data": image_b64},
            ],
            "response_format": image_format,
            "store": False,
        }
        if feedback:
            feedback.pushInfo(f"Sending request to {self.model}...")
        try:
            response = requests.post(
                self.endpoint,
                json=payload,
                headers={
                    "x-goog-api-key": self.api_key,
                    "Content-Type": "application/json",
                    "Api-Revision": "2026-05-20",
                },
                timeout=120,
            )
            if response.status_code != 200:
                return {"success": False, "error": f"API Error {response.status_code}: {response.text}"}
            result = response.json()
            if result.get("status") != "completed":
                return {"success": False, "error": f"Gemini interaction did not complete: {result.get('status')}"}
            # Only final model output is usable; never save intermediate thought images.
            images = [
                block
                for step in result.get("steps", []) if step.get("type") == "model_output"
                for block in step.get("content", []) if block.get("type") == "image"
            ]
            if not images:
                return {"success": False, "error": "No image found in Gemini response (possibly blocked)."}
            generated = images[-1]
            mime_type = generated.get("mime_type")
            if mime_type not in {"image/jpeg", "image/png"}:
                return {"success": False, "error": "Gemini returned an unsupported image format."}
            image = QImage.fromData(
                base64.b64decode(generated["data"], validate=True),
                "JPEG" if mime_type == "image/jpeg" else "PNG",
            )
            if image.isNull():
                return {"success": False, "error": "Gemini returned unreadable image data."}
            # Interactions requires JPEG output; the shared local pipeline expects PNG.
            buffer = QBuffer()
            if not buffer.open(QIODevice.OpenModeFlag.WriteOnly) or not image.save(buffer, "PNG"):
                return {"success": False, "error": "Failed to convert Gemini output to PNG."}
            data = base64.b64encode(bytes(buffer.data())).decode('ascii')
            buffer.close()
            return {"success": True, "data": data, "model": self.model, "usage": result.get("usage")}
        except (KeyError, TypeError, AttributeError, ValueError, binascii.Error) as e:
            return {"success": False, "error": f"Invalid Gemini response: {e}"}
        except requests.RequestException as e:
            return {"success": False, "error": f"Request failed: {e}"}


class Gemini3ProImageAlgorithm(BaseAIAlgorithm):
    """Gemini image editing with selectable models."""

    MODEL = "MODEL"

    def initAlgorithm(self, config=None):
        super().initAlgorithm(config)
        self.addParameter(QgsProcessingParameterEnum(
            self.MODEL, "Gemini Model", options=[model[0] for model in MODELS], defaultValue=0,
        ))

    def execute_api(self, api_key, input_path, prompt, aspect_ratio, parameters, context, feedback):
        model_idx = self.parameterAsEnum(parameters, self.MODEL, context)
        if not 0 <= model_idx < len(MODELS):
            return {"success": False, "error": "Invalid Gemini model selection."}
        client = Gemini3ProImageAPIClient(api_key, model_idx)
        return client.process_image(self.read_image_as_base64(input_path), prompt, aspect_ratio, feedback)

    def _api_key_env_var(self): return "GEMINI_API_KEY"
    def name(self): return "gemini_3_image"
    def displayName(self): return "Gemini Image Editing (Nano Banana)"
    def group(self): return "Google Gemini API"
    def groupId(self): return "promptmap_gemini"
    def createInstance(self): return Gemini3ProImageAlgorithm()
