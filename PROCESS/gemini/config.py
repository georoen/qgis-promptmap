from typing import Dict, Any, NamedTuple

DEFAULT_PROMPT = (
    "Generate a visualization of the current map view. "
    "Style it as a high-contrast, minimalist architectural diagram. "
    "Buildings should be solid black, roads thin white lines, vegetation green, water blue."
)

class ApiConfig(NamedTuple):
    id: str
    display_name: str
    short_help: str
    endpoint_path: str
    default_payload: Dict[str, Any]
    prompt_label: str
    prompt_default: str

GEMINI_3_IMAGE_CONFIG = ApiConfig(
    id="gemini_3_image",
    display_name="Gemini 3 Pro Image",
    short_help="Generates a map visualization using Google's Gemini 3 Pro Image model.",
    endpoint_path="/v1beta/models/gemini-3-pro-image-preview:generateContent",
    default_payload={
        "generationConfig": {
            "imageConfig": {
                "aspectRatio": "1:1",
                "imageSize": "2K" # Or 4K
            }
        }
    },
    prompt_label="Prompt",
    prompt_default=DEFAULT_PROMPT
)

API_CONFIGS: Dict[str, ApiConfig] = {
    "gemini_3_image": GEMINI_3_IMAGE_CONFIG,
}