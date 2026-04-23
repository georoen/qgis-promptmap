# Originality & Comparison with Related Projects

This document clarifies the origin of PromptMap and provides a factual comparison with related AI cartography projects to demonstrate independent development.

---

## Timeline

| Date | Event | Author | Description |
|------|-------|--------|-------------|
| **Oct 11, 2025** | ai-topographic-maps initial commit | David Oesch | Standalone Python project for Swiss-style topographic map generation using Google Gemini (NanoBanana) |
| **Nov 8, 2025** | PromptMap initial commit | JSReseach | First QGIS Processing plugin for general AI cartography |
| Mar 23, 2026 | QGIS AI Edit initial commit | TerraLab | QGIS Dock Widget plugin with proprietary API backend |

---

## Three-Way Comparison

| Aspect | PromptMap | QGIS AI Edit | ai-topographic-maps |
|--------|-----------|--------------|---------------------|
| **Type** | QGIS Processing Plugin | QGIS Dock Widget Plugin | Standalone Python scripts |
| **Architecture** | Flat: `plugin.py` + `clients/*.py` | Layered: `src/api`, `core`, `ui`, `workers` | Modular scripts: `style_transfer_swissimage.py`, `stitch_tiles.py` |
| **API Providers** | Multiple: BFL (FLUX.1/2), Google Gemini | Single: TerraLab proprietary | Single: Google Gemini (NanoBanana) |
| **Focus** | General AI cartography (segmentation, mapping, synthetic imagery) | General image editing | Swiss-style topographic map generation |
| **Input** | Live QGIS canvas | Rectangle selection on QGIS canvas | WMTS tiles from swisstopo |
| **Output** | GeoTIFF + GPKG metadata layer | GeoTIFF | JPEG map tiles |
| **Authentication** | Per-provider API keys | Centralized TerraLab account | Direct Google API key |
| **Pricing Model** | Token-based (user pays providers) | Subscription (TerraLab) | Token-based (user pays Google) |
| **Vendor Lock-in** | None | Yes (TerraLab API) | None (Google-only) |
| **Watermark** | Yes (plugin icon) | No | No |
| **Metadata** | Yes (GPKG with model, prompt, timestamp, extent) | No | No |
| **Telemetry** | None | Extensive | None |
| **QGIS Integration** | Native Processing Toolbox | Custom dock widget | None (standalone) |

---

## Verification

Anyone can verify the timeline and independence by examining the public Git commit history:

```bash
# PromptMap
cd qgis-promptmap
git log --reverse --oneline -1
# Output: e46c9e4 Initial commit (Sat Nov 8 02:56:47 2025 +0100)

# QGIS AI Edit
cd QGIS_AI-Edit
git log --reverse --oneline -1
# Output: e8e70dd chore: initial placeholder (Mon Mar 23 12:35:42 2026 +0100)

# ai-topographic-maps
cd ai-topographic-maps
git log --reverse --oneline -1
# Output: 7266ace Initial commit (Sat Oct 11 17:51:28 2025 +0200)
```

---

*Document created: April 2026*
*Last updated: April 2026*
