import os
import time
import json
import hashlib
import base64
import logging
from typing import Dict, Any, Optional

from .config import ApiConfig

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
except ImportError:
    requests = None

class FluxEngine:
    """
    Handles communication with the FLUX AI API.
    """

    def __init__(self, api_key: str, log_path: Optional[str] = None, endpoint: str = "https://api.eu.bfl.ai"):
        if not api_key or len(api_key.strip()) < 10:
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

        if api_key.lower() == 'demo':
            os.environ['FLUX_DEMO_MODE'] = 'true'
            self.logger.info("🎯 DEMO MODE explicitly enabled.")
        else:
            os.environ['FLUX_DEMO_MODE'] = 'false'
            self.logger.info("🚀 LIVE API MODE enabled.")
        
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

    def send_api_request(
        self, input_path: str, prompt: str, seed: Optional[int],
        image_format: str, api_config: ApiConfig, extra_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Builds the payload and sends the initial request to the specified API."""
        with open(input_path, 'rb') as f:
            image_data = base64.b64encode(f.read()).decode('ascii')

        # Start with the default payload from the config
        payload = api_config.default_payload.copy()
        
        # Add dynamic values
        payload['prompt'] = prompt
        payload[api_config.image_payload_key] = image_data
        payload['output_format'] = image_format.lower()
        
        # Merge any additional, user-defined parameters
        payload.update(extra_params)

        if seed is not None:
            payload["seed"] = seed

        headers = {"accept": "application/json", "x-key": self.api_key, "Content-Type": "application/json"}
        
        if os.getenv('FLUX_DEMO_MODE', 'false').lower() == 'true':
            self.logger.info("DEMO MODE: Simulating API request.")
            return self._simulate_flux_request()
        
        full_url = f"{self.endpoint}{api_config.endpoint_path}"
        self.logger.info(f"Sending request to {full_url} for API '{api_config.id}' with keys: {list(payload.keys())}")
        
        response = self.session.post(full_url, json=payload, headers=headers, timeout=60)
        response.raise_for_status()
        result = response.json()
        
        self.logger.info(f"API request successful. ID: {result.get('id', 'N/A')}")
        return {"success": True, "polling_url": result["polling_url"], "id": result["id"]}

    def _simulate_flux_request(self) -> Dict[str, Any]:
        """Returns a mock response for demo mode."""
        return {
            "success": True,
            "polling_url": f"{self.endpoint}/v1/get_result?id=demo_12345",
            "id": "demo_12345"
        }

    def poll_until_ready(self, polling_url: str, timeout_s: int = 600) -> Dict[str, Any]:
        """Polls the API result URL until the status is Ready, Failed, or a timeout occurs."""
        start_time = time.time()
        poll_interval = 0.5
        headers = {"accept": "application/json", "x-key": self.api_key}

        is_demo = os.getenv('FLUX_DEMO_MODE', 'false').lower() == 'true'
        self.logger.info(f"Polling ({'DEMO' if is_demo else 'LIVE'}) | Timeout: {timeout_s}s")

        while time.time() - start_time < timeout_s:
            if is_demo:
                if time.time() - start_time > 2:
                    return {"status": "Ready", "delivery_url": "https://delivery-eu1.bfl.ai/demo/sample.png"}
                time.sleep(poll_interval)
                continue

            response = self.session.get(polling_url, headers=headers, timeout=30)
            if response.status_code != 200:
                self.logger.warning(f"Polling received status {response.status_code}. Retrying...")
                time.sleep(poll_interval * 2)
                continue

            result = response.json()
            status = result.get("status", "UNKNOWN")
            self.logger.info(f"Current API Status: '{status}'")

            if status == "Ready":
                return {"status": "Ready", "delivery_url": result["result"]["sample"]}
            if status in ["Error", "Failed"]:
                return {"status": "Failed", "error": result.get("message", "Unknown API error")}
            
            time.sleep(poll_interval)

        raise TimeoutError(f"Polling timed out after {timeout_s} seconds.")

    def download_stylized_image(self, delivery_url: str, out_path: str, width: int, height: int, image_format: str):
        """Downloads the final image from the delivery URL."""
        if os.getenv('FLUX_DEMO_MODE', 'false').lower() == 'true':
            self.logger.info("DEMO MODE: Creating demo stylized image.")
            self._create_demo_stylized_image(out_path, width, height, image_format)
            return

        response = self.session.get(delivery_url, timeout=60)
        response.raise_for_status()
        
        with open(out_path, 'wb') as f:
            f.write(response.content)
        
        self.logger.info(f"Image successfully downloaded to {out_path}")
        self._validate_and_resize_if_needed(out_path, width, height, image_format)

    def _create_demo_stylized_image(self, out_path: str, width: int, height: int, image_format: str):
        """Creates a placeholder stylized image for demo mode."""
        try:
            from PIL import Image, ImageDraw, ImageFilter
            import random
            img = Image.new('RGB', (width, height), "white")
            draw = ImageDraw.Draw(img)
            for _ in range(10):
                x1, y1 = random.randint(0, max(width, 1)), random.randint(0, max(height, 1))
                x2 = x1 + random.randint(-max(width // 2, 1), max(width // 2, 1))
                y2 = y1 + random.randint(-max(height // 2, 1), max(height // 2, 1))
                color = (random.randint(50, 200), random.randint(50, 200), random.randint(50, 200))
                draw.ellipse([x1, y1, x2, y2], fill=color)
            img = img.filter(ImageFilter.GaussianBlur(radius=2))
            img.save(out_path, 'JPEG' if image_format.upper() == 'JPEG' else 'PNG')
        except ImportError:
            self.logger.warning("PIL not found. Cannot create demo image. A blank file will be used.")
            with open(out_path, 'wb') as f:
                f.write(b'')

    def _validate_and_resize_if_needed(self, image_path: str, expected_width: int, expected_height: int, image_format: str):
        """Ensures the downloaded image has the correct dimensions."""
        try:
            from PIL import Image
            with Image.open(image_path) as img:
                if img.size != (expected_width, expected_height):
                    self.logger.warning(
                        f"Image size mismatch: {img.size} vs {expected_width}x{expected_height}. Resizing..."
                    )
                    resized = img.resize((expected_width, expected_height), Image.LANCZOS)
                    resized.save(image_path, 'JPEG' if image_format.upper() == 'JPEG' else 'PNG')
        except ImportError:
            self.logger.warning("PIL not available. Cannot validate or resize image dimensions.")
        except Exception as e:
            self.logger.error(f"Failed during image validation: {e}")