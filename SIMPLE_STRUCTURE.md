# Simplified Structure: One File Per Client

## 🎯 Perfect Balance: Simple Yet Maintainable

Based on your excellent suggestion, here's the **one file per client** approach:

```
qgis_flux/
├── __init__.py                    # Main package entry
├── flux_kontext.py               # Flux Kontext: API + QGIS algorithm
├── flux_ultra.py                 # Flux Ultra: API + QGIS algorithm  
├── gemini.py                     # Gemini: API + QGIS algorithm
├── utils.py                      # Shared utilities
└── types.py                      # Type definitions (optional)
```

## 🏗️ Implementation Details

### 1. Main Package Entry (`__init__.py`)
```python
"""
QGIS FLUX AI Toolbox - Simplified Implementation.

One file per client approach for maximum simplicity.
"""

from .flux_kontext import FluxKontextAlgorithm
from .flux_ultra import FluxUltraAlgorithm
from .gemini import GeminiAlgorithm

__all__ = [
    'FluxKontextAlgorithm',
    'FluxUltraAlgorithm',
    'GeminiAlgorithm'
]
```

### 2. Flux Kontext Client (`flux_kontext.py`)
```python
"""
Flux Kontext Client - API Communication + QGIS Algorithm.

Single file containing everything for Flux Kontext functionality.
"""

import os
import base64
import logging
from typing import Dict, Any, Optional
from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingParameterString,
    QgsProcessingParameterNumber,
    QgsProcessingContext,
    QgsProcessingFeedback
)

# --- API Client (Pure API Communication) ---
class FluxKontextAPIClient:
    """Handles communication with Flux Kontext API."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.endpoint = "https://api.eu.bfl.ai/v1/flux-kontext-pro"
        self.logger = logging.getLogger(__name__)
    
    def process_image(
        self,
        input_path: str,
        prompt: str,
        safety_tolerance: int = 2,
        aspect_ratio: str = "1:1",
        seed: Optional[int] = None
    ) -> Dict[str, Any]:
        """Process image with Flux Kontext API."""
        try:
            # Read and encode image
            with open(input_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('ascii')
            
            # Build payload
            payload = {
                'input_image': image_data,
                'prompt': prompt,
                'safety_tolerance': safety_tolerance,
                'aspect_ratio': aspect_ratio
            }
            
            if seed:
                payload['seed'] = seed
            
            # Send request (simplified - add proper error handling)
            import requests
            response = requests.post(
                self.endpoint,
                json=payload,
                headers={'x-key': self.api_key},
                timeout=60
            )
            
            response.raise_for_status()
            result = response.json()
            
            # Handle polling and download (simplified)
            return {
                'success': True,
                'output_path': output_path,
                'metadata': result
            }
            
        except Exception as e:
            self.logger.error(f"Flux Kontext API error: {e}")
            return {
                'success': False,
                'error': str(e),
                'output_path': None
            }

# --- QGIS Algorithm (QGIS Integration) ---
class FluxKontextAlgorithm(QgsProcessingAlgorithm):
    """QGIS Processing Algorithm for Flux Kontext."""
    
    API_KEY = "API_KEY"
    PROMPT = "PROMPT"
    SAFETY = "SAFETY"
    
    def __init__(self):
        super().__init__()
        self._setup_parameters()
    
    def _setup_parameters(self):
        """Setup algorithm parameters."""
        # API Key
        self.addParameter(
            QgsProcessingParameterString(
                self.API_KEY,
                "API Key",
                optional=False
            )
        )
        
        # Prompt
        self.addParameter(
            QgsProcessingParameterString(
                self.PROMPT,
                "Prompt",
                multiLine=True,
                optional=False
            )
        )
        
        # Safety Tolerance
        self.addParameter(
            QgsProcessingParameterNumber(
                self.SAFETY,
                "Safety Tolerance (0=strict, 6=permissive)",
                type=QgsProcessingParameterNumber.Integer,
                defaultValue=2,
                minValue=0,
                maxValue=6,
                optional=True
            )
        )
    
    def processAlgorithm(self, parameters, context, feedback):
        """Process the algorithm."""
        # Extract parameters
        api_key = self.parameterAsString(parameters, self.API_KEY, context)
        prompt = self.parameterAsString(parameters, self.PROMPT, context)
        safety = self.parameterAsInt(parameters, self.SAFETY, context)
        
        # Create API client
        api_client = FluxKontextAPIClient(api_key)
        
        # Process image
        result = api_client.process_image(
            input_path="input.png",  # Would come from rendering
            prompt=prompt,
            safety_tolerance=safety
        )
        
        if not result['success']:
            feedback.reportError(result['error'], fatalError=True)
            return {}
        
        # Load result into QGIS
        feedback.pushInfo(f"✅ Processing complete: {result['output_path']}")
        return {"OUTPUT": result['output_path']}

# --- Algorithm Registration ---
def create_algorithm():
    """Create algorithm instance."""
    return FluxKontextAlgorithm()
```

