# Final Refined Structure: Perfect Balance

## 🎯 The Ideal Structure

Based on your excellent feedback, here's the **perfect balance** structure:

```
qgis_flux/
├── __init__.py                    # Main package entry
├── clients/                      # Client implementations
│   ├── flux_kontext.py           # Flux Kontext: API + QGIS
│   ├── flux_ultra.py             # Flux Ultra: API + QGIS
│   └── gemini.py                 # Gemini: API + QGIS
└── utils.py                      # Shared utilities
```

## 🏆 Why This is Perfect

### 1. **Just Enough Organization**
- **`clients/` directory** provides logical grouping
- **Not too flat**: Avoids clutter in root directory
- **Not too deep**: Only one level of nesting

### 2. **Maximum Simplicity**
- **5 files total** (including directory)
- **Clear naming**: Easy to understand purpose
- **Easy navigation**: Find what you need quickly

### 3. **Professional Quality**
- **Proper separation**: API + QGIS in each client file
- **Maintainable**: Easy to modify individual clients
- **Extensible**: Add new clients by adding files

## 📋 Implementation Details

### 1. Main Package Entry (`__init__.py`)
```python
"""
QGIS FLUX AI Toolbox - Final Refined Implementation.

Perfect balance: simple yet professional structure.
"""

from .clients.flux_kontext import FluxKontextAlgorithm
from .clients.flux_ultra import FluxUltraAlgorithm
from .clients.gemini import GeminiAlgorithm

__all__ = [
    'FluxKontextAlgorithm',
    'FluxUltraAlgorithm',
    'GeminiAlgorithm'
]
```

### 2. Client Structure (Example: `clients/flux_kontext.py`)
```python
"""
Flux Kontext Client - Complete implementation in one file.

Contains both API communication and QGIS algorithm for simplicity.
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

# ===== API CLIENT =====
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
            
            # Build and send request
            payload = {
                'input_image': image_data,
                'prompt': prompt,
                'safety_tolerance': safety_tolerance,
                'aspect_ratio': aspect_ratio
            }
            
            if seed:
                payload['seed'] = seed
            
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
            return {
                'success': False,
                'error': str(e),
                'output_path': None
            }

# ===== QGIS ALGORITHM =====
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
        # API Key parameter
        self.addParameter(
            QgsProcessingParameterString(
                self.API_KEY,
                "API Key",
                optional=False
            )
        )
        
        # Prompt parameter
        self.addParameter(
            QgsProcessingParameterString(
                self.PROMPT,
                "Prompt",
                multiLine=True,
                optional=False
            )
        )
        
        # Safety Tolerance parameter
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
        
        # Create and use API client
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
        
        # Return results
        feedback.pushInfo(f"✅ Processing complete: {result['output_path']}")
        return {"OUTPUT": result['output_path']}

# ===== ALGORITHM REGISTRATION =====
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

# Geometry utilities
def extent_with_aspect_ratio(extent: QgsRectangle, desired_ratio: float) -> QgsRectangle:
    """Crop extent to match desired aspect ratio."""
    # Implementation from original code
    pass

def format_aspect_ratio(width: int, height: int) -> str:
    """Format aspect ratio as string."""
    # Implementation from original code
    pass

# File utilities
def ensure_directory_exists(path: str):
    """Ensure directory exists."""
    os.makedirs(path, exist_ok=True)

def create_fallback_image(width: int, height: int, output_path: str):
    """Create fallback image."""
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

## 🎯 Benefits of This Structure

### 1. **Perfect Organization**
- **`clients/` directory** groups related files
- **Flat enough** to be simple
- **Organized enough** to be professional

### 2. **Easy to Understand**
- **Clear file names** indicate purpose
- **Logical grouping** of client files
- **Simple navigation** to find what you need

### 3. **Simple to Maintain**
- **One file per client** - easy to modify
- **Shared utilities** - avoid duplication
- **Clear separation** within files

### 4. **Easy to Extend**
- **Add new clients** by adding files to `clients/`
- **Add utilities** to `utils.py`
- **No structural changes** needed

## 📊 Comparison with Other Approaches

### ❌ Too Complex (Original)
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
**Problem**: Too many files, deep nesting, hard to navigate

### ❌ Too Simple (Flat)
```
qgis_flux/
├── __init__.py
├── flux_kontext.py
├── flux_ultra.py
├── gemini.py
└── utils.py
```
**Problem**: Root directory gets cluttered with many files

### ✅ Perfect Balance (Recommended)
```
qgis_flux/
├── __init__.py
├── clients/
│   ├── flux_kontext.py
│   ├── flux_ultra.py
│   └── gemini.py
└── utils.py
```
**Benefits**: Just enough organization, not too complex

## 🚀 Implementation Plan

### Step 1: Create Structure
```bash
mkdir -p qgis_flux/clients
cd qgis_flux
```

### Step 2: Create Files
1. `__init__.py` - Main package entry
2. `clients/flux_kontext.py` - Flux Kontext client
3. `clients/flux_ultra.py` - Flux Ultra client
4. `clients/gemini.py` - Gemini client
5. `utils.py` - Shared utilities

### Step 3: Implement Functionality
- API communication in each client file
- QGIS algorithm in each client file
- Shared utilities in `utils.py`

### Step 4: Test
- Verify imports work
- Test each algorithm
- Test complete workflow

## ✨ Why This is the Best Approach

1. **Simple**: Only 5 files total
2. **Organized**: Logical grouping with `clients/`
3. **Maintainable**: Easy to modify individual files
4. **Extensible**: Simple to add new clients
5. **Professional**: Proper structure without complexity
6. **Balanced**: Not too simple, not too complex

## 🎯 Recommendation

This **final refined structure** provides the **perfect balance** between simplicity and organization. It's:
- ✅ **Simple enough** for easy understanding
- ✅ **Organized enough** for professional quality
- ✅ **Maintainable enough** for long-term use
- ✅ **Extensible enough** for future growth

**Question**: Should I implement this final refined structure now? This will create a clean, professional, and maintainable QGIS FLUX plugin with the perfect balance of simplicity and organization.