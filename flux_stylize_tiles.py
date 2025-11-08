"""
FLUX Stylize Tiles - Core processing engine für QGIS FLUX AI Integration.

Diese Datei implementiert die FluxStylizeTiles Klasse, die für:
- FLUX 1.1 [pro] Ultra API-Integration (Image-to-Image) 
- Polling-Workflow mit Timeout-Handling
- Download und Georeferenzierung
- World-File-Berechnung 
- VRT-Erstellung
zuständig ist.
"""

import os
import time
import json
import hashlib
import base64
import logging
from typing import Dict, Any, List, Tuple, Optional, Union
from datetime import datetime

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


class FluxStylizeTiles:
    """
    Core-Implementierung für FLUX AI Tile Stylization.
    
    Verarbeitet Kacheln sequenziell:
    1. FLUX API-Request (base64 image → polling_url)
    2. Polling bis Ready/Failed/Timeout
    3. Download der stylisierten Ergebnisse
    4. World-File-Georeferenzierung
    5. Optionale VRT-Mosaikerstellung
    """
    
    def __init__(self, api_key: str, log_path: Optional[str] = None, endpoint: str = "https://api.eu.bfl.ai"):
        """
        Args:
            api_key: FLUX API Key (aus https://api.flux.dev)
            log_path: Pfad für JSON-Logs (optional)
            endpoint: API Endpoint (EU oder global)
        """
        if not api_key or len(api_key.strip()) < 10:
            raise ValueError("FLUX API Key erforderlich. Hol dir einen auf https://api.bfl.ai")
            
        self.api_key = api_key
        self.endpoint = endpoint.rstrip('/')
        self.log_path = log_path
        self.tiles_processed = []
        
        # ✅ LOGGER ZUERST SETUP (bevor wir loggen!)
        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
        
        # ✅ DEMO-MODUS NACH LOGGER-SETUP
        # Demo-Modus nur bei expliziter 'demo' Eingabe
        if api_key.lower() == 'demo':
            os.environ['FLUX_DEMO_MODE'] = 'true'
            self.logger.info("🎯 DEMO-MODUS explizit aktiviert")
        else:
            # ✅ WICHTIG: Demo-Modus deaktivieren für echte API-Keys!
            os.environ['FLUX_DEMO_MODE'] = 'false'
            self.logger.info("🚀 ECHTER API-MODUS aktiviert")
        # Setup requests session with retries
        if requests:
            self.session = requests.Session()
            retry_strategy = Retry(
                total=3,
                status_forcelist=[429, 500, 502, 503, 504],
                backoff_factor=1
            )
            adapter = HTTPAdapter(max_retries=retry_strategy)
            self.session.mount("http://", adapter)
            self.session.mount("https://", adapter)
        else:
            raise ImportError("requests library ist erforderlich")

    # =====================================================
    # CORE PUBLIC API
    # =====================================================
    
    def process_tile(
        self, 
        row: int, 
        col: int, 
        extent: Tuple[float, float, float, float],  # (xmin, ymin, xmax, ymax)
        N: int,  # Pixelgröße (muss Vielfaches von 32 sein)
        prompt: str,
        out_path: str,
        seed: Optional[int] = None,
        image_format: str = "PNG",
        payload: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Verarbeitet eine einzelne Kachel mit FLUX AI.
        
        Args:
            row, col: Kachel-Koordinaten im Grid
            extent: Georeferenzierte Bounding Box (xmin, ymin, xmax, ymax)
            N: Tile-Größe in Pixel (256, 512, 1024, etc. - Vielfache von 32)
            prompt: FLUX Style-Prompt
            out_path: Ausgabepfad für stylisiertes Bild
            seed: Optionaler Zufallsseed
            image_format: "PNG" oder "JPEG"
            payload: Zusätzliche API-Parameter
            
        Returns:
            Dict mit "status" (Ready/Failed/Timeout/...), "reason", "output_path"
        """
        start_time = time.time()
        tile_info = {
            "row": row, "col": col, "extent": extent, "N": N,
            "prompt_hash": self._hash_prompt(prompt),
            "seed": seed, "start_time": start_time
        }
        
        self.logger.info(f"Verarbeite Tile {row},{col} - Größe {N}x{N}")
        
        try:
            # 1. ✅ RENDERE ECHTE KARTE vom Map Canvas
            input_png_path = self._render_map_tile(extent, N, out_path)
            
            # 2. FLUX API Request
            api_result = self._request_flux_stylization(
                input_png_path, prompt, seed, image_format, payload or {}
            )
            
            if not api_result["success"]:
                tile_info.update({"status": "Failed", "reason": api_result["error"]})
                self._log_tile(tile_info)
                return {"status": "Failed", "reason": api_result["error"]}
            
            # 3. Polling bis fertig
            polling_result = self._poll_until_ready(
                api_result["polling_url"], timeout_s=600
            )
            
            if polling_result["status"] != "Ready":
                tile_info.update({"status": polling_result["status"], "reason": polling_result.get("error", "")})
                self._log_tile(tile_info)
                return {"status": polling_result["status"], "reason": polling_result.get("error", "")}
            
            # 4. Download Result
            download_result = self._download_stylized_image(
                polling_result["delivery_url"], out_path, N, image_format
            )
            
            if not download_result["success"]:
                tile_info.update({"status": "DownloadFailed", "reason": download_result["error"]})
                self._log_tile(tile_info)
                return {"status": "DownloadFailed", "reason": download_result["error"]}
            
            # 5. World-File schreiben
            try:
                self._write_worldfile(out_path, extent, N, image_format)
            except Exception as e:
                self.logger.warning(f"World-File konnte nicht erstellt werden: {e}")
            
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
            self.logger.error(f"Unexpected error processing tile {row},{col}: {e}")
            tile_info.update({"status": "Failed", "reason": str(e), "end_time": time.time()})
            self._log_tile(tile_info)
            return {"status": "Failed", "reason": str(e)}
    
    def build_vrt(self, vrt_path: str, tile_paths: List[str]) -> None:
        """
        Erstellt ein VRT-Mosaik aus den verarbeiteten Kacheln.
        
        Args:
            vrt_path: Pfad für die VRT-Datei
            tile_paths: Liste der Tile-Pfade
            
        Raises:
            RuntimeError: Falls GDAL nicht verfügbar oder VRT-Erstellung fehlschlägt
        """
        if not gdal:
            raise RuntimeError("GDAL ist nicht verfügbar. VRT kann nicht erstellt werden.")
        
        if len(tile_paths) < 2:
            raise RuntimeError("VRT benötigt mindestens 2 Tiles")
        
        # Validiere, dass alle Dateien existieren
        missing_files = [p for p in tile_paths if not os.path.exists(p)]
        if missing_files:
            raise RuntimeError(f"Fehlende Tile-Dateien: {missing_files}")
        
        try:
            # Erstelle VRT
            vrt_options = ['VRT']  # Format
            gdal.BuildVRT(vrt_path, tile_paths, options=vrt_options)
            self.logger.info(f"VRT-Mosaik erstellt: {vrt_path}")
            
        except Exception as e:
            raise RuntimeError(f"VRT-Erstellung fehlgeschlagen: {e}")

    # =====================================================
    # INTERNAL HELPER METHODS
    # =====================================================
    
    def _render_map_tile(self, extent_tuple: Tuple[float, float, float, float], N: int, base_path: str) -> str:
        """
        Rendert echte QGIS Map Canvas als PNG für FLUX AI.
        
        Args:
            extent_tuple: (xmin, ymin, xmax, ymax) für Rendering
            N: Tile-Größe in Pixel
            base_path: Basis-Pfad für Output-PNG
            
        Returns:
            Pfad zur gerenderten PNG-Datei
        """
        output_path = base_path.replace('.png', '_input.png').replace('.jpeg', '_input.png')
        
        # ✅ SICHERSTELLEN DASS OUTPUT-VERZEICHNIS EXISTIERT
        import os
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        self.logger.info(f"🎯 Starte Map-Rendering: {extent_tuple} → {output_path}")
        
        try:
            # ✅ ECHTES QGIS MAP RENDERING mit verbesserter Fehlerbehandlung
            from qgis.core import (
                QgsMapSettings, QgsRectangle, QgsMapRendererParallelJob,
                QgsProject, QgsCoordinateReferenceSystem
            )
            from qgis.utils import iface
            from PyQt5.QtCore import QSize, Qt
            from PyQt5.QtGui import QImage
            
            # Map Canvas Settings kopieren
            canvas = iface.mapCanvas()
            if not canvas:
                raise RuntimeError("Map Canvas nicht verfügbar")
                
            settings = QgsMapSettings()
            
            # Extent setzen (quadratisch vom Processing Algorithm)
            xmin, ymin, xmax, ymax = extent_tuple
            render_extent = QgsRectangle(xmin, ymin, xmax, ymax)
            settings.setExtent(render_extent)
            
            # Output-Größe: N x N Pixel
            settings.setOutputSize(QSize(N, N))
            
            # Layer: aktuelle Canvas-Layer verwenden
            layers = canvas.layers()
            if not layers:
                raise RuntimeError("Keine sichtbaren Layer im Canvas")
                
            settings.setLayers(layers)
            settings.setDestinationCrs(canvas.mapSettings().destinationCrs())
            
            # Transparenter Hintergrund für PNG
            settings.setBackgroundColor(Qt.transparent)
            
            self.logger.info(f"🗺️ Rendering-Setup: {len(layers)} Layer, {render_extent.toString()}")
            
            # Parallel-Rendering (schneller)
            job = QgsMapRendererParallelJob(settings)
            job.start()
            job.waitForFinished()
            
            # Rendered Image validieren und speichern
            rendered_image = job.renderedImage()
            if rendered_image.isNull():
                raise RuntimeError("Map-Rendering returned Null-Image")
                
            if rendered_image.width() != N or rendered_image.height() != N:
                self.logger.warning(f"⚠️ Rendered size mismatch: {rendered_image.width()}x{rendered_image.height()} vs {N}x{N}")
                
            # PNG speichern mit Validierung
            success = rendered_image.save(output_path, 'PNG')
            if not success:
                raise RuntimeError(f"PNG-Save failed: {output_path}")
                
            # Datei-Existenz prüfen
            if not os.path.exists(output_path):
                raise RuntimeError(f"PNG nicht erstellt: {output_path}")
                
            file_size = os.path.getsize(output_path)
            if file_size < 100:  # Sehr kleine Datei = wahrscheinlich kaputt
                raise RuntimeError(f"PNG zu klein: {file_size} bytes")
                
            self.logger.info(f"✅ Map-Canvas gerendert: {os.path.basename(output_path)} ({file_size} bytes)")
            return output_path
            
        except Exception as e:
            self.logger.error(f"❌ QGIS-Rendering fehlgeschlagen: {e}")
            self.logger.info("🔄 Fallback zu Demo-Tile...")
            
            # ✅ FALLBACK: Demo-Tile wenn QGIS-Rendering nicht funktioniert
            try:
                return self._create_demo_tile_fallback(N, output_path)
            except Exception as fe:
                self.logger.error(f"❌ Auch Fallback fehlgeschlagen: {fe}")
                raise RuntimeError(f"Weder Map-Rendering noch Fallback erfolgreich: {e} | {fe}")
    
    def _create_demo_tile_fallback(self, N: int, output_path: str) -> str:
        """Fallback Demo-Tile wenn echtes Rendering fehlschlägt."""
        try:
            from PIL import Image, ImageDraw
            img = Image.new('RGBA', (N, N), (100, 150, 200, 255))
            draw = ImageDraw.Draw(img)
            draw.rectangle([N//4, N//4, 3*N//4, 3*N//4], fill=(200, 100, 150, 255))
            draw.text((N//2-50, N//2), "DEMO MAP", fill=(255, 255, 255, 255))
            img.save(output_path, 'PNG')
        except ImportError:
            # Minimal PNG wenn PIL fehlt
            with open(output_path, 'wb') as f:
                png_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\x0f\x00\x00\x01\x00\x01\x00\x00\x00\x00\x00\r\n\x00\x00\x00\x00IEND\xaeB`\x82'
                f.write(png_data)
        return output_path
    
    def _request_flux_stylization(
        self, input_path: str, prompt: str, seed: Optional[int],
        output_format: str, extra_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Sendet Request an FLUX API - unterstützt sowohl Ultra als auch Kontext.
        
        Returns:
            {"success": bool, "polling_url": str, "error": str}
        """
        try:
            # Base64-kodiere Eingabebild (Kartenkachel)
            with open(input_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('ascii')
            
            # ✅ API WAHL: Kontext [pro] vs Ultra
            use_kontext = extra_params.get("use_kontext_api", False)
            
            if use_kontext:
                # FLUX.1 Kontext [pro] - Einfaches Image Editing
                endpoint = "/v1/flux-kontext-pro"
                payload = {
                    "prompt": prompt,
                    "input_image": image_data,                       # ✅ Kontext: input_image
                    "output_format": output_format.lower(),
                    "safety_tolerance": extra_params.get("safety_tolerance", 2),
                    "aspect_ratio": "1:1"                           # Quadratische Kacheln
                }
                self.logger.info(f"📝 Using FLUX.1 Kontext [pro] for image editing")
            else:
                # FLUX 1.1 [pro] Ultra - Advanced Image-to-Image
                endpoint = "/v1/flux-pro-1.1-ultra"
                payload = {
                    "prompt": prompt,
                    "image_prompt": image_data,                      # ✅ Ultra: image_prompt
                    "image_prompt_strength": extra_params.get("image_prompt_strength", 0.8),
                    "aspect_ratio": "1:1",                           # Quadratische Kacheln
                    "output_format": output_format.lower(),
                    "safety_tolerance": extra_params.get("safety_tolerance", 2),
                    "raw": extra_params.get("raw", False)
                }
                self.logger.info(f"🚀 Using FLUX 1.1 [pro] Ultra for advanced stylization")
            
            if seed is not None:
                payload["seed"] = seed
            
            headers = {
                "accept": "application/json",
                "x-key": self.api_key,
                "Content-Type": "application/json"
            }
            
            # ✅ CLEAR DEBUG: Demo vs. Echter API-Call
            demo_mode = os.getenv('FLUX_DEMO_MODE', 'false').lower() == 'true'
            self.logger.info(f"🔄 API-Modus: {'DEMO' if demo_mode else 'ECHT'} | Endpoint: {self.endpoint}{endpoint}")
            self.logger.info(f"🔑 API-Key: {self.api_key[:8]}... (Länge: {len(self.api_key)})")
            
            if demo_mode:
                self.logger.info("⚠️ DEMO-MODUS AKTIV - Kein echter API-Call!")
                return self._simulate_flux_request(payload)
            
            # ✅ ECHTER API-CALL mit detailliertem Logging
            full_url = f"{self.endpoint}{endpoint}"
            self.logger.info(f"📡 Sende Request an: {full_url}")
            self.logger.info(f"📝 Payload Keys: {list(payload.keys())}")
            self.logger.info(f"🖼️ Image Size: {len(payload.get('input_image', payload.get('image_prompt', '')))//1000}KB base64")
            
            response = self.session.post(
                full_url,
                json=payload,
                headers=headers,
                timeout=60
            )
            
            self.logger.info(f"📥 Response Status: {response.status_code}")
            
            if response.status_code == 429:
                self.logger.error("🚫 Rate limit exceeded!")
                return {"success": False, "error": "Rate limit exceeded - zu viele Requests"}
            
            if response.status_code == 401:
                self.logger.error("🚫 Authentication failed - API Key ungültig!")
                return {"success": False, "error": "API Key ungültig"}
                
            if response.status_code == 400:
                self.logger.error(f"🚫 Bad Request: {response.text}")
                return {"success": False, "error": f"Bad Request: {response.text}"}
            
            response.raise_for_status()
            result = response.json()
            
            self.logger.info(f"✅ API Request erfolgreich! ID: {result.get('id', 'N/A')}")
            self.logger.info(f"🔄 Polling URL: {result.get('polling_url', 'N/A')}")
            
            return {
                "success": True,
                "polling_url": result["polling_url"],
                "id": result["id"]
            }
            
        except Exception as e:
            self.logger.error(f"FLUX API Request failed: {e}")
            return {"success": False, "error": str(e)}
    
    def _simulate_flux_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Demo-Simulation eines FLUX-Requests."""
        return {
            "success": True,
            "polling_url": f"{self.endpoint}/v1/get_result?id=demo_12345",
            "id": "demo_12345"
        }
    
    def _poll_until_ready(self, polling_url: str, timeout_s: int = 600) -> Dict[str, Any]:
        """
        Pollt die FLUX API bis Ready/Failed oder Timeout.
        
        Returns:
            {"status": str, "delivery_url": str, "error": str}
        """
        start_time = time.time()
        poll_interval = 0.5
        poll_count = 0
        
        headers = {
            "accept": "application/json",
            "x-key": self.api_key
        }
        
        demo_mode = os.getenv('FLUX_DEMO_MODE', 'false').lower() == 'true'
        self.logger.info(f"🔄 Starte Polling: {'DEMO' if demo_mode else 'ECHT'}")
        self.logger.info(f"🕐 Timeout: {timeout_s}s | Interval: {poll_interval}s")
        
        while time.time() - start_time < timeout_s:
            poll_count += 1
            elapsed = time.time() - start_time
            
            try:
                # Für Demo-Modus
                if demo_mode:
                    self.logger.info(f"📊 Demo-Polling #{poll_count} ({elapsed:.1f}s)")
                    # Simuliere kurze Verarbeitung
                    if elapsed > 2:  # Nach 2 Sekunden "fertig"
                        self.logger.info("✅ Demo-Polling abgeschlossen!")
                        return {
                            "status": "Ready",
                            "delivery_url": "https://delivery-eu1.bfl.ai/demo/sample.png?signature=demo"
                        }
                    else:
                        time.sleep(poll_interval)
                        continue
                
                # ✅ ECHTER POLLING mit detailliertem Logging
                self.logger.info(f"📊 Polling #{poll_count} ({elapsed:.1f}s) → {polling_url}")
                
                response = self.session.get(polling_url, headers=headers, timeout=30)
                self.logger.info(f"📥 Poll-Response: {response.status_code}")
                
                if response.status_code != 200:
                    self.logger.warning(f"⚠️ Poll-Status {response.status_code}: {response.text[:200]}")
                    time.sleep(poll_interval)
                    continue
                
                result = response.json()
                status = result.get("status", "UNKNOWN")
                
                self.logger.info(f"📋 API Status: '{status}' | Keys: {list(result.keys())}")
                
                if status == "Ready":
                    delivery_url = result["result"]["sample"]
                    self.logger.info(f"✅ FLUX fertig! Delivery: {delivery_url[:60]}...")
                    return {
                        "status": "Ready",
                        "delivery_url": delivery_url
                    }
                elif status in ["Error", "Failed"]:
                    error_msg = result.get("message", result.get("error", "Unknown API error"))
                    self.logger.error(f"❌ FLUX Failed: {error_msg}")
                    return {
                        "status": "Failed",
                        "error": error_msg
                    }
                elif status in ["Processing", "Pending"]:
                    self.logger.info(f"⏳ Noch in Verarbeitung... ({status})")
                else:
                    self.logger.warning(f"⁉️ Unbekannter Status: {status}")
                
                # Weiter warten
                time.sleep(poll_interval)
                
            except Exception as e:
                self.logger.error(f"❌ Polling Fehler #{poll_count}: {e}")
                time.sleep(poll_interval)
        
        self.logger.error(f"⏰ Polling Timeout nach {timeout_s}s ({poll_count} Versuche)")
        return {"status": "Timeout", "error": f"Polling timeout nach {timeout_s}s"}
    
    def _download_stylized_image(
        self, delivery_url: str, out_path: str, expected_size: int, image_format: str
    ) -> Dict[str, Any]:
        """
        Lädt das stylisierte Bild von der Delivery-URL herunter.
        
        Returns:
            {"success": bool, "error": str}
        """
        try:
            # Für Demo: erstelle stylisiertes Bild
            if os.getenv('FLUX_DEMO_MODE', 'true').lower() == 'true':
                return self._create_demo_stylized_image(out_path, expected_size, image_format)
            
            # Echter Download
            response = self.session.get(delivery_url, timeout=60)
            
            if response.status_code in [403, 404]:
                # Ein Retry bei abgelaufenen URLs
                self.logger.info("Delivery URL expired, retrying once...")
                time.sleep(2)
                response = self.session.get(delivery_url, timeout=60)
            
            response.raise_for_status()
            
            # Speichere Bild
            with open(out_path, 'wb') as f:
                f.write(response.content)
            
            # Validiere Dimensionen (optional)
            try:
                self._validate_and_resize_if_needed(out_path, expected_size, image_format)
            except Exception as e:
                self.logger.warning(f"Dimensionsvalidierung fehlgeschlagen: {e}")
            
            return {"success": True}
            
        except Exception as e:
            self.logger.error(f"Download fehlgeschlagen: {e}")
            return {"success": False, "error": str(e)}
    
    def _create_demo_stylized_image(self, out_path: str, N: int, image_format: str) -> Dict[str, Any]:
        """Erstellt ein Demo-stylisiertes Bild für Tests."""
        try:
            from PIL import Image, ImageDraw, ImageFilter
            
            # Erstelle "stylisiertes" Demo-Bild
            img = Image.new('RGBA', (N, N), (255, 255, 255, 0) if image_format == "PNG" else (255, 255, 255, 255))
            draw = ImageDraw.Draw(img)
            
            # Zeichne einige "stylisierte" Elemente
            import random
            random.seed(42)  # Deterministisch für Tests
            
            for _ in range(10):
                x1, y1 = random.randint(0, N//2), random.randint(0, N//2)
                x2, y2 = x1 + random.randint(N//4, N//2), y1 + random.randint(N//4, N//2)
                color = (random.randint(50, 255), random.randint(50, 255), random.randint(50, 255), 200)
                draw.ellipse([x1, y1, x2, y2], fill=color)
            
            # Weichzeichner für "artistic" Look
            img = img.filter(ImageFilter.GaussianBlur(radius=1))
            
            # Speichere entsprechend Format
            if image_format == "PNG":
                img.save(out_path, 'PNG')
            else:
                # JPEG: konvertiere zu RGB
                if img.mode == 'RGBA':
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    img = Image.alpha_composite(Image.new('RGBA', img.size, (255, 255, 255, 255)), img)
                    img = img.convert('RGB')
                img.save(out_path, 'JPEG', quality=90)
            
            return {"success": True}
            
        except ImportError:
            # Fallback: kopiere Input als "stylized"
            try:
                import shutil
                input_path = out_path.replace('.png', '_input.png').replace('.jpeg', '_input.png')
                if os.path.exists(input_path):
                    shutil.copy(input_path, out_path)
                return {"success": True}
            except Exception as e:
                return {"success": False, "error": f"Demo image creation failed: {e}"}
        except Exception as e:
            return {"success": False, "error": f"Demo image creation failed: {e}"}
    
    def _validate_and_resize_if_needed(self, image_path: str, expected_size: int, image_format: str):
        """Validiert Bildgröße und passt bei Bedarf an."""
        try:
            from PIL import Image
            
            with Image.open(image_path) as img:
                if img.size != (expected_size, expected_size):
                    self.logger.info(f"Resizing {img.size} -> {expected_size}x{expected_size}")
                    
                    # Resize mit hoher Qualität
                    resized = img.resize((expected_size, expected_size), Image.LANCZOS)
                    
                    if image_format == "PNG":
                        resized.save(image_path, 'PNG')
                    else:
                        if resized.mode == 'RGBA':
                            # JPEG: konvertiere zu RGB mit weißem Hintergrund
                            background = Image.new('RGB', resized.size, (255, 255, 255))
                            resized = Image.alpha_composite(Image.new('RGBA', resized.size, (255, 255, 255, 255)), resized)
                            resized = resized.convert('RGB')
                        resized.save(image_path, 'JPEG', quality=90)
                        
        except ImportError:
            self.logger.warning("PIL nicht verfügbar - kann Dimensionen nicht prüfen")
        except Exception as e:
            self.logger.warning(f"Bildvalidierung fehlgeschlagen: {e}")
    
    def _write_worldfile(self, image_path: str, extent: Tuple[float, float, float, float], N: int, image_format: str):
        """
        Schreibt World-File für Georeferenzierung.
        
        World-File Format (6 Zeilen):
        1: A = Pixelgröße X (map units per pixel)
        2: D = Rotation Y (0.0)  
        3: B = Rotation X (0.0)
        4: E = Pixelgröße Y (negativ)
        5: C = X-Koordinate oberer linker Pixel-Mittelpunkt
        6: F = Y-Koordinate oberer linker Pixel-Mittelpunkt
        """
        xmin, ymin, xmax, ymax = extent
        
        # Pixelgrößen berechnen
        A = (xmax - xmin) / N  # X-Resolution
        E = -((ymax - ymin) / N)  # Y-Resolution (negativ!)
        
        # Koordinaten des oberen linken Pixel-Mittelpunkts
        C = xmin + A / 2
        F = ymax + E / 2  # E ist bereits negativ
        
        # World-File-Endung bestimmen
        if image_format == "PNG":
            worldfile_ext = ".pgw"
        else:
            worldfile_ext = ".jgw"
        
        worldfile_path = os.path.splitext(image_path)[0] + worldfile_ext
        
        # World-File schreiben
        with open(worldfile_path, 'w') as wf:
            wf.write(f"{A}\n")      # Pixel size X
            wf.write("0.0\n")       # Rotation Y  
            wf.write("0.0\n")       # Rotation X
            wf.write(f"{E}\n")      # Pixel size Y (negativ)
            wf.write(f"{C}\n")      # X coordinate of center of upper left pixel
            wf.write(f"{F}\n")      # Y coordinate of center of upper left pixel
        
        self.logger.debug(f"World-File erstellt: {worldfile_path}")
    
    def _hash_prompt(self, prompt: str) -> str:
        """Hasht den Prompt für Logging (ohne sensitive Daten)."""
        return hashlib.sha256(prompt.encode('utf-8')).hexdigest()[:16]
    
    def _log_tile(self, tile_info: Dict[str, Any]):
        """Loggt Tile-Verarbeitung in JSON-Format (ohne API-Key)."""
        if not self.log_path:
            return
        
        # Sichere Kopie ohne sensible Daten
        safe_info = tile_info.copy()
        
        # Log-Eintrag in JSON-Datei
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "tile": safe_info
        }
        
        try:
            os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
            
            # Append zu JSON-Log
            if os.path.exists(self.log_path):
                with open(self.log_path, 'r') as f:
                    logs = json.load(f)
            else:
                logs = []
            
            logs.append(log_entry)
            
            with open(self.log_path, 'w') as f:
                json.dump(logs, f, indent=2)
                
        except Exception as e:
            self.logger.warning(f"Logging fehlgeschlagen: {e}")


# =====================================================
# UTILITY FUNCTIONS FOR TESTING
# =====================================================

def _compute_worldfile_params(extent: Tuple[float, float, float, float], N: int) -> Tuple[float, float, float, float, float, float]:
    """
    Berechnet World-File-Parameter aus Extent und Pixelgröße.
    
    Args:
        extent: (xmin, ymin, xmax, ymax)
        N: Pixelgröße (quadratisch)
        
    Returns:
        (A, D, B, E, C, F) - World-File 6-Parameter-Transformation
    """
    xmin, ymin, xmax, ymax = extent
    
    A = (xmax - xmin) / N    # X pixel size
    D = 0.0                  # Y rotation
    B = 0.0                  # X rotation  
    E = -((ymax - ymin) / N) # Y pixel size (negativ)
    C = xmin + A / 2         # X coord of center of upper left pixel
    F = ymax + E / 2         # Y coord of center of upper left pixel
    
    return A, D, B, E, C, F


def _is_crs_degrees(crs_auth: str) -> bool:
    """
    Prüft ob ein CRS in Grad-Einheiten vorliegt.
    
    Args:
        crs_auth: CRS-Authid z.B. "EPSG:4326"
        
    Returns:
        True wenn Grad-basiert (Geographic), False wenn kartesisch/Meter
    """
    # Vereinfachte Prüfung anhand bekannter EPSG-Codes
    geographic_crs = [
        "EPSG:4326",   # WGS 84
        "EPSG:4269",   # NAD83  
        "EPSG:4258",   # ETRS89
        "EPSG:4230",   # ED50
        "EPSG:4314"    # DHDN
    ]
    
    return crs_auth in geographic_crs or "4326" in crs_auth


if __name__ == "__main__":
    # Demo
    print("FLUX Stylize Tiles - Core Engine")
    print("Für echte Nutzung verwende QGIS Processing Interface")