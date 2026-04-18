# 🤖 MediSkin AI — ML Module

The `ml/` package handles all machine learning inference for the MediSkin AI platform.
It loads a fine-tuned ResNet50 model and provides a clean prediction API consumed by Django views.

---

## 📁 Files

| File | Purpose |
|---|---|
| `predict.py` | Main prediction engine (v5.0) — model loading, preprocessing, inference |
| `create_model.py` | Offline model architecture script (used on Kaggle during training) |
| `test_predictions.py` | Standalone test suite — verifies predictions vary across different image types |
| `__init__.py` | Makes `ml/` a Python package |
| `models/` | Trained model files & metadata (see `models/README.md`) |

---

## 🚀 Quick Start

### Run a prediction

```python
# From backend/ directory
from ml.predict import load_model, predict_image

# Load model (auto-selects best format: .keras > .h5 > .pkl)
pkg = load_model()

# Predict from a file path
result = predict_image('path/to/skin_image.jpg', model_package=pkg)

print(f"Disease    : {result['disease']}")
print(f"Confidence : {result['confidence']:.1%}")
print(f"Category   : {result['category']}")
print(f"Top-3      : {result['top_predictions']}")
```

### Test the pipeline

```bash
cd backend
python ml/test_predictions.py
```

This runs 5 synthetic test images (red/inflamed, dark lesion, ring pattern, bumpy, normal)
and verifies that predictions differ meaningfully across image types.

---

## 🧠 How Prediction Works (`predict.py`)

### 1. Model Loading

`load_model()` searches for model files in this priority order:

```
backend/ml/models/skin_disease_classifier.keras   ← preferred
backend/ml/models/skin_disease_classifier.h5
backend/ml/models/skin_disease_classifier.pkl
```

Supports three PKL formats:
- **Native Keras** (`.keras` / `.h5`) — loads architecture + weights directly
- **New PKL** — raw numpy weights, rebuilt into Keras architecture at load time
- **Old PKL** — embedded Keras model object extracted from the pickle

### 2. Preprocessing

Images are converted to RGB, resized to **224 × 224**, and pixel values divided by **255**
(normalised to [0, 1]) before being passed to the model.

### 3. Hybrid Scoring

| Component | Weight | Description |
|---|---|---|
| Neural Network | **70%** | ResNet50 softmax probabilities across 10 classes |
| Pixel Heuristics | **30%** | Colour, brightness, edge density, ring patterns |

The two scores are blended, normalised, and sorted to produce Top-K predictions.

> Pixel heuristics act as a robustness fallback if NN output variance is too low (< 0.005 std).

### 4. Output Format

```python
{
    'disease': 'Melanoma',
    'confidence': 0.834,
    'category': 'Malignant',
    'top_predictions': [
        {'rank': 1, 'disease': 'Melanoma',        'confidence': 0.834, 'category': 'Malignant'},
        {'rank': 2, 'disease': 'Basal Cell ...',   'confidence': 0.091, 'category': 'Malignant'},
        {'rank': 3, 'disease': 'Melanocytic Nevi', 'confidence': 0.048, 'category': 'Benign'},
    ],
    'all_probabilities': { 'Melanoma': 0.834, ... }
}
```

---

## 📦 Helper Functions

```python
from ml.predict import (
    load_model,            # Load and cache the model
    predict_image,         # Predict from file path, PIL image, or numpy array
    predict_batch,         # Predict for a list of images
    preprocess_image,      # Resize & normalise (backward-compat utility)
    get_model_info,        # Return model metadata dict
    _load_severity_summary,  # {class_name: severity_level_int (1-4)}
    _load_severity_levels,   # {"1": {label, emoji, advice}, ...}
)
```

---

## 🔁 Updating the Model

After retraining on Kaggle:

1. Download the new model files from your Kaggle output:
   - `skin_disease_classifier.keras` ← **preferred**
   - `skin_disease_classifier.h5`
   - `skin_disease_classifier.pkl`
   - `class_names.json`, `label_mapping.json`, `model_card.json`
   - `severity_summary.json`, `severity_levels.json`

2. Place all files in `backend/ml/models/`

3. Restart the Django server — the model cache auto-refreshes on next request

---

## 📋 Requirements

```
tensorflow>=2.15.0
numpy>=1.24.0
Pillow>=10.0.0
```

All covered by the root `requirements.txt`.
