# QGIS FLUX AI Toolbox - Comprehensive Requirements Specification

## 🎯 Core Objective

Create a **modern, clean, professional** QGIS plugin for AI-powered map processing with:
- **No backward compatibility constraints**
- **From-scratch design** based on extracted functionality
- **Professional code quality** (type hints, docstrings, testing)
- **Modern Python practices** (clean architecture, dependency injection)
- **Easy maintenance and extension**

## 🔍 Functionality Extraction

### Current Core Functionality to Preserve

1. **Canvas Rendering**
   - Capture current QGIS canvas extent
   - Render to PNG with proper resolution
   - Handle different tile sizes (512, 1024, 2048, 16:9, full canvas)
   - Aspect ratio preservation

2. **API Communication**
   - Flux Kontext API integration
   - Flux Ultra API integration  
   - Gemini 3 Pro Image API integration
   - Authentication (API keys)
   - Request/response handling
   - Error handling and retries

3. **Result Processing**
   - Download and save processed images
   - Georeferencing with world files
   - GeoTIFF conversion (optional)
   - Footprint GPKG generation (optional)
   - Load results back into QGIS

4. **User Interface**
   - QGIS Processing Algorithm integration
   - Parameter configuration
   - Progress feedback
   - Error reporting

## 🏗️ New Package Structure

```
qgis_flux/
├── __init__.py                    # Main package entry
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

## 📋 Detailed Requirements

### 1. Core Functionality

#### Canvas Rendering
- **Input**: QGIS canvas extent, resolution parameters
- **Output**: PNG image with transparency
- **Features**:
  - Multiple tile size presets (512×512, 1024×1024, 2048×2048, 1280×720)
  - Full canvas option
  - Aspect ratio preservation
  - Error handling with fallback

#### API Processing
- **Flux Kontext**: Image editing with instruction prompts
- **Flux Ultra**: Artistic generation with style prompts
- **Gemini**: Multi-modal image generation
- **Common Features**:
  - API key management
  - Request signing and authentication
  - Retry logic with exponential backoff
  - Progress tracking
  - Error handling and reporting

#### Result Handling
- **Georeferencing**: World file generation (.pgw)
- **Format Conversion**: PNG → GeoTIFF (optional)
- **Metadata**: Footprint GPKG with processing metadata
- **QGIS Integration**: Automatic layer loading

### 2. Technical Requirements

#### Python Version
- **Minimum**: Python 3.8+
- **Recommended**: Python 3.9+

#### Dependencies
```requirements.txt
# Core dependencies
qgis>=3.20
requests>=2.25.0
Pillow>=8.0.0

# Optional dependencies
gdal>=3.0.0

# Development dependencies
types-requests>=2.25.0
pytest>=6.0.0
mypy>=0.900
ruff>=0.0.200
black>=22.0.0
isort>=5.0.0
```

#### Type Safety
- **Full type hints** for all public functions
- **Type checking** with mypy
- **Runtime type validation** for critical paths

#### Code Quality
- **Formatting**: Black code style
- **Linting**: Ruff with strict rules
- **Imports**: isort sorting
- **Documentation**: Google-style docstrings

### 3. API Specifications

#### Flux Kontext API
- **Endpoint**: `https://api.eu.bfl.ai/v1/flux-kontext-pro`
- **Authentication**: `x-key` header
- **Parameters**:
  - `input_image` (base64)
  - `prompt` (string)
  - `safety_tolerance` (0-6)
  - `aspect_ratio` (string)
  - `seed` (integer, optional)

#### Flux Ultra API
- **Endpoint**: `https://api.eu.bfl.ai/v1/flux-pro-1.1-ultra`
- **Authentication**: `x-key` header
- **Parameters**:
  - `image_prompt` (base64)
  - `prompt` (string)
  - `image_prompt_strength` (0.1-1.0)
  - `safety_tolerance` (0-6)
  - `aspect_ratio` (string)
  - `seed` (integer, optional)

#### Gemini 3 Pro Image API
- **Endpoint**: `https://generativelanguage.googleapis.com/v1beta/models/gemini-3-pro-image-preview:generateContent`
- **Authentication**: `x-goog-api-key` header
- **Parameters**:
  - `contents` with text and image parts
  - `generationConfig` with image settings

### 4. QGIS Integration

#### Processing Algorithm Requirements
- **Algorithm ID**: Unique identifier for each algorithm
- **Display Name**: User-friendly name
- **Group**: "FLUX AI Processing" or "Gemini AI Processing"
- **Parameters**:
  - API Key (required)
  - Prompt (required, multiline)
  - Tile Size (dropdown)
  - Output Directory (optional)
  - Seed (optional)
  - Save GeoTIFF (boolean)
  - Save Footprint (boolean)
  - Model-specific parameters

#### User Experience
- **Progress Feedback**: Real-time progress updates
- **Error Handling**: Clear error messages
- **Validation**: Input validation before processing
- **Defaults**: Sensible default values

### 5. Error Handling

#### Error Categories
- **Input Errors**: Invalid parameters, missing API key
- **Rendering Errors**: Canvas rendering failures
- **API Errors**: Authentication, rate limiting, timeouts
- **Processing Errors**: Image processing failures
- **Output Errors**: File writing permissions

#### Error Recovery
- **Retry Logic**: Automatic retries for transient errors
- **Fallback**: Graceful degradation where possible
- **User Notification**: Clear error messages with recovery suggestions

