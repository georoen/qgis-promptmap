# Contributions welcome

Thanks for helping keep PromptMap sharp. A few notes before you open a PR.

## Architecture primer

1. **PREPARE** – [`BaseAIAlgorithm`](../clients/base.py) renders the visible QGIS canvas to PNG using the framing preset you choose (1:1, 16:9, or full canvas). It crops the extent to match the selected aspect ratio and encodes the image as base64. Final output pixel dimensions are API/model-dependent.
2. **PROCESS** – The algorithm subclass calls `execute_api()`, which delegates to the provider-specific API client ([`BFLAPIClient`](../clients/bfl_base.py) for FLUX models, [`Gemini3ProImageAPIClient`](../clients/gemini_3_pro_image.py) for all five Gemini models). BFL uses asynchronous polling; Gemini uses the Interactions API and returns inline data from final model-output steps. [`OpenAIImageAPIClient`](../clients/openai_image.py) uploads the rendered PNG to the Image API edit endpoint and receives base64 PNG data.
3. **INTEGRATE** – The result is downloaded or decoded, watermarked, georeferenced as a GeoTIFF via GDAL, and loaded as a new raster layer. A GeoPackage with model name, prompt, timestamp, and extent is saved alongside.

Canvas input and local output use PNG. Gemini requests JPEG from the Interactions API and converts it to PNG locally with Qt before integration; this cannot recover JPEG compression losses or transparency.

## Development workflow

1. Fork/clone the repo into `~/Desktop/promptmap` (or update paths in README accordingly).
2. Copy the folder into your QGIS profile's `python/plugins/` directory, restart QGIS, and enable **PromptMap**.

   ```bash
   # Linux, QGIS 4 default profile (use QGIS3 for QGIS 3).
   QGIS_PLUGINS_DIR="$HOME/.local/share/QGIS/QGIS4/profiles/default/python/plugins"
   # macOS: "$HOME/Library/Application Support/QGIS/QGIS4/profiles/default/python/plugins"
   mkdir -p "$QGIS_PLUGINS_DIR/promptmap"
   rsync -av --exclude='.*' --exclude='__pycache__' "$PWD/" "$QGIS_PLUGINS_DIR/promptmap/"
   ```
   Then restart QGIS.

3. Run the smoke test below, then test your changes with a live canvas inside QGIS. The Processing dialog requires a running QGIS instance.

4. Document user-facing changes in `README.md` and keep the model parameter reference up to date in [`docs/available_models.md`](available_models.md).

## Tests

Run the offline smoke test with a Python interpreter that has QGIS, Qt and GDAL installed:

```bash
QT_QPA_PLATFORM=offscreen python3 tests/smoke_qgis.py
QT_QPA_PLATFORM=offscreen python3 tests/test_gemini.py
QT_QPA_PLATFORM=offscreen python3 tests/test_openai.py
QT_QPA_PLATFORM=offscreen python3 tests/test_flux_3.py
```

The Gemini, OpenAI and FLUX 3 tests mock HTTP requests to check every model's payload, response parsing, validation, cancellation, and errors without spending API credits. They do not verify live service availability or image quality.

The smoke test checks provider registration, map rendering, watermarking, GeoTIFF conversion and GeoPackage metadata export. It does not call paid AI APIs or test the interactive UI. See [`docs/env_vars.md`](env_vars.md) for live API setup.

## Filing issues / PRs

- Include screenshots or log snippets when reporting UI/API regressions.
- For feature PRs, describe the user story ("why would a mapper care?") and update the metadata/README copy if the positioning changes.
- Keep linting simple — follow the existing formatting style (black-compatible, UTF-8).

Happy hacking!
