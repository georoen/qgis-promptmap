# API Key Handling — Developer Notes

## Current state (v0.5.1)

The API Key parameter in every PromptMap algorithm is pre-filled from environment variables. This is implemented in [`clients/base.py`](../clients/base.py) inside `BaseAIAlgorithm.initAlgorithm()`:

```python
default_key = (
    environ.get("BFL_API_KEY")
    or environ.get("GEMINI_API_KEY")
    or environ.get("PROMPTMAP_API_KEY")
    or ""
)
self.addParameter(QgsProcessingParameterString(
    self.API_KEY, "API Key", defaultValue=default_key, optional=False
))
```

**Priority order:** `BFL_API_KEY` → `GEMINI_API_KEY` → `PROMPTMAP_API_KEY` → empty string.

**Known limitation:** The base class reads all three env vars and uses the first non-empty one. This means if a user has both `BFL_API_KEY` and `GEMINI_API_KEY` set, the Gemini algorithm will also pre-fill with the BFL key (wrong). The user can override it in the dialog, but it's not ideal UX.

## What needs to be improved

### Option A — Per-algorithm env var (recommended, minimal change)

Each algorithm subclass should override `initAlgorithm()` to read its own env var:

```python
# In Flux1KontextProAlgorithm, Flux1_1UltraProAlgorithm, Flux2EditingAlgorithm:
def initAlgorithm(self, config=None):
    default_key = os.environ.get("BFL_API_KEY", "")
    self.addParameter(QgsProcessingParameterString(
        self.API_KEY, "API Key", defaultValue=default_key, optional=False
    ))
    # ... rest of super().initAlgorithm() parameters

# In Gemini3ProImageAlgorithm:
def initAlgorithm(self, config=None):
    default_key = os.environ.get("GEMINI_API_KEY", "")
    self.addParameter(QgsProcessingParameterString(
        self.API_KEY, "API Key", defaultValue=default_key, optional=False
    ))
    # ... rest of super().initAlgorithm() parameters
```

This requires refactoring `BaseAIAlgorithm.initAlgorithm()` to accept a `default_key` parameter, or moving the API_KEY parameter addition to each subclass.

**Cleanest approach:** Add a `_api_key_env_var()` method to `BaseAIAlgorithm` that subclasses override:

```python
# In BaseAIAlgorithm:
def _api_key_env_var(self) -> str:
    """Return the environment variable name for this algorithm's API key."""
    return "PROMPTMAP_API_KEY"

def initAlgorithm(self, config=None):
    default_key = os.environ.get(self._api_key_env_var(), "")
    self.addParameter(QgsProcessingParameterString(
        self.API_KEY, "API Key", defaultValue=default_key, optional=False
    ))
    # ...

# In Flux1KontextProAlgorithm (and other BFL clients):
def _api_key_env_var(self) -> str:
    return "BFL_API_KEY"

# In Gemini3ProImageAlgorithm:
def _api_key_env_var(self) -> str:
    return "GEMINI_API_KEY"
```

### Option B — `QgsSettings` (persistent, no env var needed)

Store the key in the QGIS user profile INI file. Survives QGIS restarts without needing shell config:

```python
from qgis.core import QgsSettings

# Read
settings = QgsSettings()
default_key = settings.value("promptmap/bfl_api_key", "")

# Save after successful run (in processAlgorithm):
settings.setValue("promptmap/bfl_api_key", api_key)
```

**Downside:** Key stored in plain text in `QGIS3.ini`. Not suitable for shared machines.

### Option C — QGIS Authentication Manager (most secure)

Uses QGIS's encrypted credential store. Requires the user to set a master password. Most complex to implement. Overkill for a single API key.

## Testing the current env var feature

The feature was implemented but **not tested in QGIS** before the v0.5.1 release. To verify:

1. Set `export BFL_API_KEY="sk-test-123"` in your shell
2. Start QGIS from that shell (not from Finder/Spotlight on macOS — those don't inherit shell env vars)
3. Open Processing Toolbox → PromptMap → FLUX.1 Kontext [pro]
4. Verify the API Key field is pre-filled with `sk-test-123`

**macOS note:** QGIS launched from Finder does NOT inherit shell environment variables. Users need to either:
- Launch QGIS from Terminal: `open -a QGIS`
- Or use a QGIS startup script (`~/.qgis3/startup.py`) to set the env var programmatically

This is a known macOS limitation and should be documented in the README if Option A is implemented.

## Recommended next steps

1. Implement Option A (`_api_key_env_var()` method pattern) — clean, minimal, correct
2. Test on macOS and document the "launch from Terminal" requirement
3. Consider adding a note in the Processing dialog description about the env var
4. Long-term: evaluate Option B (`QgsSettings`) for a better UX without shell config
