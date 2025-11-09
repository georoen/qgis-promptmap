# FLUX Model Reference

This plugin talks to two BFL/FLUX endpoints. Keep this page close when you need to
double-check parameter behaviour or jump to the official documentation.

| Parameter | FLUX.1 Kontext *(image editing)* | FLUX 1.1 [pro] Ultra *(image stylisation)* | Notes |
| --- | --- | --- | --- |
| `prompt` | ✔︎ (required) | ✔︎ (required) | Text instruction or style guidance. Filled from the QGIS “Prompt” field. |
| `input_image` / `image_prompt` | `input_image` | `image_prompt` | The plugin always renders the current canvas and base64-encodes it for both endpoints. |
| `aspect_ratio` | Optional (`"1:1"` default, supports 3:7–7:3) | Optional (`"16:9"` default) | We auto-compute a ratio from the selected tile option and send it for both models. |
| `seed` | Optional integer | Optional integer | Controlled by the optional “Random Seed” advanced field. Blank = random. |
| `prompt_upsampling` | Optional boolean (default `false`) | Optional boolean (default `false`) | Currently left at the API default. |
| `safety_tolerance` | Optional integer (default `2`) | Optional integer (default `2`) | Kontext exposes it as an advanced parameter; Ultra exposes it too. Range 0 (strict) – 6 (permissive). |
| `output_format` | `"jpeg"` / `"png"` | `"jpeg"` / `"png"` | The plugin always requests `png` so transparency & georeferencing stay consistent. |
| `raw` | — | Optional boolean (default `false`) | Exposed as “Raw Mode” for Ultra. |
| `image_prompt_strength` | — | Optional float 0–1 (default `0.8`) | Exposed as “Image Prompt Strength” slider for Ultra. |
| `webhook_url` / `webhook_secret` | Optional | Optional | Not surfaced yet; defaults to `null`. |

**Official docs**

- FLUX.1 Kontext parameters: <https://docs.bfl.ai/kontext/kontext_image_editing#flux-1-kontext-image-editing-parameters>
- FLUX 1.1 Ultra parameters: <https://docs.bfl.ai/flux/flux_pro#flux-11-ultra>

The defaults in `flux_api_config.py` mirror those specs so you can compare the
payload that leaves QGIS with the upstream expectations.
