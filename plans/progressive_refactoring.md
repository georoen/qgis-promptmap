# Progressive Refactoring Plan for QGIS FLUX

## Key Principles

1. **Preserve all existing functionality** - No feature loss
2. **Maintain API-specific options** - Flux-specific parameters like image strength will be enhanced, not removed
3. **Progressive approach** - Small, testable steps
4. **Backward compatibility** - Existing code continues to work during transition

## Understanding the Unified API Approach

The unified API base class **does not remove** API-specific functionality. Instead, it:

```python
# Current approach (duplication)
class FluxEngine:
    def send_request(self, payload):
        # Common code for all APIs
        # Flux-specific code
        
class GeminiEngine:
    def send_request(self, payload):
        # Common code for all APIs (DUPLICATED!)
        # Gemini-specific code

# Proposed approach (unified with extensions)
class BaseAPIClient:
    def send_request(self, payload):
        # Common code for all APIs (shared)
        self._validate_payload(payload)
        self._handle_auth()
        self._handle_retry_logic()
        
    def _get_api_specific_params(self):
        # To be overridden by subclasses
        return {}

class FluxAPIClient(BaseAPIClient):
    def _get_api_specific_params(self):
        return {
            'image_prompt_strength': 0.8,  # Flux-specific!
            'safety_tolerance': 2,         # Flux-specific!
            'aspect_ratio': '1:1'          # Flux-specific!
        }

class GeminiAPIClient(BaseAPIClient):
    def _get_api_specific_params(self):
        return {
            'generationConfig': {           # Gemini-specific!
                'imageConfig': {
                    'aspectRatio': '1:1',
                    'imageSize': '2K'
                }
            }
        }
```

## Progressive Refactoring Phases

### Phase 1: Core Structure Cleanup (Safe, No Functional Changes)
**Goal**: Improve organization without changing functionality

1. **Create new simplified directory structure**
   ```
   qgis_flux/
   ├── core/                  # New structure
   │   ├── __init__.py
   │   ├── algorithm.py       # Copy of current base_ai_algorithm.py
   │   ├── rendering.py      # Copy of PREPARE/rendering.py
   │   └── loading.py         # Copy of INTEGRATE/loader.py
   ├── legacy/                # Old structure (kept working)
   │   ├── PREPARE/
   │   ├── PROCESS/
   │   └── INTEGRATE/
   └── models/                # API configurations
       ├── __init__.py
       ├── flux_kontext.py    # Copy of PROCESS/flux/config.py
       └── flux_ultra.py       # Copy of PROCESS/flux/config.py
   ```

2. **Update imports in main algorithm** to use new paths
3. **Test thoroughly** - Ensure no functionality is broken
4. **Remove legacy directories** only after confirmation

**Benefits**: 
- Cleaner structure immediately
- No risk to existing functionality
- Easy to rollback if needed

### Phase 2: Unified API Base with Model-Specific Extensions
**Goal**: Reduce code duplication while preserving API-specific features

1. **Create base API client** (`core/api/base.py`)
   - Common functionality: authentication, retry logic, error handling
   - Abstract methods for API-specific implementations

2. **Create Flux-specific implementation** (`core/api/flux.py`)
   - Inherits from base
   - Implements Flux-specific parameters (image_prompt_strength, safety_tolerance, etc.)
   - Preserves all current Flux functionality

3. **Create Gemini-specific implementation** (`core/api/gemini.py`)
   - Inherits from base  
   - Implements Gemini-specific parameters
   - Currently incomplete - can be enhanced later

4. **Update algorithm classes** to use new API clients
5. **Test each API separately** to ensure all parameters work correctly

**Key Design**:
```python
# In flux.py
class FluxAPIClient(BaseAPIClient):
    def __init__(self, model_type='kontext'):
        super().__init__()
        self.model_type = model_type
        
        # Model-specific default parameters
        if model_type == 'kontext':
            self.default_params = {
                'safety_tolerance': 2,
                'aspect_ratio': '1:1'
            }
        elif model_type == 'ultra':
            self.default_params = {
                'image_prompt_strength': 0.8,
                'safety_tolerance': 2,
                'aspect_ratio': '1:1'
            }
    
    def get_model_specific_ui_params(self):
        """Returns UI parameters specific to this Flux model"""
        params = []
        
        if self.model_type == 'ultra':
            params.append({
                'name': 'IMAGE_STRENGTH',
                'type': 'number',
                'label': 'Image Prompt Strength',
                'default': 0.8,
                'min': 0.1,
                'max': 1.0
            })
        
        # Common Flux parameters
        params.append({
            'name': 'SAFETY_TOLERANCE',
            'type': 'number',
            'label': 'Safety Tolerance',
            'default': 2,
            'min': 0,
            'max': 6
        })
        
        return params
```

### Phase 3: Gradual Migration of Existing Functionality
**Goal**: Move functionality piece by piece with testing at each step

1. **Start with utility functions** (geometry, georeferencing)
2. **Move rendering functionality** 
3. **Migrate API communication**
4. **Update loading/integration**
5. **Test after each migration step**

### Phase 4: Enhancement and Future-Proofing
**Goal**: Add features and improve maintainability

1. **Add advanced parameter support** for all APIs
2. **Improve error handling** and user feedback
3. **Add comprehensive logging**
4. **Enhance testing** coverage
5. **Document new architecture**

## Risk Mitigation Strategy

### Low Risk Changes (Do First)
- Directory restructuring (can be reverted)
- Code organization improvements
- Documentation updates

### Medium Risk Changes (Do with Testing)
- API client refactoring
- Import path changes
- Interface modifications

### High Risk Changes (Avoid or Do Last)
- Major logic changes
- Breaking API changes
- Database/schema modifications

## Testing Strategy

1. **Unit tests** for each component
2. **Integration tests** for workflows
3. **Manual testing** in QGIS for each phase
4. **Regression testing** to ensure no functionality lost

## Timeline Estimate

This is a progressive approach that can be done in stages:
- Phase 1: 1-2 days (immediate improvement)
- Phase 2: 3-5 days (API unification with full testing)
- Phase 3: 2-3 days (gradual migration)
- Phase 4: Ongoing (enhancements)

## Benefits of This Approach

1. **Immediate improvement** in code organization
2. **No feature loss** - all API-specific options preserved
3. **Easier to add new APIs** in the future
4. **Better maintainability** with reduced duplication
5. **Progressive** - can stop at any phase if needed
6. **Testable** - each phase can be verified independently

## Next Steps

I recommend starting with **Phase 1** as it provides immediate benefits with minimal risk. Would you like me to implement Phase 1 now?