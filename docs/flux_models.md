# Model & Parameter Reference

All four algorithms share the same base pipeline (render canvas → send to API → georeference result). The parameters below are specific to each model.

---

## Shared UI behavior (all models)

- The Processing dropdown controls **aspect ratio / input framing** for the canvas render.
- It does **not** guarantee final output pixel dimensions.
- Final pixel dimensions are determined by each provider/model response.

---

## Black Forest Labs API

### FLUX.1 Kontext [pro]

Image-to-image editing with strong prompt adherence. Best for segmentation, cartographic abstraction, and targeted scene modifications.

| Parameter | Type | Default | Notes |
|---|---|---|---|
| `prompt` | string | required | Text instruction |
| `input_image` | base64 PNG | auto | Rendered QGIS canvas |
| `aspect_ratio` | string | auto | Derived from framing preset (e.g. `"1:1"`, `"16:9"`) |
| `safety_tolerance` | int 0–6 | 2 | 0 = strict, 6 = permissive |
| `seed` | int | optional | Set for reproducibility |
| `output_format` | string | `"png"` | Always PNG for georeferencing |

Official docs: <https://docs.bfl.ai/kontext/kontext_image_editing#flux-1-kontext-image-editing-parameters>

---

### FLUX 1.1 [pro] Ultra

High-quality stylisation with image prompt strength control. Best for thematic maps and high-resolution outputs.

| Parameter | Type | Default | Notes |
|---|---|---|---|
| `prompt` | string | required | Text instruction |
| `image_prompt` | base64 PNG | auto | Rendered QGIS canvas |
| `image_prompt_strength` | float 0.1–1.0 | 0.8 | How strongly the input image guides the output |
| `aspect_ratio` | string | auto | Derived from framing preset |
| `safety_tolerance` | int 0–6 | 2 | 0 = strict, 6 = permissive |
| `seed` | int | optional | Set for reproducibility |
| `output_format` | string | `"png"` | Always PNG |

Official docs: <https://docs.bfl.ai/flux/flux_pro#flux-11-ultra>

---

### FLUX.2 Image Editing

Five model variants selectable via dropdown. Useful for exploring the quality/speed trade-off.

| Variant | Endpoint | Characteristic |
|---|---|---|
| FLUX.2 [pro] | `flux-2-pro` | Balanced |
| FLUX.2 [max] | `flux-2-max` | Highest quality |
| FLUX.2 [flex] | `flux-2-flex` | Controllable |
| FLUX.2 [klein] 4B | `flux-2-klein-4b` | Fastest |
| FLUX.2 [klein] 9B | `flux-2-klein-9b` | Fast + quality |

| Parameter | Type | Default | Notes |
|---|---|---|---|
| `prompt` | string | required | Text instruction |
| `input_image` | base64 PNG | auto | Rendered QGIS canvas |
| `aspect_ratio` | string | auto | Derived from framing preset |
| `safety_tolerance` | int 0–5 | 2 | 0 = strict, 5 = permissive |
| `seed` | int | optional | Set for reproducibility |
| `output_format` | string | `"png"` | Always PNG |

Official docs: <https://docs.bfl.ai/>

---

## Google Gemini API

### Gemini 3 Pro Image

Multimodal model with strong contextual understanding. Accepts image + text and returns an inline base64-encoded PNG.

| Parameter | Type | Default | Notes |
|---|---|---|---|
| `prompt` | string | required | Text instruction |
| `inlineData` (image) | base64 PNG | auto | Rendered QGIS canvas |
| `aspectRatio` | string | auto | Derived from framing preset (e.g. `"1:1"`, `"16:9"`) |
| `imageSize` | string | `"2K"` | Fixed at 2K resolution |

Official docs: <https://ai.google.dev/gemini-api/docs/image-generation>

---

## API keys

| Provider | Registration | Environment variable |
|---|---|---|
| Black Forest Labs | <https://api.bfl.ai/> | `BFL_API_KEY` |
| Google Gemini | <https://aistudio.google.com/> | `GEMINI_API_KEY` |

Set the environment variable before starting QGIS and PromptMap will pre-fill the API Key field automatically.