### 6. Testing Requirements

#### Unit Tests
- **Coverage**: 90%+ code coverage
- **Isolation**: Mock external dependencies
- **Speed**: Fast execution (<1s per test)

#### Integration Tests
- **End-to-end**: Complete workflow testing
- **API Mocking**: Simulated API responses
- **QGIS Mocking**: Simulated QGIS environment

#### Test Data
- **Sample Images**: Test images for rendering
- **API Responses**: Mock API responses
- **Configurations**: Test configuration files

### 7. Documentation

#### Code Documentation
- **Docstrings**: Google-style for all public functions
- **Type Hints**: Complete type annotations
- **Comments**: Explanatory comments for complex logic

#### User Documentation
- **README**: Installation and usage guide
- **API Reference**: Parameter documentation
- **Examples**: Usage examples
- **Troubleshooting**: Common issues and solutions

### 8. Performance Requirements

#### Processing Times
- **Small Tiles (512×512)**: <5 seconds (excluding API time)
- **Large Tiles (2048×2048)**: <10 seconds (excluding API time)
- **Memory Usage**: <500MB for typical operations

#### Scalability
- **Concurrent Operations**: Support for multiple simultaneous processes
- **Resource Management**: Proper cleanup of resources
- **Batch Processing**: Support for processing multiple tiles

### 9. Security Requirements

#### Data Protection
- **API Keys**: Secure handling (no logging, no storage in plain text)
- **User Data**: No collection of personal data
- **Network**: HTTPS for all API communications

#### Privacy
- **No Telemetry**: No usage tracking
- **No Analytics**: No data collection
- **Transparent**: Clear about data handling

### 10. Deployment Requirements

#### Package Structure
- **Single Package**: All functionality in one package
- **No External Dependencies**: Minimal required dependencies
- **Easy Installation**: Standard Python package installation

#### QGIS Plugin Requirements
- **Plugin Metadata**: Proper metadata.txt
- **Icon**: High-quality plugin icon
- **Resources**: Proper resource handling
- **Compatibility**: QGIS 3.20+ compatibility

## 🎯 Implementation Priorities

### Phase 1: Core Infrastructure
1. **Package Structure**: Set up clean package layout
2. **Type Definitions**: Define all data types
3. **Base Classes**: Implement core abstractions
4. **Utility Functions**: Geometry, logging, validation

### Phase 2: Core Functionality
1. **Canvas Rendering**: Implement tile rendering
2. **API Clients**: Implement all API integrations
3. **Processing Pipeline**: Build main workflow
4. **Result Handling**: Georeferencing and loading

### Phase 3: QGIS Integration
1. **Algorithm Implementations**: Create QGIS algorithms
2. **Parameter Definitions**: Set up UI parameters
3. **User Interface**: Configure dialogs and forms
4. **Integration Testing**: Test QGIS integration

### Phase 4: Testing & Quality
1. **Unit Tests**: Comprehensive test coverage
2. **Integration Tests**: End-to-end testing
3. **Code Quality**: Linting, formatting, type checking
4. **Documentation**: Complete all documentation

## ✨ Modern Features to Implement

### 1. Dependency Injection
- **Configurable Components**: Swappable implementations
- **Testability**: Easy mocking for testing
- **Flexibility**: Different configurations for different environments

### 2. Async/Await Support
- **Asynchronous API Calls**: Non-blocking API communication
- **Progress Updates**: Real-time progress reporting
- **Cancellation**: Support for operation cancellation

### 3. Configuration Management
- **Environment Variables**: Configurable through env vars
- **Configuration Files**: JSON/YAML configuration support
- **Runtime Configuration**: Dynamic configuration changes

### 4. Logging & Monitoring
- **Structured Logging**: JSON logging format
- **Log Levels**: Configurable verbosity
- **Performance Metrics**: Operation timing and metrics

### 5. Internationalization
- **Multi-language Support**: i18n ready
- **Localization**: Easy translation support
- **Locale Detection**: Automatic locale handling

## 📝 Implementation Notes

### Design Principles
- **Single Responsibility**: Each class/module does one thing well
- **Open/Closed**: Open for extension, closed for modification
- **Dependency Inversion**: High-level modules don't depend on low-level details
- **Interface Segregation**: Clients shouldn't depend on interfaces they don't use

### Coding Standards
- **Python**: PEP 8 compliance
- **Type Hints**: PEP 484 compliance
- **Docstrings**: Google style
- **Imports**: Absolute imports, grouped by type

### Testing Strategy
- **TDD Approach**: Test-driven development where appropriate
- **Mocking**: Use unittest.mock for external dependencies
- **Property Testing**: Hypothesis for edge case testing
- **Performance Testing**: Benchmark critical operations

## 🚀 Next Steps

1. **Create New Package Structure**: Set up clean directory layout
2. **Implement Core Types**: Define data models and interfaces
3. **Build Base Classes**: Create abstract base classes
4. **Implement Utilities**: Geometry, logging, validation
5. **Develop API Clients**: Flux and Gemini implementations
6. **Create Processing Pipeline**: Main workflow logic
7. **Build QGIS Algorithms**: Algorithm implementations
8. **Write Comprehensive Tests**: Unit and integration tests
9. **Document Everything**: Complete documentation
10. **Test and Validate**: Ensure everything works correctly

This specification provides a complete blueprint for building a modern, professional QGIS FLUX plugin from scratch with no backward compatibility constraints.