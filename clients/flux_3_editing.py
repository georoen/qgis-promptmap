"""FLUX 3 Image and Klein canvas editing."""

import base64

from qgis.core import QgsProcessingParameterEnum
from qgis.PyQt.QtCore import QBuffer, QIODevice
from qgis.PyQt.QtGui import QImage, QImageReader

from .base import BaseAIAlgorithm
from .bfl_base import BFLAPIClient


MODELS = (
    ("FLUX 3 Image", "flux-3-image"),
    ("FLUX 3 Image Klein", "flux-3-image-klein"),
)


class Flux3APIClient(BFLAPIClient):
    def __init__(self, api_key, model_idx):
        self.model = MODELS[model_idx][1]
        super().__init__(api_key, f"https://api.eu.bfl.ai/v1/{self.model}")

    def process_image(self, input_path, prompt, feedback):
        reader = QImageReader(input_path, b"png")
        size = reader.size()
        width, height = size.width(), size.height()
        klein = self.model == "flux-3-image-klein"
        min_edge, max_pixels = (64, 16_822_272) if klein else (256, 4_194_304)
        if not (min_edge <= min(width, height) and max(width, height) <= 6256
                and width * height <= max_pixels):
            return {"success": False, "error": (
                f"Invalid render size for {self.model}: {width}×{height}. "
                "Use the Square or Widescreen preset."
            )}
        try:
            with open(input_path, "rb") as source:
                image_b64 = base64.b64encode(source.read()).decode("ascii")
        except OSError:
            return {"success": False, "error": "Cannot read the rendered canvas image."}
        # Exact dimensions preserve the framing instead of letting the prompt pick a ratio.
        payload = {"prompt": prompt, "images": [image_b64], "width": width, "height": height}
        if klein:
            payload["output_format"] = "png"
        else:
            payload["grounding"] = False
        result = self.post_and_poll(payload, feedback)
        if not result["success"]:
            return result
        if feedback and feedback.isCanceled():
            return {"success": False, "error": "Canceled."}

        # Download the signed result without sending the API key. Image does not accept output_format.
        import requests

        try:
            if "url" in result:
                response = requests.get(result["url"], timeout=60, allow_redirects=False)
                if response.status_code != 200:
                    return {"success": False, "error": f"BFL image download failed (HTTP {response.status_code})."}
                image_bytes = response.content
            else:
                image_bytes = base64.b64decode(result["data"], validate=True)
        except (requests.RequestException, ValueError):
            return {"success": False, "error": "Could not read the BFL result image."}

        image = QImage.fromData(image_bytes)
        if image.isNull():
            return {"success": False, "error": "BFL returned an unreadable image."}
        if image.width() * height != image.height() * width:
            return {"success": False, "error": "BFL returned a different aspect ratio; refusing distorted georeferencing."}
        if not image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
            buffer = QBuffer()
            if not buffer.open(QIODevice.OpenModeFlag.WriteOnly) or not image.save(buffer, "PNG"):
                return {"success": False, "error": "Could not convert the BFL result to PNG."}
            image_bytes = bytes(buffer.data())
        result.pop("url", None)
        return {**result, "data": base64.b64encode(image_bytes).decode("ascii"), "model": self.model}


class Flux3EditingAlgorithm(BaseAIAlgorithm):
    MODEL = "MODEL"

    def initAlgorithm(self, config=None):
        super().initAlgorithm(config)
        self.addParameter(QgsProcessingParameterEnum(
            self.MODEL, "Model", options=[label for label, _ in MODELS], defaultValue=0,
        ))

    def execute_api(self, api_key, input_path, prompt, aspect_ratio, parameters, context, feedback):
        model_idx = self.parameterAsEnum(parameters, self.MODEL, context)
        if not 0 <= model_idx < len(MODELS):
            return {"success": False, "error": "Invalid FLUX 3 model selection."}
        return Flux3APIClient(api_key, model_idx).process_image(input_path, prompt, feedback)

    def _api_key_env_var(self): return "BFL_API_KEY"
    def name(self): return "flux_3_editing"
    def displayName(self): return "FLUX 3 Image Editing"
    def group(self): return "Black Forest Labs API"
    def groupId(self): return "promptmap_bfl"
    def createInstance(self): return Flux3EditingAlgorithm()
