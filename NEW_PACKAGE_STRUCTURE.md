# New Modern Package Structure - Implementation Plan

## 🚀 Starting Fresh: Modern QGIS FLUX Package

Based on the comprehensive requirements, here's the implementation plan for a completely new, modern package structure.

## 🏗️ New Package Layout

```
qgis_flux/
├── __init__.py                    # Clean package entry
├── py.typed                      # Type hints marker
├── core/                          # Core domain logic
│   ├── __init__.py
│   ├── types.py                   # Type definitions
│   ├── exceptions.py              # Custom exceptions
│   ├── rendering/                 # Rendering functionality
│   │   ├── __init__.py
│   │   ├── canvas.py              # Canvas rendering
│   │   └── tile.py                # Tile generation
│   ├── processing/                # Processing pipeline
│   │   ├── __init__.py
│   │   ├── pipeline.py            # Main processing pipeline
│   │   └── georeferencing.py      # Georeferencing
│   └── loading/                   # Result loading
│       ├── __init__.py
│       ├── qgis_loader.py         # QGIS loading
│       └── format_conversion.py   # Format conversion
├── api/                           # API integrations
│   ├── __init__.py
│   ├── base.py                    # Base API client
│   ├── flux/                      # Flux API implementations
│   │   ├── __init__.py
│   │   ├── kontext.py             # Flux Kontext
│   │   └── ultra.py               # Flux Ultra
│   └── gemini.py                  # Gemini API
├── algorithms/                    # QGIS algorithm implementations
│   ├── __init__.py
│   ├── base.py                    # Base algorithm
│   ├── flux_kontext.py            # Flux Kontext algorithm
│   ├── flux_ultra.py              # Flux Ultra algorithm
│   └── gemini.py                  # Gemini algorithm
├── models/                        # Data models
│   ├── __init__.py
│   ├── config.py                  # Configuration models
│   └── result.py                  # Result models
├── utils/                         # Utilities
│   ├── __init__.py
│   ├── geometry.py                # Geometry utilities
│   ├── logging.py                 # Logging setup
│   └── validation.py              # Validation helpers
└── tests/                         # Comprehensive tests
    ├── __init__.py
    ├── unit/                      # Unit tests
    └── integration/               # Integration tests
```

## 📋 Implementation Steps

### Step 1: Create Package Foundation

#### 1.1. Main Package Entry (`__init__.py`)
```python
"""
QGIS FLUX AI Toolbox - Modern Implementation.

A professional QGIS plugin for AI-powered map processing.
"""

from .algorithms import FluxKontextAlgorithm, FluxUltraAlgorithm, GeminiAlgorithm
from .core.types import ProcessingResult
from .models.config import APIConfig

__all__ = [
    'FluxKontextAlgorithm',
    'FluxUltraAlgorithm',
    'GeminiAlgorithm',
    'ProcessingResult',
    'APIConfig'
]
```

#### 1.2. Type Definitions (`core/types.py`)
```python
from typing import TypedDict, Literal, Optional, Tuple
from enum import Enum

class TileSize(Enum):
    """Supported tile sizes."""
    SMALL = (512, 512)
    MEDIUM = (1024, 1024)
    LARGE = (2048, 2048)
    WIDE = (1280, 720)
    CANVAS = "canvas"

class ProcessingParameters(TypedDict):
    """Processing parameters."""
    api_key: str
    prompt: str
    tile_size: TileSize
    output_dir: str
    seed: Optional[int]
    save_geotiff: bool
    save_footprint: bool

class ProcessingResult(TypedDict):
    """Processing result."""
    success: bool
    output_path: Optional[str]
    error: Optional[str]
    metadata: dict
```

### Step 2: Core Functionality

