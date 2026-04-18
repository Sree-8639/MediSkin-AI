# 🗂️ MediSkin AI — Trained Model Files

This directory contains all trained model files and metadata for the MediSkin AI skin disease classifier.

> ⚠️ All model files (`.keras`, `.h5`, `.pkl`) are excluded from Git via `.gitignore`.
> Store them using [Git LFS](https://git-lfs.github.com/) or download from Kaggle output.

---

## 🧠 Model Architecture

| Property | Value |
|---|---|
| **Base Model** | ResNet50 (ImageNet pretrained, fine-tuned) |
| **Head** | GAP → Dense(512)+BN+ReLU+Dropout(0.5) → Dense(256)+BN+ReLU+Dropout(0.3) → Softmax(10) |
| **Input Shape** | 224 × 224 × 3 (RGB) |
| **Preprocessing** | Divide by 255 → values in [0, 1] |
| **Output** | 10-class softmax |
| **Framework** | TensorFlow 2.19 / Keras |
| **Total Parameters** | ~25.6M |

---

## 📁 Files

### Model Files (loaded in this priority order)

| File | Size | Format | Notes |
|---|---|---|---|
| `skin_disease_classifier.keras` | ~473 MB | Native Keras | ✅ **PRIMARY** — full architecture + weights |
| `skin_disease_classifier.h5` | ~284 MB | HDF5 | Alternate full model format |
| `skin_disease_classifier.pkl` | ~95 MB | Pickle | Legacy — raw numpy weights |

> `predict.py` auto-selects the best available format: `.keras` > `.h5` > `.pkl`

### Metadata & Configuration Files

| File | Description |
|---|---|
| `class_names.json` | **Authoritative** ordered list of 10 clean disease class names |
| `label_mapping.json` | Kaggle index (0–9) → raw folder name mapping |
| `raw_class_names.json` | Original Kaggle folder names (with numeric prefixes & counts) |
| `severity_summary.json` | Per-class severity level: `{class_name: 1–4}` |
| `severity_levels.json` | Severity level definitions: `{level: {label, emoji, advice}}` |
| `severity_codes.json` | Full ICD-10 codes, treatments, and descriptions per disease |
| `model_card.json` | Complete training config, dataset info & performance metrics |

---

## 🏷️ Disease Classes

| Index | Clean Name | Raw Kaggle Name | Severity |
|---|---|---|---|
| 0 | Eczema | 1. Eczema 1677 | 🟡 Moderate (2) |
| 1 | Warts Molluscum Viral Infections | 10. Warts Molluscum... | 🟡 Moderate (2) |
| 2 | Melanoma | 2. Melanoma 15.75k | 🔴 Critical (4) |
| 3 | Atopic Dermatitis | 3. Atopic Dermatitis - 1.25k | 🟡 Moderate (2) |
| 4 | Basal Cell Carcinoma (BCC) | 4. Basal Cell Carcinoma (BCC) 3323 | 🔴 Critical (4) |
| 5 | Melanocytic Nevi (NV) | 5. Melanocytic Nevi (NV) - 7970 | 🟠 High (3) |
| 6 | Benign Keratosis-like Lesions (BKL) | 6. Benign Keratosis-like Lesions (BKL) 2624 | 🟡 Moderate (2) |
| 7 | Psoriasis Lichen Planus | 7. Psoriasis pictures Lichen Planus... | 🟡 Moderate (2) |
| 8 | Seborrheic Keratoses | 8. Seborrheic Keratoses... | 🟢 Low (1) |
| 9 | Tinea Ringworm Fungal Infections | 9. Tinea Ringworm Candidiasis... | 🟡 Moderate (2) |

---

## 📊 Performance Metrics

From `model_card.json` (test set evaluation):

| Metric | Score |
|---|---|
| Accuracy | **81.6%** |
| Precision (macro) | 75.6% |
| Recall (macro) | 77.3% |
| F1 Score (macro) | **76.1%** |
| F1 Score (weighted) | 81.7% |
| Validation Accuracy (Stage 2) | **80.9%** |

---

## 💻 Usage

```python
from ml.predict import load_model, predict_image, _load_severity_summary, _load_severity_levels

# Load the model (auto-picks best format)
pkg = load_model()

# Predict
result = predict_image('path/to/skin_image.jpg', model_package=pkg, top_k=3)
print(result['disease'])          # e.g. "Melanoma"
print(result['confidence'])       # e.g. 0.834
print(result['top_predictions'])  # list of top-k dicts

# Load severity info
severity_map  = _load_severity_summary()   # {"Melanoma": 4, "Eczema": 2, ...}
severity_defs = _load_severity_levels()    # {"4": {"label": "CRITICAL", "emoji": "🔴", ...}}

level = severity_map.get(result['disease'], 2)
info  = severity_defs.get(str(level), {})
print(info['label'], info['advice'])
```

---

## 🔄 Replacing / Updating the Model

1. Retrain on Kaggle using `MediSkin_AI.ipynb`
2. Download output files and place in this directory
3. **Keep** `class_names.json` as the authoritative name list (clean names, no prefixes)
4. Restart the Django server — the model cache reloads automatically on the next request
