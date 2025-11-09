# QGIS FLUX AI Toolbox

Turn your current QGIS canvas into a high-contrast land-cover rendering with a single
Processing algorithm. The plugin captures the visible map, sends it to FLUX.1 Kontext or
FLUX 1.1 [pro] Ultra, and loads the returned PNG back into your project with proper
georeferencing. The default prompt emphasises buildings, roads, vegetation, soil, and
water—perfect for quick site analysis or presentation graphics.

---

## Why cartographers love it

- **Semantic look** – ships with a shared remote-sensing prompt so both models behave
  like lightweight land-cover classifiers.
- **Canvas-aware** – respects your current map view, including aspect ratio and CRS.
- **Two FLUX brains** – switch between Kontext (image editing) and Ultra (stylisation)
  without rewriting prompts.
- **Clean UX** – only API Key + Prompt are required; everything else sits behind the
  Processing “Advanced” toggle.

---

## Quickstart

1. **Install the plugin**
   ```bash
   rm -rf ~/Library/Application\ Support/QGIS/QGIS3/profiles/default/python/plugins/qgis_flux/
   cp -r /Users/jstaab/Desktop/qgis_flux \
         ~/Library/Application\ Support/QGIS/QGIS3/profiles/default/python/plugins/
   ```
   Then restart QGIS and enable *qgis_flux* under **Plugins → Manage and Install…**

2. **Grab an API key** from <https://api.bfl.ai/> (needs FLUX pro credit). Paste it into
   the Processing dialog every time or store it via the QGIS **Favorites** feature.

3. **Open the Processing Toolbox → FLUX AI Processing** and pick either *FLUX 1.1 Ultra*
   or *FLUX.1 Kontext*. Leave the default prompt in place for semantic segmentation or
   tweak it to your needs. Hit **Run**.

You’ll find the PNG result (plus its world file and log) in the chosen output folder, and
the layer loads automatically under an “AI Results” group.

---

## Workflow in three steps

1. **PREPARE** – `BaseAiAlgorithm` renders the current canvas extent to PNG based on the
   tile size you picked (512², 1024², 2048², 16:9, or full canvas). Aspect ratio is
   derived automatically and sent to the API.
2. **PROCESS** – `RemoteAiEngine` uploads the PNG together with your prompt and advanced
   settings (seed, safety tolerance, raw mode, image prompt strength) and polls the FLUX
   endpoint until the job is ready.
3. **INTEGRATE** – the PNG is downloaded, georeferenced (PNG + PGW), optionally VRT’d in
   the future, and inserted back into QGIS with the same extent you just processed.

We always request PNG output to keep transparency/headless workflows simple.

---

## Parameters

| Parameter | Default | Notes |
| --- | --- | --- |
| **FLUX API Key** | — | Required. Obtain from <https://api.bfl.ai/>. |
| **Prompt** | Remote-sensing land-cover prompt | Shared constant documented in `flux_api_config.py`; feel free to edit per run. |
| **Tile Size** *(Advanced)* | `1024×1024 (1:1)` | Preset pixel sizes plus “Map Canvas (Full Extent)”. Determines rendered resolution **and** the `aspect_ratio` sent to FLUX. |
| **Output Directory** *(Advanced)* | QGIS temp dir | Folder for PNG, PGW, and log files. |
| **Random Seed** *(Advanced)* | blank | Forwarded to both APIs when provided. |
| **Safety Tolerance** *(Advanced)* | `2` | Available in both algorithms; matches FLUX moderation scale (0–6). |
| **Raw Mode** *(Ultra only, Advanced)* | `False` | Toggles the Ultra-specific `raw` flag. |
| **Image Prompt Strength** *(Ultra only, Advanced)* | `0.8` | Float between 0–1 controlling how much the rendered canvas influences Ultra. |

Looking for the full matrix of parameters per model? See
[`docs/flux_models.md`](docs/flux_models.md) and cross-check with the official BFL docs:
Kontext (<https://docs.bfl.ai/kontext/kontext_image_editing#flux-1-kontext-image-editing-parameters>)
and Ultra (<https://docs.bfl.ai/flux/flux_pro#flux-11-ultra>).

---

## Troubleshooting

- **Plugin fails to load** – remove the plugin folder under
  `~/Library/Application Support/QGIS/QGIS3/.../plugins/qgis_flux/` and copy it again,
  then restart QGIS.
- **401 / API errors** – make sure your key starts with `sk-` and you have pro credits.
- **Timeout / Failed** – rerun later or reduce the tile size. Check the generated log in
  your output directory.
- **Nothing shows up** – ensure at least one layer is visible on the canvas; the plugin
  renders what you currently see.

---

## Development & tests

```bash
python3 -m pytest tests -v
```

The tests mock out QGIS/FLUX internals and focus on the remote-engine workflow,
polling, logging, and world-file generation. When editing Processing parameters, run a
manual smoke test inside QGIS because the UI requires a live canvas.

---

## Support & contact

- Issues / feature requests: <https://github.com/georoen/qgis-flux>
- Author: Jeroen Staab – email@jstaab.de
- Tag your renders with **#qgisflux** so we can see what you build!
