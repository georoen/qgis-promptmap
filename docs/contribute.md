# Contributions wellcome

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

## Development & tests

```bash
python3 -m pytest tests -v
```

The tests mock out QGIS/FLUX internals and focus on the remote-engine workflow,
polling, logging, and world-file generation. When editing Processing parameters, run a
manual smoke test inside QGIS because the UI requires a live canvas.
