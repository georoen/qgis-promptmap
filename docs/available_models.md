# Model & Parameter Reference

All four Processing algorithms share the same base pipeline (render canvas → send to API → georeference result). FLUX.2 and Gemini expose model dropdowns. PromptMap 0.7.0 offers five Gemini models alongside the FLUX models below.

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

### Gemini Image Editing (Nano Banana)

Select a model under **Google Gemini API → Gemini Image Editing (Nano Banana) → Gemini Model**.

| Model | API model ID | Output requested by PromptMap | Suggested use |
|---|---|---|---|
| Nano Banana Pro (default) | `gemini-3-pro-image` | 2K JPEG → local PNG | Complex instructions, detailed cartography and planning scenarios |
| Nano Banana 2.1 | `gemini-nano-banana-2.1` | 2K JPEG → local PNG | Balanced general-purpose mapping and synthetic aerial edits |
| Nano Banana 2 | `gemini-3.1-flash-image` | 2K JPEG → local PNG | Alternative balanced model for comparisons |
| Nano Banana 2 Lite | `gemini-3.1-flash-lite-image` | 1K JPEG (`1024px`) → local PNG | Fast previews, simple recolouring and local edits |
| Original Nano Banana (legacy) | `gemini-2.5-flash-image` | Native resolution, approximately 1K JPEG → local PNG | Legacy comparisons |

These recommendations follow Google's model descriptions, not a PromptMap quality benchmark. Lite prioritizes speed and cost and is not optimized for multiple references or sequential editing. No model guarantees accurate segmentation or preservation of spatial geometry.

#### Common request syntax

All five models use the same REST endpoint:
`POST https://generativelanguage.googleapis.com/v1beta/interactions`.
Requests use `x-goog-api-key` authentication and `Api-Revision: 2026-05-20`.

| Field | Value in PromptMap |
|---|---|
| `model` | Selected API model ID |
| `input` | Text instruction plus the rendered canvas as a base64 PNG |
| `response_format.type` | `image` |
| `response_format.mime_type` | `image/jpeg` (required by the live Pro Interactions endpoint) |
| `response_format.aspect_ratio` | Derived from input framing |
| `response_format.image_size` | Fixed per model as listed above; omitted for original Nano Banana |
| `store` | `false`: disable Interactions request/response storage for later retrieval |

The client reads the last image from `model_output` steps, ignores thought images, and decodes JPEG (or PNG) output with Qt. It converts the result to PNG locally before saving, watermarking and georeferencing, preserving decoded pixel dimensions and colours. Missing, malformed, unreadable or unsupported output is rejected. The selected API model ID is recorded in the output GeoPackage.

**JPEG limitation:** local PNG conversion does not reverse JPEG compression or restore transparency. For exact-colour segmentation masks, validate colours and boundaries rather than assuming lossless API output. The live Pro endpoint rejects `image/png` output requests despite PNG examples in Google's documentation.

**Framing:** all models accept the Square (1:1) and Widescreen (16:9) presets. Full-canvas mode only works when the resulting ratio is supported; otherwise PromptMap reports an error before sending a request. Standard supported ratios are 1:1, 2:3, 3:2, 3:4, 4:3, 4:5, 5:4, 9:16, 16:9 and 21:9. Nano Banana 2.1 and 2 also accept 1:4, 4:1, 1:8 and 8:1.

**Model limits versus plugin controls:** Pro, 2.1 and 2 support higher resolutions up to 4K, but this release requests 2K. Lite is limited to 1K. Thinking uses each model's default. Search grounding, extra reference images, video, batch generation and conversational interaction history are not exposed. Each run sends the current canvas independently.

**Migration from 0.6.x:** the Processing algorithm ID remains `promptmap:gemini_3_image`, and Pro remains the default. The API model changes from `gemini-3-pro-image-preview` to the stable `gemini-3-pro-image`; the transport changes from `generateContent` to Interactions. Saved workflows without a model parameter select Pro. Outputs may differ from the former preview model.

Georeferencing assigns the input extent and CRS to the generated image; it does not correct model-induced spatial drift. API usage is billed by Google. Disabling Interactions storage does not override Google's other data-handling policies.

Official documentation:
- [Image generation](https://aistudio.google.com/docs/image-generation)
- [Nano Banana 2.1](https://aistudio.google.com/docs/models/gemini-nano-banana-2.1)
- [Nano Banana Pro](https://aistudio.google.com/docs/models/gemini-3-pro-image)
- [Nano Banana 2](https://aistudio.google.com/docs/models/gemini-3.1-flash-image)
- [Nano Banana 2 Lite](https://aistudio.google.com/docs/models/gemini-3.1-flash-lite-image)
- [Original Nano Banana](https://aistudio.google.com/docs/models/gemini-2.5-flash-image)

The Lite model page specifies `1024px` and contains conflicting aspect-ratio descriptions; PromptMap conservatively enables only the standard ratios. Request construction and response parsing are tested offline; live model availability, Lite parameter acceptance and comparative quality still require paid API validation.

---

## API keys

| Provider | Registration | Environment variable |
|---|---|---|
| Black Forest Labs | <https://api.bfl.ai/> | `BFL_API_KEY` |
| Google Gemini | <https://aistudio.google.com/> | `GEMINI_API_KEY` |

Set the environment variable before starting QGIS and PromptMap will pre-fill the API Key field automatically.
