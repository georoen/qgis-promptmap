"""OpenAI Image API editing for the rendered QGIS canvas."""

import base64

from qgis.core import QgsProcessingParameterEnum
from qgis.PyQt.QtGui import QImage

from .base import BaseAIAlgorithm


MODELS = (
    ("GPT-Image-2.6 Sunburst (Detailed edits)", "gpt-image-2.6-sunburst"),
    ("GPT-Image-2.6 Flare (Fast iteration)", "gpt-image-2.6-flare"),
)
QUALITIES = ("low", "medium", "high")
COMPLEXITIES = ("low", "medium", "high")


class OpenAIImageAPIClient:
    def __init__(self, api_key: str, model_idx: int = 0):
        if not 0 <= model_idx < len(MODELS):
            raise ValueError("Invalid OpenAI model selection.")
        self.api_key = api_key
        self.model = MODELS[model_idx][1]
        self.endpoint = "https://api.openai.com/v1/images/edits"

    def process_image(self, input_path, prompt, quality, feedback, complexity="high"):
        try:
            import requests
        except ImportError:
            return {"success": False, "error": "Python 'requests' library not found."}
        if quality not in QUALITIES or complexity not in COMPLEXITIES:
            return {"success": False, "error": "Invalid OpenAI quality or complexity selection."}
        if feedback and feedback.isCanceled():
            return {"success": False, "error": "Canceled."}
        try:
            with open(input_path, 'rb') as image_file:
                image_data = image_file.read(50 * 1024 * 1024 + 1)
        except OSError as e:
            return {"success": False, "error": f"Cannot read input image: {e}"}
        if len(image_data) > 50 * 1024 * 1024:
            return {"success": False, "error": "OpenAI input image exceeds 50 MB."}
        image = QImage.fromData(image_data, "PNG")
        if image.isNull():
            return {"success": False, "error": "OpenAI input must be a readable PNG."}
        width, height = image.width(), image.height()
        # Never round dimensions: that would change the canvas framing or stretch its georeferencing.
        if (width % 16 or height % 16 or max(width, height) > 3840
                or not 655360 <= width * height <= 8294400 or not 1 / 3 <= width / height <= 3):
            return {"success": False, "error": (
                f"OpenAI does not support the rendered size {width}x{height}. "
                "Choose Square or Widescreen input framing. Custom dimensions must be multiples of 16, "
                "with 655,360–8,294,400 pixels, edges up to 3840 pixels and aspect ratio 1:3–3:1."
            )}
        if feedback:
            feedback.pushInfo(f"Sending request to {self.model} ({width}x{height}, quality {quality}, complexity {complexity})...")
        try:
            response = requests.post(
                self.endpoint,
                headers={"Authorization": f"Bearer {self.api_key}"},
                data={
                    "model": self.model, "prompt": prompt, "n": "1",
                    "size": f"{width}x{height}", "quality": quality, "complexity": complexity, "output_format": "png",
                },
                files={"image[]": ("input.png", image_data, "image/png")},
                timeout=180,
            )
            if feedback and feedback.isCanceled():
                return {"success": False, "error": "Canceled."}
            if response.status_code != 200:
                error = f"API Error {response.status_code}: {response.text}"
                return {"success": False, "error": error.replace(self.api_key, '[redacted]') if self.api_key else error}
            body = response.json()
            if body.get("output_format", "png") != "png":
                return {"success": False, "error": "OpenAI returned a non-PNG image."}
            data = body["data"][0]["b64_json"]
            output = QImage.fromData(base64.b64decode(data, validate=True), "PNG")
            if output.isNull():
                return {"success": False, "error": "OpenAI returned unreadable PNG data."}
            if output.width() * height != output.height() * width:
                return {"success": False, "error": "OpenAI returned a different aspect ratio; refusing distorted georeferencing."}
            return {"success": True, "data": data, "model": self.model, "usage": body.get("usage")}
        except requests.RequestException as e:
            error = f"OpenAI request failed: {e}"
            return {"success": False, "error": error.replace(self.api_key, '[redacted]') if self.api_key else error}
        except (KeyError, IndexError, TypeError, AttributeError, ValueError) as e:
            return {"success": False, "error": f"Invalid OpenAI response: {e}"}


class OpenAIImageAlgorithm(BaseAIAlgorithm):
    MODEL = "MODEL"
    QUALITY = "QUALITY"
    COMPLEXITY = "COMPLEXITY"

    def initAlgorithm(self, config=None):
        super().initAlgorithm(config)
        self.addParameter(QgsProcessingParameterEnum(
            self.MODEL, "OpenAI Model", options=[model[0] for model in MODELS], defaultValue=0,
        ))
        self.addParameter(QgsProcessingParameterEnum(
            self.QUALITY, "Quality (affects cost and latency)", options=list(QUALITIES), defaultValue=1,
        ))
        self.addParameter(QgsProcessingParameterEnum(
            self.COMPLEXITY, "Complexity (planning effort)", options=list(COMPLEXITIES), defaultValue=2,
        ))

    def execute_api(self, api_key, input_path, prompt, aspect_ratio, parameters, context, feedback):
        model_idx = self.parameterAsEnum(parameters, self.MODEL, context)
        quality_idx = self.parameterAsEnum(parameters, self.QUALITY, context)
        complexity_idx = self.parameterAsEnum(parameters, self.COMPLEXITY, context)
        if (not 0 <= model_idx < len(MODELS) or not 0 <= quality_idx < len(QUALITIES)
                or not 0 <= complexity_idx < len(COMPLEXITIES)):
            return {"success": False, "error": "Invalid OpenAI model, quality or complexity selection."}
        client = OpenAIImageAPIClient(api_key, model_idx)
        return client.process_image(input_path, prompt, QUALITIES[quality_idx], feedback,
                                    complexity=COMPLEXITIES[complexity_idx])

    def _api_key_env_var(self): return "OPENAI_API_KEY"
    def name(self): return "openai_image_editing"
    def displayName(self): return "OpenAI Image Editing"
    def group(self): return "OpenAI API"
    def groupId(self): return "promptmap_openai"
    def createInstance(self): return OpenAIImageAlgorithm()