#### 2.1. Canvas Rendering (`core/rendering/canvas.py`)
```python
import os
from typing import Tuple
from qgis.core import QgsRectangle
from PIL import Image

class CanvasRenderer:
    """Handles rendering of QGIS canvas to image."""
    
    def __init__(self):
        self._validate_dependencies()
    
    def _validate_dependencies(self):
        """Validate required dependencies."""
        try:
            from qgis.utils import iface
            from qgis.core import QgsMapSettings
        except ImportError as e:
            raise RuntimeError(f"QGIS dependencies missing: {e}") from e
    
    def render_canvas(
        self,
        extent: QgsRectangle,
        width: int,
        height: int,
        output_path: str
    ) -> str:
        """Render QGIS canvas to PNG file."""
        # Implementation with proper error handling
        pass
    
    def create_fallback_image(
        self,
        width: int,
        height: int,
        output_path: str
    ) -> str:
        """Create fallback image if rendering fails."""
        img = Image.new('RGBA', (width, height), (100, 150, 200, 255))
        # Add demo text
        img.save(output_path, 'PNG')
        return output_path
```

#### 2.2. API Base Client (`api/base.py`)
```python
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import requests

class BaseAPIClient(ABC):
    """Abstract base class for API clients."""
    
    def __init__(self, api_key: str, endpoint: str):
        self.api_key = api_key
        self.endpoint = endpoint.rstrip('/')
        self.logger = logging.getLogger(self.__class__.__name__)
        self._setup_session()
    
    def _setup_session(self):
        """Setup requests session with retry logic."""
        self.session = requests.Session()
        # Add retry logic, timeout configuration
    
    @abstractmethod
    def process(
        self,
        input_path: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process image through API."""
        pass
    
    def _handle_error(self, error: Exception) -> Dict[str, Any]:
        """Handle API errors consistently."""
        self.logger.error(f"API error: {error}")
        return {
            'success': False,
            'error': str(error),
            'output_path': None
        }
```

### Step 3: API Implementations

#### 3.1. Flux Kontext API (`api/flux/kontext.py`)
```python
import base64
from typing import Dict, Any
from ..base import BaseAPIClient

class FluxKontextClient(BaseAPIClient):
    """Flux Kontext API client."""
    
    def __init__(self, api_key: str):
        super().__init__(
            api_key,
            "https://api.eu.bfl.ai"
        )
    
    def process(
        self,
        input_path: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process image with Flux Kontext API."""
        try:
            # Read and encode image
            with open(input_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('ascii')
            
            # Build payload
            payload = {
                'input_image': image_data,
                'prompt': parameters['prompt'],
                'safety_tolerance': parameters.get('safety_tolerance', 2),
                'aspect_ratio': parameters.get('aspect_ratio', '1:1')
            }
            
            # Add seed if provided
            if 'seed' in parameters:
                payload['seed'] = parameters['seed']
            
            # Send request
            response = self.session.post(
                f"{self.endpoint}/v1/flux-kontext-pro",
                json=payload,
                headers={'x-key': self.api_key},
                timeout=60
            )
            
            response.raise_for_status()
            result = response.json()
            
            # Handle polling and download
            # ... implementation
            
            return {
                'success': True,
                'output_path': output_path,
                'metadata': result
            }
            
        except Exception as e:
            return self._handle_error(e)
```

### Step 4: QGIS Algorithm Implementation

#### 4.1. Base Algorithm (`algorithms/base.py`)
```python
from qgis.core import QgsProcessingAlgorithm
from ..core.types import ProcessingParameters

class BaseFluxAlgorithm(QgsProcessingAlgorithm):
    """Base class for all FLUX algorithms."""
    
    API_KEY = "API_KEY"
    PROMPT = "PROMPT"
    TILE_SIZE = "TILE_SIZE"
    OUTPUT_DIR = "OUTPUT_DIR"
    
    def __init__(self):
        super().__init__()
        self._setup_parameters()
    
    def _setup_parameters(self):
        """Setup common parameters."""
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
        
        # Tile size parameter
        # ... implementation
    
    def processAlgorithm(self, parameters, context, feedback):
        """Process the algorithm."""
        # Extract parameters
        # Validate inputs
        # Execute processing pipeline
        # Return results
        pass
```

### Step 5: Complete Implementation Plan

#### 5.1. File Creation Order

1. **Package Foundation**
   - `__init__.py`
   - `py.typed`
   - `core/types.py`
   - `core/exceptions.py`

2. **Core Functionality**
   - `core/rendering/canvas.py`
   - `core/rendering/tile.py`
   - `core/processing/pipeline.py`
   - `core/processing/georeferencing.py`
   - `core/loading/qgis_loader.py`
   - `core/loading/format_conversion.py`

