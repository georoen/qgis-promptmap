# Contributions welcome

Thanks for helping keep the toolbox sharp. A few notes before you open a PR.

## Architecture primer

1. **PREPARE** – `BaseAiAlgorithm` renders the visible QGIS canvas to PNG using the tile
   preset you choose (512², 1024², 2048², 16:9, or full canvas). It also derives the
   aspect ratio that gets forwarded to the API.
2. **PROCESS** – `RemoteAiEngine` uploads the PNG plus your prompt/advanced options
   (seed, safety tolerance, raw mode, image prompt strength) and polls the FLUX endpoint
   until the job finishes.
3. **INTEGRATE** – the PNG is downloaded, georeferenced via PGW, optionally VRT’d in the
   future, and injected back into QGIS under the “AI Results” group.

PNG is enforced throughout so transparency and georeferencing remain predictable.

## Development workflow

1. Fork/clone the repo into `~/Desktop/qgis_flux` (or update paths in README accordingly).
2. Copy the folder into your QGIS profile’s `python/plugins/` directory, restart QGIS,
   and enable **AI Toolbox**.
3. Iterate on code, then run the unit tests:

   ```bash
   python3 -m pytest tests -v
   ```

   Tests mock QGIS/FLUX internals (polling, world files, logging). Whenever you modify
   Processing parameters or UX, run a quick smoke test inside QGIS because the dialog
   requires a live canvas.

  ```bash
  QGIS_PLUGINS_DIR="$HOME/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/"
  rm -rf "$QGIS_PLUGINS_DIR/qgis_flux/"
  rsync -av --exclude='.*' "$PWD" "$QGIS_PLUGINS_DIR"
  ```
  Then restart QGIS.

4. Document user-facing changes in `README.md` and keep the FLUX parameter reference up
   to date in [`docs/flux_models.md`](flux_models.md).

## Filing issues / PRs

- Include screenshots or log snippets when reporting UI/API regressions.
- For feature PRs, describe the user story (“why would a mapper care?”) and update the
  metadata/README copy if the positioning changes.
- Keep linting simple—follow the existing formatting style (black-compatible, UTF-8).

Happy hacking!
