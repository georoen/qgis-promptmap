# Originality & Comparison with Other Projects

This document clarifies the origin of PromptMap and addresses any questions about resemblance to other QGIS AI plugins.

---

## Timeline

| Date | Event | Author |
|------|-------|--------|
| **Nov 8, 2025** | PromptMap initial commit | JSReseach |
| Mar 23, 2026 | QGIS_AI-Edit initial commit | TerraLab |

**PromptMap was released ~4.5 months before TerraLab's AI Edit plugin.**

---

## Comparison: PromptMap vs. QGIS_AI-Edit

Both plugins enable AI-powered image processing within QGIS. Below is a technical comparison showing fundamental differences in implementation.

### Architecture

| Aspect | PromptMap | QGIS_AI-Edit (TerraLab) |
|--------|-----------|-------------------------|
| **Plugin Type** | Processing Provider (toolbox-based) | Dock Widget with custom UI |
| **Codebase Size** | ~485 lines (core) | ~1800+ lines (core) |
| **Module Structure** | Flat: `plugin.py` + `clients/*.py` | Layered: `src/api/`, `src/core/`, `src/ui/`, `src/workers/` |

### API Integration

| Aspect | PromptMap | QGIS_AI-Edit |
|--------|-----------|--------------|
| **Providers** | Multiple: Black Forest Labs (FLUX.1, FLUX.2), Google Gemini | Single: TerraLab proprietary API |
| **Authentication** | API key per provider, entered in Processing dialog | Centralized account system with activation keys |
| **Pricing Model** | User manages their own API credits | Freemium with tiered pricing (free tier + subscription) |

### User Experience

| Aspect | PromptMap | QGIS_AI-Edit |
|--------|-----------|--------------|
| **Input Selection** | Full canvas or aspect-ratio preset (1:1, 16:9, full extent) | Rectangle selection tool on map |
| **Output** | GeoTIFF + GeoPackage metadata layer | GeoTIFF only |
| **Watermark** | Yes (plugin icon burnt into lower-right corner) | No |
| **Metadata** | GPKG with timestamp, model, prompt, extent | None |
| **Telemetry** | None | Extensive tracking and analytics |

### Feature Set

| Feature | PromptMap | QGIS_AI-Edit |
|---------|-----------|--------------|
| Processing Toolbox Integration | ✅ Yes | ❌ No |
| Custom Dock Widget | ❌ No | ✅ Yes |
| Account Settings Dialog | ❌ No | ✅ Yes |
| Prompt Templates | ❌ No | ✅ Yes (catalog with 28+ presets) |
| Resolution Selection | Preset-based (2048×2048, 1280×720, full canvas) | Dynamic (1K, 2K, 4K with server config) |
| Credit Usage Tracking | ❌ No | ✅ Yes |
| Cross-Plugin Promotion | ❌ No | ✅ Yes (links to AI Segmentation plugin) |

---

## Code Similarity Analysis

### Unique Implementation Patterns in PromptMap

1. **BaseAIAlgorithm class** (`clients/base.py`): Custom `QgsProcessingAlgorithm` subclass that handles:
   - Aspect ratio cropping via `extent_with_aspect_ratio()`
   - Map canvas rendering with `QgsMapRendererParallelJob`
   - Base64 image encoding
   - GeoTIFF creation via GDAL
   - GPKG metadata export with QgsVectorFileWriter
   - Watermark application using QPainter

2. **BFLAPIClient polling pattern** (`clients/bfl_base.py`): Asynchronous request-poll-complete loop with configurable timeout

3. **Provider-specific clients**: Separate implementations for each model (FLUX.1 Kontext, FLUX.2, Gemini)

### Unique Implementation Patterns in QGIS_AI-Edit

1. **Three-tier architecture**: Explicit separation of API, core logic, UI, and worker threads
2. **QGIS Network Stack**: Uses `QgsBlockingNetworkRequest` instead of Python `requests` library
3. **GenerationService**: State machine for submit → poll → complete cycle with progress callbacks
4. **AuthManager**: Centralized authentication handling with consent and activation
5. **CanvasExporter**: Client-side resolution detection with server-driven configuration
6. **Telemetry System**: Event tracking with opt-in consent

### Conclusion

**There is zero code overlap between the projects.** Both solve the same high-level problem (AI-powered image editing in QGIS) but do so with completely different technical approaches, reflecting independent development efforts.

This is a case of **parallel innovation** — when multiple parties independently arrive at solutions for an obvious and timely problem. The fact that PromptMap was released first is well-documented by the public commit history.

---

## Related Projects

| Project | Repository | First Release | Author | Notes |
|---------|-----------|---------------|--------|-------|
| **PromptMap** | [github.com/georoen/qgis-promptmap](https://github.com/georoen/qgis-promptmap) | Nov 2025 | JSReseach | Multi-provider, Processing-based |
| AI Edit | [github.com/TerraLabAI/QGIS_AI-Edit](https://github.com/TerraLabAI/QGIS_AI-Edit) | Mar 2026 | TerraLab | Proprietary API, Dock-based UI |

---

## Verification

Anyone can verify the timeline and independence by examining the public Git commit history:

```bash
# PromptMap
cd qgis-promptmap
git log --reverse --oneline -1
# Output: e46c9e4 Initial commit (Sat Nov 8 02:56:47 2025 +0100)

# QGIS_AI-Edit  
cd QGIS_AI-Edit
git log --reverse --oneline -1
# Output: e8e70dd chore: initial placeholder (Mon Mar 23 12:35:42 2026 +0100)
```

---

*Document created: April 2026*
*Last updated: April 2026*