3. **API Layer**
   - `api/base.py`
   - `api/flux/kontext.py`
   - `api/flux/ultra.py`
   - `api/gemini.py`

4. **QGIS Integration**
   - `algorithms/base.py`
   - `algorithms/flux_kontext.py`
   - `algorithms/flux_ultra.py`
   - `algorithms/gemini.py`

5. **Models**
   - `models/config.py`
   - `models/result.py`

6. **Utilities**
   - `utils/geometry.py`
   - `utils/logging.py`
   - `utils/validation.py`

#### 5.2. Testing Strategy

```python
# Example test structure
import pytest
from qgis_flux.core.rendering.canvas import CanvasRenderer

class TestCanvasRenderer:
    def test_render_canvas(self, tmp_path):
        renderer = CanvasRenderer()
        extent = QgsRectangle(0, 0, 100, 100)
        output = tmp_path / "test.png"
        
        result = renderer.render_canvas(extent, 512, 512, str(output))
        assert output.exists()
        assert result == str(output)
    
    def test_fallback_image(self, tmp_path):
        renderer = CanvasRenderer()
        output = tmp_path / "fallback.png"
        
        result = renderer.create_fallback_image(512, 512, str(output))
        assert output.exists()
        assert result == str(output)
```

## 🎯 Modern Features to Implement

### 1. Dependency Injection
```python
from typing import Protocol

class APIClientProtocol(Protocol):
    def process(self, input_path: str, parameters: dict) -> dict:
        ...

class ProcessingPipeline:
    def __init__(self, api_client: APIClientProtocol):
        self.api_client = api_client
    
    def execute(self, input_path: str, parameters: dict):
        return self.api_client.process(input_path, parameters)
```

### 2. Async Support
```python
import asyncio
from aiohttp import ClientSession

class AsyncAPIClient:
    async def process(self, input_path: str, parameters: dict):
        async with ClientSession() as session:
            # Async API call
            pass
```

### 3. Configuration Management
```python
from pydantic import BaseSettings

class PluginSettings(BaseSettings):
    api_endpoint: str = "https://api.eu.bfl.ai"
    max_retries: int = 3
    timeout: int = 60
    debug_mode: bool = False
    
    class Config:
        env_file = ".env"
        env_prefix = "FLUX_"
```

## 📝 Implementation Timeline

### Phase 1: Foundation (2-3 days)
- Package structure setup
- Type definitions and exceptions
- Core utility functions
- Basic testing framework

### Phase 2: Core Functionality (3-4 days)
- Canvas rendering implementation
- API client implementations
- Processing pipeline
- Result loading and georeferencing

### Phase 3: QGIS Integration (2-3 days)
- Algorithm implementations
- Parameter configuration
- User interface integration
- QGIS-specific functionality

### Phase 4: Testing & Quality (2-3 days)
- Comprehensive unit tests
- Integration tests
- Code quality checks
- Documentation

### Phase 5: Deployment (1 day)
- Package building
- QGIS plugin configuration
- Final testing
- Release preparation

## ✨ Benefits of New Structure

1. **Clean Separation**: Clear division between core logic and QGIS integration
2. **Type Safety**: Full type hints throughout
3. **Testability**: Easy to test individual components
4. **Extensibility**: Simple to add new APIs or features
5. **Maintainability**: Professional code organization
6. **Modern Practices**: Dependency injection, async support, configuration management
7. **No Legacy Constraints**: Complete freedom to implement best practices

## 🚀 Next Steps

1. **Create package structure**: Set up all directories and files
2. **Implement core types**: Define data models and interfaces
3. **Build utility functions**: Geometry, logging, validation
4. **Develop API clients**: Flux and Gemini implementations
5. **Create processing pipeline**: Main workflow logic
6. **Implement QGIS algorithms**: Algorithm classes
7. **Write comprehensive tests**: Unit and integration tests
8. **Document everything**: Complete documentation
9. **Test and validate**: Ensure everything works correctly

This plan provides a complete blueprint for building a modern, professional QGIS FLUX plugin from scratch with no backward compatibility constraints.