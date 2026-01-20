# Naming Conventions - Specific and Appropriate

## 🎯 Actual Model Names from Codebase

Based on the actual configurations, here are the **real model names**:

### 1. **Flux Kontext**
- **ID**: `flux_kontext`
- **Display Name**: `FLUX.1 Kontext [pro]`
- **API Endpoint**: `/v1/flux-kontext-pro`
- **Key Feature**: Image editing with instruction prompts

### 2. **Flux Ultra**
- **ID**: `flux_ultra`
- **Display Name**: `FLUX 1.1 [pro] Ultra`
- **API Endpoint**: `/v1/flux-pro-1.1-ultra`
- **Key Feature**: Artistic generation with style prompts + image strength

### 3. **Gemini**
- **ID**: `gemini_3_image`
- **Display Name**: `Gemini 3 Pro Image`
- **API Endpoint**: `/v1beta/models/gemini-3-pro-image-preview:generateContent`
- **Key Feature**: Multi-modal image generation

## 📋 Naming Convention Options

### Option 1: **Model-Based Naming (Recommended)**
**Most specific and accurate** - uses actual model names

```
qgis_flux/
├── __init__.py
├── clients/
│   ├── flux_1_kontext_pro.py          # FLUX.1 Kontext [pro]
│   ├── flux_1_1_ultra_pro.py          # FLUX 1.1 [pro] Ultra
│   └── gemini_3_pro_image.py          # Gemini 3 Pro Image
└── utils.py
```

**Pros**:
- ✅ **Most specific** - matches actual model names
- ✅ **Clear versioning** - includes version numbers
- ✅ **Professional** - matches API documentation
- ✅ **Unique** - no ambiguity between models

**Cons**:
- ❌ **Slightly longer** filenames

### Option 2: **Shortened Model-Based**
**Balanced approach** - specific but shorter

```
qgis_flux/
├── __init__.py
├── clients/
│   ├── flux_kontext_pro.py          # FLUX.1 Kontext [pro]
│   ├── flux_ultra_pro.py            # FLUX 1.1 [pro] Ultra
│   └── gemini_pro_image.py          # Gemini 3 Pro Image
└── utils.py
```

**Pros**:
- ✅ **Specific** - still identifies models clearly
- ✅ **Shorter** - more concise filenames
- ✅ **Professional** - includes "pro" designation

**Cons**:
- ❌ **Less version info** - version numbers omitted

### Option 3: **API Endpoint-Based**
**Technical approach** - based on API endpoints

```
qgis_flux/
├── __init__.py
├── clients/
│   ├── flux_kontext_pro.py          # /v1/flux-kontext-pro
│   ├── flux_pro_1_1_ultra.py        # /v1/flux-pro-1.1-ultra
│   └── gemini_3_pro_image.py        # /v1beta/models/gemini-3-pro-image-preview
└── utils.py
```

**Pros**:
- ✅ **Technical accuracy** - matches API endpoints
- ✅ **Unique** - no naming conflicts

**Cons**:
- ❌ **Less user-friendly** - technical names

### Option 4: **Feature-Based**
**User-focused approach** - based on what each model does

```
qgis_flux/
├── __init__.py
├── clients/
│   ├── flux_instruction_edit.py     # Edits based on instructions
│   ├── flux_artistic_generation.py  # Generates artistic images
│   └── gemini_multimodal.py         # Multi-modal generation
└── utils.py
```

**Pros**:
- ✅ **User-friendly** - describes functionality
- ✅ **Intuitive** - easy to understand purpose

**Cons**:
- ❌ **Less specific** - doesn't identify exact models

## 🎯 Recommended Naming Convention

### **Option 1: Model-Based Naming** ✨ BEST CHOICE

```
qgis_flux/
├── __init__.py
├── clients/
│   ├── flux_1_kontext_pro.py          # FLUX.1 Kontext [pro]
│   ├── flux_1_1_ultra_pro.py          # FLUX 1.1 [pro] Ultra
│   └── gemini_3_pro_image.py          # Gemini 3 Pro Image
└── utils.py
```

### Why This is Best:

1. **Matches Actual Models**: Uses real model names from configurations
2. **Clear Versioning**: Includes version numbers (1.1, 3)
3. **Professional**: Matches API documentation exactly
4. **Unique Identification**: No ambiguity between different models
5. **Future-Proof**: Easy to add new versions (e.g., `flux_1_2_pro.py`)

### File Content Structure:

```python
# clients/flux_1_kontext_pro.py

class Flux1KontextProAPIClient:
    """FLUX.1 Kontext [pro] API Client."""
    # Implementation

class Flux1KontextProAlgorithm(QgsProcessingAlgorithm):
    """FLUX.1 Kontext [pro] QGIS Algorithm."""
    # Implementation

def create_flux_1_kontext_pro_algorithm():
    """Create FLUX.1 Kontext [pro] algorithm instance."""
    return Flux1KontextProAlgorithm()
```

## 📋 Alternative Naming Ideas

### Version-Specific Prefixes
- `v1_flux_kontext_pro.py`
- `v1_1_flux_ultra_pro.py`
- `v3_gemini_pro_image.py`

### Company-Based Prefixes
- `bfl_flux_1_kontext_pro.py` (Black Forest Labs)
- `google_gemini_3_pro_image.py`

### Date-Based Suffixes
- `flux_kontext_pro_2024.py`
- `gemini_3_pro_image_2024.py`

## 🎯 Final Recommendation

**Use Option 1: Model-Based Naming** for:
- ✅ **Maximum clarity**
- ✅ **Professional quality**
- ✅ **Future extensibility**
- ✅ **Technical accuracy**

This naming convention provides **specific, appropriate filenames** that exactly match the actual model configurations while being **clear, professional, and maintainable**.

**Question**: Would you like me to implement the naming convention with Option 1 (Model-Based Naming) now?