### 3. Shared Utilities (`utils.py`)
```python
"""
Shared utilities for all clients.
"""

import os
from typing import Tuple
from qgis.core import QgsRectangle

# --- Geometry Utilities ---
def extent_with_aspect_ratio(extent: QgsRectangle, desired_ratio: float) -> QgsRectangle:
    """Crop extent to match desired aspect ratio."""
    # Implementation from original code
    pass

def format_aspect_ratio(width: int, height: int) -> str:
    """Format aspect ratio as string (e.g., '16:9')."""
    # Implementation from original code
    pass

# --- File Utilities ---
def ensure_directory_exists(path: str):
    """Ensure directory exists."""
    os.makedirs(path, exist_ok=True)

# --- Image Utilities ---
def create_fallback_image(width: int, height: int, output_path: str):
    """Create fallback image if rendering fails."""
    try:
        from PIL import Image, ImageDraw
        img = Image.new('RGBA', (width, height), (100, 150, 200, 255))
        draw = ImageDraw.Draw(img)
        draw.text((width//2 - 50, height//2), "DEMO MAP", fill="white")
        img.save(output_path, 'PNG')
        return output_path
    except ImportError:
        # Create minimal PNG
        with open(output_path, 'wb') as f:
            f.write(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc`\x00\x00\x00\x02\x00\x01\xe2\x21\xbc\x33\x00\x00\x00\x00IEND\xaeB`\x82')
        return output_path
```

## 🎯 Benefits of This Approach

### 1. **Maximum Simplicity**
- **5 files total** (including main package)
- **One file per client** - easy to understand
- **No complex directory structure**

### 2. **Still Maintainable**
- **Clear separation** within each file (API vs QGIS)
- **Easy to test** individual components
- **Simple to extend** with new clients

### 3. **Perfect Balance**
- **Not too simple**: Still has proper separation
- **Not too complex**: No deep nesting
- **Just right**: One file per logical unit

## 📋 File Structure Comparison

### Old Complex Structure
```
PROCESS/
├── flux/
│   ├── engine.py
│   ├── config.py
│   └── kontext_algorithm.py
├── gemini/
│   ├── engine.py
│   ├── config.py
│   └── algorithm.py
```
**10+ files, deep nesting, hard to navigate**

### New Simple Structure
```
qgis_flux/
├── __init__.py
├── flux_kontext.py
├── flux_ultra.py
├── gemini.py
└── utils.py
```
**5 files total, flat structure, easy to understand**

## 🚀 Implementation Plan

### Step 1: Create Files
1. `__init__.py` - Main package entry
2. `flux_kontext.py` - Flux Kontext client
3. `flux_ultra.py` - Flux Ultra client
4. `gemini.py` - Gemini client
5. `utils.py` - Shared utilities

### Step 2: Implement Core Functionality
- API communication in each client file
- QGIS algorithm in each client file
- Shared utilities in utils.py

### Step 3: Test
- Verify imports work
- Test each algorithm individually
- Test complete workflow

## ✨ Why This is Perfect

1. **Simple to understand**: 5 files, clear names
2. **Easy to maintain**: One file per client
3. **Simple to extend**: Add new client files
4. **Easy to test**: Test individual files
5. **Professional**: Still has proper separation
6. **No complexity**: Flat structure, no nesting

## 🎯 Recommendation

This **one file per client** approach gives you:
- ✅ **Maximum simplicity** (only 5 files)
- ✅ **Easy maintenance** (clear separation)
- ✅ **Simple extension** (add new files)
- ✅ **Professional quality** (proper structure)

**Question**: Should I implement this simplified structure now?