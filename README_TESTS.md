# Tests für FLUX-Stylize-Tiles (ohne QGIS/FLUX-Laufzeit)

Diese Tests validieren ausschließlich die interne Logik von [`FluxStylizeTiles`](flux_stylize_tiles.py:1) (Polling/Download, World-File-Geometrie, Dimensionsprüfung/Resampling, Logging, VRT-Bau). Es werden keine echten Netzaufrufe durchgeführt und keine QGIS-Laufzeit benötigt.

## Voraussetzungen

- Python 3.9+
- pytest (installierbar via `pip install pytest`)
- Keine weiteren Abhängigkeiten erforderlich. Pillow/Qt/GDAL sind optional und werden in Tests gemockt/umgangen.

## Ausführung

- Alle Tests:
  - `python -m pytest -q`
- Einzelne Datei:
  - `python -m pytest -q tests/test_worldfile.py`
- Markierte Tests (z. B. „backoff“ im Namen):
  - `python -m pytest -q -k backoff`

Die Tests sind deterministisch und nutzen Mocks/Fakes. Es werden keine Internetverbindungen aufgebaut.

## Architektur der Mocks

- Netzwerkschicht ist vollständig kapsuliert in internen Methoden der Klasse:
  - [`FluxStylizeTiles._post_json()`](flux_stylize_tiles.py:1)
  - [`FluxStylizeTiles._get_json()`](flux_stylize_tiles.py:1)
  - [`FluxStylizeTiles._download_binary()`](flux_stylize_tiles.py:1)
- In `tests/conftest.py`:
  - [`FakeSession`](tests/conftest.py:1): requests-ähnliche Session mit Skript-API:
    - `script_post(url, responder)` → Responder-Funktion liefert `FakeResp`
    - `script_get_sequence(url, [FakeResp, ...])` → sequentielle Antworten
  - [`FakeResp`](tests/conftest.py:1): Minimale Response mit `status_code`, `content`, `json()`.
  - [`FakeTime`](tests/conftest.py:1): Steuert `time()`/`sleep()` deterministisch (für Timeout/Backoff).
- Bildobjekte:
  - [`SimpleImage`](flux_stylize_tiles.py:1): Stub mit `width`, `height`, `mode`, `fmt`, dient als Fallback ohne Pillow/Qt.
  - Wo Pillow verfügbar ist, wird es intern genutzt; Tests benötigen es nicht.

## Interne Helper (für Testbarkeit extrahiert)

- [`FluxStylizeTiles._compute_worldfile_params(extent, N)`](flux_stylize_tiles.py:1) → `(A, D, B, E, C, F)`
- [`FluxStylizeTiles._write_worldfile_for(path, params)`](flux_stylize_tiles.py:1) → `.wld`-Pfad
- [`FluxStylizeTiles._expected_size(N)`](flux_stylize_tiles.py:1) → `(N, N)`
- [`FluxStylizeTiles._needs_resample(w, h, N, tol=1)`](flux_stylize_tiles.py:1) → `bool`
- [`FluxStylizeTiles._resample_qimage_like(img, N, fmt)`](flux_stylize_tiles.py:1) → bildähnliches Objekt, PNG mit Alpha, JPEG ohne Alpha (weiß)
- [`FluxStylizeTiles._backoff_delays(max_retries=5, base=1, cap=16)`](flux_stylize_tiles.py:1) → `[1, 2, 4, 8, 16]`
- [`FluxStylizeTiles._hash_prompt(prompt)`](flux_stylize_tiles.py:1) → SHA256-hex
- [`FluxStylizeTiles._is_crs_degrees(crs)`](flux_stylize_tiles.py:1) → `bool` (Stub ohne QGIS)

## Abgedeckte Testfälle

- World-File (tests/test_worldfile.py)
  - Quadrat-Extent (0,0,100,100), N=100 → Erwartung: A=1.0, E=-1.0, C=0.5, F=99.5, D=B=0.
- Dimensionsprüfung/Resampling (tests/test_dimensions_resample.py)
  - 101×99 → Korrektur auf exakt N×N (tol=1 → resample).
  - PNG: Alpha bleibt erhalten; JPEG: erzwungenes RGB (weißer Background wird implizit behandelt).
- Polling/Download (tests/test_polling_and_download.py)
  - Ready-Pfad: POST→polling_url; GET: Processing→Ready; danach Download.
  - Fehlerpfad: `{"status":"Failed"}` → Kachel „Failed“, kein World-File.
  - Timeout: simuliert via `FakeTime` (>600s) → „Timeout“, keine Datei/WLD.
  - 429 Backoff: Sequenz 429→429→200; Logs zeigen Delays `[1, 2]` (max Cap 16).
  - 403/404 Download-Retry: erster 403/404, zweiter 200.
  - Backoff-Sequenz direkt verifiziert über [`FluxStylizeTiles._backoff_delays()`](flux_stylize_tiles.py:1).
- VRT-Bau (tests/test_vrt_build.py)
  - Mit GDAL: `BuildVRT`-Aufruf ge-mockt und verifiziert.
  - Ohne GDAL: sauberer Fehler mit Erklärung.
- Logging-Privacy (tests/test_logging_privacy.py)
  - API-Key taucht nicht im Log auf.
  - Pflichtfelder in Logs: `status`, `row/col`, `extent`, `N`, `xres/yres`, `prompt_hash`, `seed?`, `delivery_url`, `path`, `timestamps`.

## Designentscheidungen

- Keine Änderung von Processing-Parametern/GUI; nur interne Helper und Tests ergänzt.
- Requests- und Zeitverhalten vollständig mockbar.
- World-File-Formeln exakt wie spezifiziert:
  - `A=(xmax-xmin)/N`, `E=-(ymax-ymin)/N`, `C=xmin + A/2`, `F=ymax + E/2`.
- Backoff-Delays mit Cap 16s und max 5 Wiederholungen.
- Bildpfad:
  - PNG: Alpha beibehalten.
  - JPEG: keine Alpha; bei Bedarf weißer Hintergrund.
- GDAL optional; Tests prüfen Verhalten mit/ohne Modul.

## Hinweise zur lokalen Ausführung

- Es ist keine Internetverbindung erforderlich.
- QGIS/Qt/Pillow/GDAL sind nicht notwendig, da Tests mit Stubs/Fakes arbeiten.
- Wenn Pillow vorhanden ist, wird es intern verwendet, Tests funktionieren dennoch ohne.
- Falls Sie spezifische Teile neu ausführen möchten:
  - z. B. nur Backoff/Retry: `python -m pytest -q -k "backoff or retry"`

## Troubleshooting

- Fehlende pytest-Installation:
  - `pip install pytest`
- Importfehler `osgeo.gdal`:
  - Erwartet; Tests mocken den Pfad. Kein echtes GDAL erforderlich.
- Wenn Logs zur Inspektion auf Platte gewünscht sind:
  - Klasse mit `log_path="pfad/zur/log.jsonl"` initialisieren; siehe [`tests/test_logging_privacy.py`](tests/test_logging_privacy.py:1).
