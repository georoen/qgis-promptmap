from typing import Dict, Any, NamedTuple

DEFAULT_PROMPT = (
    "You are an expert in remote sensing and well trained in interpreting earth observation data. "
    "Create a clean, stylized map from the provided reference image. "
    "Represent buildings as solid black shapes with sharp edges. "
    "Trace roads and paths as thin white lines. "
    "Identify green spaces like parks and vegetation, and represent them as solid green areas. "
    "Open water bodies are represented as solid blue areas. "
    "Open soil should appear in a light yellowish tone. "
    "The final map must be a high-contrast, minimalist, and flat graphic, suitable for architectural "
    "diagrams or site analysis."
)

class ApiConfig(NamedTuple):
    """
    Data structure to hold all API-specific configurations.
    
    This allows algorithms to be defined declaratively, simply by pointing
    to one of these configurations.
    """
    # Unique identifier for the API
    id: str
    
    # UI-specific strings
    display_name: str
    short_help: str
    
    # API endpoint and payload details
    endpoint_path: str
    # The key used for the main image data in the payload (e.g., "image_prompt" or "input_image")
    image_payload_key: str
    
    # Default and specific parameters for the payload
    default_payload: Dict[str, Any]
    
    # UI parameter definitions
    prompt_label: str
    prompt_default: str

# --- API Definitions ---

FLUX_ULTRA_CONFIG = ApiConfig(
    id="flux_ultra",
    display_name="FLUX 1.1 [pro] Ultra",
    short_help="Generates an artistic image based on a style prompt using the FLUX 1.1 [pro] Ultra model.",
    endpoint_path="/v1/flux-pro-1.1-ultra",
    image_payload_key="image_prompt",
    default_payload={
        "image_prompt_strength": 0.8,
        "aspect_ratio": "1:1",
        "safety_tolerance": 2
    },
    prompt_label="Prompt",
    prompt_default=DEFAULT_PROMPT
)

FLUX_KONTEXT_CONFIG = ApiConfig(
    id="flux_kontext",
    display_name="FLUX.1 Kontext [pro]",
    short_help="Edits the map image based on an instruction prompt using the FLUX.1 Kontext [pro] model.",
    endpoint_path="/v1/flux-kontext-pro",
    image_payload_key="input_image",
    default_payload={
        "aspect_ratio": "1:1",
        "safety_tolerance": 2
    },
    prompt_label="Prompt",
    prompt_default=DEFAULT_PROMPT
)

# A dictionary to easily access configurations by their ID
API_CONFIGS: Dict[str, ApiConfig] = {
    "flux_ultra": FLUX_ULTRA_CONFIG,
    "flux_kontext": FLUX_KONTEXT_CONFIG,
}