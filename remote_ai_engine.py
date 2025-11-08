"""
Remote AI Engine - Core processing for QGIS AI integration.

This file implements the RemoteAiEngine class, which is responsible for:
- Communicating with a remote AI API (currently FLUX).
- Handling the polling workflow with timeouts.
- Downloading and georeferencing the results.
- Calculating world files for proper spatial positioning.
- Creating VRT mosaics.
"""

import os
import time
import json
import hashlib
import base64
import logging
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime

from .flux_api_config import ApiConfig

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
except ImportError:
    requests = None

try:
    from osgeo import gdal
    gdal.UseExceptions()
except ImportError:
    gdal = None


class RemoteAiEngine:
    """
    Core implementation for remote AI image processing.

    Handles the PROCESS step of the workflow:
    1. Sends an API request with a rendered map tile.
    2. Polls for the result until it's ready, fails, or times out.
    3. Downloads the processed image.
    4. Writes a world file for georeferencing.
    """

    def __init__(self, api_key: str, log_path: Optional[str] = None, endpoint: str = "https://api.eu.bfl.ai"):
        """
        Args:
            api_key: The API Key for the remote service.
            log_path: Path for JSON log files (optional).
            endpoint: The base API endpoint (e.g., EU or global).
        """
        if not api_key or len(api_key.strip()) < 10:
            raise ValueError("A valid API Key is required.")

        self.api_key = api_key
        self.endpoint = endpoint.rstrip('/')
        self.log_path = log_path
        self.tiles_processed = []

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


    def process_tile(
        self,
        row: int,
        col: int,
        extent: Tuple[float, float, float, float],
        N: int,
        prompt: str,
        out_path: str,
        api_config: ApiConfig,
        seed: Optional[int] = None,
        image_format: str = "PNG",
        payload: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Processes a single map tile using a remote AI service.
        """
        start_time = time.time()
        tile_info = {
            "row": row, "col": col, "extent": extent, "N": N,
            "prompt_hash": self._hash_prompt(prompt),
            "seed": seed, "start_time": start_time
        }
        
        self.logger.info(f"Processing Tile {row},{col} - Size {N}x{N}")

        try:
            # Step 1: Render the actual map from the QGIS canvas
            input_png_path = self._render_map_tile(extent, N, out_path)
            
            # Step 2: Send the request to the AI API
            api_result = self._send_api_request(
                input_path=input_png_path,
                prompt=prompt,
                seed=seed,
                image_format=image_format,
                api_config=api_config,
                extra_params=payload or {}
            )
            
            if not api_result["success"]:
                raise RuntimeError(api_result.get("error", "Unknown API error"))

            # Step 3: Poll until the processing is complete
            polling_result = self._poll_until_ready(
                api_result["polling_url"], timeout_s=600
            )

            if polling_result["status"] != "Ready":
                raise RuntimeError(f"Processing did not complete: {polling_result['status']} ({polling_result.get('error','')})")

            # Step 4: Download the result
            self._download_stylized_image(
                polling_result["delivery_url"], out_path, N, image_format
            )
            
            # Step 5: Write the world file for georeferencing
            self._write_worldfile(out_path, extent, N, image_format)
            
            # Success
            tile_info.update({
                "status": "Ready",
                "output_path": out_path,
                "delivery_url": polling_result["delivery_url"],
                "end_time": time.time()
            })
            self._log_tile(tile_info)
            self.tiles_processed.append(out_path)
            
            return {"status": "Ready", "output_path": out_path}

        except Exception as e:
            self.logger.error(f"Failed to process tile {row},{col}: {e}", exc_info=True)
            tile_info.update({"status": "Failed", "reason": str(e), "end_time": time.time()})
            self._log_tile(tile_info)
            return {"status": "Failed", "reason": str(e)}

    def build_vrt(self, vrt_path: str, tile_paths: List[str]) -> None:
        """Creates a VRT mosaic from the processed tiles."""
        if not gdal:
            raise RuntimeError("GDAL is not available. Cannot create VRT.")
        
        if not tile_paths:
            self.logger.warning("No tile paths provided to build VRT.")
            return

        missing_files = [p for p in tile_paths if not os.path.exists(p)]
        if missing_files:
            raise RuntimeError(f"Cannot create VRT, missing files: {missing_files}")
        
        try:
            gdal.BuildVRT(vrt_path, tile_paths)
            self.logger.info(f"VRT mosaic created: {vrt_path}")
        except Exception as e:
            raise RuntimeError(f"VRT creation failed: {e}")

    # =====================================================
    # INTERNAL WORKFLOW METHODS
    # =====================================================
    
    def _render_map_tile(self, extent_tuple: Tuple[float, float, float, float], N: int, base_path: str) -> str:
        """Renders the QGIS map canvas to a PNG file for the AI service."""
        output_path = base_path.replace('.png', '_input.png').replace('.jpeg', '_input.png')
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        self.logger.info(f"Rendering map canvas to: {output_path}")
        
        try:
            from qgis.core import (
                QgsMapSettings, QgsRectangle, QgsMapRendererParallelJob
            )
            from qgis.utils import iface
            from PyQt5.QtCore import QSize, Qt

            canvas = iface.mapCanvas()
            if not canvas:
                raise RuntimeError("Map Canvas is not available.")
                
            settings = QgsMapSettings()
            render_extent = QgsRectangle(*extent_tuple)
            settings.setExtent(render_extent)
            settings.setOutputSize(QSize(N, N))
            
            layers = canvas.layers()
            if not layers:
                raise RuntimeError("No visible layers in canvas to render.")
                
            settings.setLayers(layers)
            settings.setDestinationCrs(canvas.mapSettings().destinationCrs())
            settings.setBackgroundColor(Qt.transparent)
            
            job = QgsMapRendererParallelJob(settings)
            job.start()
            job.waitForFinished()
            
            rendered_image = job.renderedImage()
            if rendered_image.isNull() or not rendered_image.save(output_path, 'PNG'):
                raise RuntimeError(f"Failed to render or save map tile to {output_path}")

            return output_path
            
        except Exception as e:
            self.logger.error(f"QGIS map rendering failed: {e}. Falling back to demo tile.")
            try:
                return self._create_demo_tile_fallback(N, output_path)
            except Exception as fe:
                self.logger.error(f"Demo tile fallback also failed: {fe}")
                raise RuntimeError(f"Map rendering and fallback failed. Original error: {e}")

    def _create_demo_tile_fallback(self, N: int, output_path: str) -> str:
        """Creates a placeholder map tile if QGIS rendering fails."""
        try:
            from PIL import Image, ImageDraw
            img = Image.new('RGBA', (N, N), (100, 150, 200, 255))
            draw = ImageDraw.Draw(img)
            draw.text((N//2 - 50, N//2), "DEMO MAP", fill="white")
            img.save(output_path, 'PNG')
            return output_path
        except ImportError:
            with open(output_path, 'wb') as f:
                f.write(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc`\x00\x00\x00\x02\x00\x01\xe2\x21\xbc\x33\x00\x00\x00\x00IEND\xaeB`\x82')
            return output_path

    def _send_api_request(
        self, input_path: str, prompt: str, seed: Optional[int],
        output_format: str, api_config: ApiConfig, extra_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Builds the payload and sends the initial request to the specified API."""
        with open(input_path, 'rb') as f:
            image_data = base64.b64encode(f.read()).decode('ascii')

        # Start with the default payload from the config
        payload = api_config.default_payload.copy()
        
        # Add dynamic values
        payload['prompt'] = prompt
        payload[api_config.image_payload_key] = image_data
        payload['output_format'] = output_format.lower()
        
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

    def _poll_until_ready(self, polling_url: str, timeout_s: int = 600) -> Dict[str, Any]:
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

    def _download_stylized_image(self, delivery_url: str, out_path: str, N: int, image_format: str):
        """Downloads the final image from the delivery URL."""
        if os.getenv('FLUX_DEMO_MODE', 'false').lower() == 'true':
            self.logger.info("DEMO MODE: Creating demo stylized image.")
            self._create_demo_stylized_image(out_path, N, image_format)
            return

        response = self.session.get(delivery_url, timeout=60)
        response.raise_for_status()
        
        with open(out_path, 'wb') as f:
            f.write(response.content)
        
        self.logger.info(f"Image successfully downloaded to {out_path}")
        self._validate_and_resize_if_needed(out_path, N, image_format)

    def _create_demo_stylized_image(self, out_path: str, N: int, image_format: str):
        """Creates a placeholder stylized image for demo mode."""
        try:
            from PIL import Image, ImageDraw, ImageFilter
            import random
            img = Image.new('RGB', (N, N), "white")
            draw = ImageDraw.Draw(img)
            for _ in range(10):
                x1, y1 = random.randint(0, N), random.randint(0, N)
                x2, y2 = x1 + random.randint(-N//2, N//2), y1 + random.randint(-N//2, N//2)
                color = (random.randint(50, 200), random.randint(50, 200), random.randint(50, 200))
                draw.ellipse([x1, y1, x2, y2], fill=color)
            img = img.filter(ImageFilter.GaussianBlur(radius=2))
            img.save(out_path, 'JPEG' if image_format.upper() == 'JPEG' else 'PNG')
        except ImportError:
            self.logger.warning("PIL not found. Cannot create demo image. A blank file will be used.")
            with open(out_path, 'wb') as f:
                f.write(b'')

    def _validate_and_resize_if_needed(self, image_path: str, expected_size: int, image_format: str):
        """Ensures the downloaded image has the correct dimensions."""
        try:
            from PIL import Image
            with Image.open(image_path) as img:
                if img.size != (expected_size, expected_size):
                    self.logger.warning(f"Image size mismatch: {img.size} vs {expected_size}x{expected_size}. Resizing...")
                    resized = img.resize((expected_size, expected_size), Image.LANCZOS)
                    resized.save(image_path, 'JPEG' if image_format.upper() == 'JPEG' else 'PNG')
        except ImportError:
            self.logger.warning("PIL not available. Cannot validate or resize image dimensions.")
        except Exception as e:
            self.logger.error(f"Failed during image validation: {e}")

    def _write_worldfile(self, image_path: str, extent: Tuple[float, float, float, float], N: int, image_format: str):
        """Writes a georeferencing world file for the given image."""
        xmin, ymin, xmax, ymax = extent
        A = (xmax - xmin) / N      # X pixel size
        E = -((ymax - ymin) / N)   # Y pixel size (negative)
        C = xmin + A / 2           # X coordinate of upper-left pixel center
        F = ymax + E / 2           # Y coordinate of upper-left pixel center
        
        ext = ".pgw" if image_format.upper() == "PNG" else ".jgw"
        worldfile_path = os.path.splitext(image_path)[0] + ext
        
        with open(worldfile_path, 'w') as wf:
            wf.write(f"{A}\n0.0\n0.0\n{E}\n{C}\n{F}\n")
        self.logger.debug(f"World file created: {worldfile_path}")

    def _hash_prompt(self, prompt: str) -> str:
        """Creates a simple hash of the prompt for non-sensitive logging."""
        return hashlib.sha256(prompt.encode('utf-8')).hexdigest()[:16]
    
    def _log_tile(self, tile_info: Dict[str, Any]):
        """Logs tile processing details to a JSON file if a path is provided."""
        if not self.log_path: return
        log_entry = {"timestamp": datetime.now().isoformat(), "tile": tile_info}
        try:
            os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
            with open(self.log_path, 'a') as f:
                f.write(json.dumps(log_entry) + "\n")
        except Exception as e:
            self.logger.warning(f"Failed to write to log file {self.log_path}: {e}")