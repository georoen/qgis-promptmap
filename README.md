# QGIS FLUX Stylize Plugin

KI-basierte Stylisierung von Rasterkarten mit FLUX API. Verwandelt Geodaten in künstlerische Visualisierungen.

## 🚀 Schnellstart

### 1. Installation
```bash
# Plugin-Ordner in QGIS kopieren
cp -r qgis_flux ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/
```

Oder: ZIP-Datei über QGIS Plugin Manager → "Install from ZIP"

### 2. API Key besorgen
- Gehe zu https://api.flux.dev 
- Registriere dich und hole API Key
- Format: `sk-xxxxxxxxxxxxxxxxxx`

### 3. Plugin nutzen
1. QGIS öffnen → **Processing Toolbox** → **FLUX AI Processing** → **FLUX Stylize Tiles**
2. **Input Raster Layer**: Deine Rasterkarte auswählen
3. **FLUX API Key**: Deinen API Key einfügen
4. **Style Prompt**: z.B. "watercolor painting", "cyberpunk neon", "medieval map"
5. **Output Directory**: Ordner für Ergebnisse wählen
6. **Run** klicken

### 4. Fertig!
- Stylisierte Tiles + World-Files werden erstellt
- Optional: VRT-Mosaik für nahtlose Darstellung
- Log-Datei zeigt Details der Verarbeitung

## 📋 Parameter

| Parameter | Beschreibung | Beispiel |
|-----------|-------------|----------|
| **Input Raster** | Eingabe-Rasterlayer | OpenStreetMap, Sentinel-2 |
| **API Key** | FLUX API Schlüssel | sk-abc123... |
| **Style Prompt** | Gewünschter Stil | "impressionist painting" |
| **Tile Size** | Kachelgröße | 512×512 oder 1024×1024 |
| **Output Format** | Bildformat | PNG (Alpha) oder JPEG |
| **Seed** | Zufallssaat (optional) | 42 für gleiche Ergebnisse |
| **Create VRT** | Mosaik erstellen | ✓ für nahtlose Darstellung |

## 🎨 Style-Beispiele

```
"watercolor landscape painting"
"satellite view in cyberpunk style with neon colors"
"hand-drawn medieval fantasy map"
"black and white pencil sketch"
"retro 80s synthwave aesthetic"
"oil painting in Van Gogh style"
```

## 📁 Ausgabe-Struktur

```
output_directory/
├── flux_tile_000_000.png      # Stylisierte Kachel
├── flux_tile_000_000.png.wld  # World-File für Georeferenz
├── flux_stylized_mosaic.vrt   # VRT-Mosaik aller Kacheln
└── flux_processing.log        # Verarbeitungsprotokoll
```

## 🔧 Systemanforderungen

- **QGIS**: 3.20 oder neuer
- **Internet**: API-Zugriff auf FLUX
- **Python**: Requests-Bibliothek (meist vorhanden)
- **Optional**: GDAL für VRT-Erstellung

## 💡 Tipps & Tricks

### Performance
- Kleine Testgebiete erst probieren
- 512×512 ist schneller als 1024×1024
- PNG für Transparenz, JPEG für kleinere Dateien

### Prompts
- Sei spezifisch: "aerial view of forest in autumn colors"
- Stil + Inhalt: "watercolor painting of mountains"
- Kontraste: "high contrast black and white"

### Troubleshooting
- **API Error 401**: API Key prüfen
- **Timeout**: Netzwerk/Serverlast
- **No VRT**: GDAL fehlt (nicht kritisch)
- **Details**: Siehe `flux_processing.log`

## 🛠 Entwicklung

### Tests ausführen
```bash
python -m pytest tests/ -v
```

### Struktur
- `flux_stylize_tiles.py`: Core-Logik mit internen Helpers
- `flux_processing_algorithm.py`: QGIS Processing Integration   
- `tests/`: Vollständige Testsuite ohne QGIS/FLUX-Abhängigkeiten

## 📄 Lizenz

Open Source - siehe Lizenz für Details.

---

**Viel Spaß beim Erstellen künstlerischer Karten!** 🗺️✨