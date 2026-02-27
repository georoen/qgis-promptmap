# Contributions welcome

Thanks for helping keep PromptMap sharp. A few notes before you open a PR.

## Architecture primer

1. **PREPARE** – [`BaseAIAlgorithm`](../clients/base.py) renders the visible QGIS canvas to PNG using the tile preset you choose (512², 1024², 2048², 16:9, or full canvas). It crops the extent to match the selected aspect ratio and encodes the image as base64.
2. **PROCESS** – The algorithm subclass calls `execute_api()`, which delegates to the provider-specific API client ([`BFLAPIClient`](../clients/bfl_base.py) for FLUX models, [`Gemini3ProImageAPIClient`](../clients/gemini_3_pro_image.py) for Gemini). BFL uses asynchronous polling; Gemini returns inline data.
3. **INTEGRATE** – The result is downloaded or decoded, watermarked, georeferenced as a GeoTIFF via GDAL, and loaded as a new raster layer. A GeoPackage with model name, prompt, timestamp, and extent is saved alongside.

PNG is enforced throughout so transparency and georeferencing remain predictable.

## Development workflow

1. Fork/clone the repo into `~/Desktop/promptmap` (or update paths in README accordingly).
2. Copy the folder into your QGIS profile's `python/plugins/` directory, restart QGIS, and enable **PromptMap**.

   ```bash
   QGIS_PLUGINS_DIR="$HOME/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/"
   rm -rf "$QGIS_PLUGINS_DIR/promptmap/"
   rsync -av --exclude='.*' "$PWD" "$QGIS_PLUGINS_DIR"
   ```
   Then restart QGIS.

3. Test your changes with a live canvas inside QGIS. The Processing dialog requires a running QGIS instance — there are currently no automated unit tests (see below).

4. Document user-facing changes in `README.md` and keep the model parameter reference up to date in [`docs/flux_models.md`](flux_models.md).

## Tests

The `tests/` directory was removed in v0.5.0 because the old test suite targeted a module (`flux_stylize_tiles`) that no longer exists. New tests covering [`clients/base.py`](../clients/base.py) and the API clients are planned for a future release. See [`docs/env_vars.md`](env_vars.md) for notes on what to test.

## Filing issues / PRs

- Include screenshots or log snippets when reporting UI/API regressions.
- For feature PRs, describe the user story ("why would a mapper care?") and update the metadata/README copy if the positioning changes.
- Keep linting simple — follow the existing formatting style (black-compatible, UTF-8).

Happy hacking!
