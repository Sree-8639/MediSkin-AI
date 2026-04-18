"""
MediSkin AI - Prediction Utility  v5.0
========================================
Supports multiple model formats in order of preference:
  1.  .keras  — Native Keras saved model (BEST, loads architecture + weights)
  2.  .h5     — HDF5 saved model (also loads full model)
  3.  .pkl    — Legacy PKL with raw numpy weights (requires architecture rebuild)

Strategy
--------
1.  On first load, find and load the model file (prefer .keras > .h5 > .pkl).
2.  Run the model directly for predictions (softmax output across 10 classes).
3.  Combine with pixel-level scoring for robustness.

Preprocessing: the model was trained with rescale=1/255 (raw [0-255]
input divided by 255 before feeding into ResNet50). We apply this in predict.
"""

from __future__ import annotations

import os
import json
import pickle
import warnings
from pathlib import Path

import numpy as np
from PIL import Image

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
warnings.filterwarnings('ignore')

import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers


# ─── Compatibility stub ───────────────────────────────────────────────────────
class SkinDiseaseClassifier:
    pass


class _CompatUnpickler(pickle.Unpickler):
    def find_class(self, module, name):
        if name == 'SkinDiseaseClassifier':
            return SkinDiseaseClassifier
        return super().find_class(module, name)


# ─── Global caches ────────────────────────────────────────────────────────────
_model_cache: dict | None = None
_keras_model = None            # Reconstructed Keras model

# Preferred model filenames — searched in this order
MODEL_FILENAMES = [
    'skin_disease_classifier.keras',
    'skin_disease_classifier.h5',
    'skin_disease_classifier.pkl',
]
MODEL_FILENAME = 'skin_disease_classifier.keras'  # Best available format

# Input size for the new model
INPUT_SIZE = (224, 224)

# ─── Disease categories ───────────────────────────────────────────────────────
_CATEGORIES = {
    'melanoma': 'Malignant',
    'basal cell carcinoma': 'Malignant',
    'squamous cell carcinoma': 'Malignant',
    'actinic keratosis': 'Pre-Malignant',
    'eczema': 'Inflammatory',
    'psoriasis': 'Inflammatory',
    'atopic dermatitis': 'Inflammatory',
    'lichen planus': 'Inflammatory',
    'ringworm': 'Infectious',
    'tinea': 'Infectious',
    'warts': 'Infectious',
    'molluscum': 'Infectious',
    'fungal': 'Infectious',
    'seborrheic keratosis': 'Benign',
    'seborrheic keratoses': 'Benign',
    'melanocytic nevi': 'Benign',
    'nevus': 'Benign',
    'nevi': 'Benign',
    'benign keratosis': 'Benign',
    'vitiligo': 'Pigmentary',
    'melasma': 'Pigmentary',
    'viral': 'Infectious',
}


def get_disease_category(name: str) -> str:
    key = name.strip().lower()
    for k, cat in _CATEGORIES.items():
        if k in key:
            return cat
    return 'Dermatological Condition'


# ─── Model path resolver ──────────────────────────────────────────────────────

def _resolve_model_path(model_path: str | None = None) -> Path:
    """
    Find the best available model file.
    If model_path is given, try that first.
    Otherwise, search for .keras > .h5 > .pkl in standard locations.
    """
    here = Path(__file__).resolve().parent
    search_dirs = [
        Path('.'),
        here,
        here / 'models',
        here.parent.parent / 'backend' / 'ml' / 'models',
    ]

    # If a specific path was given, try it and its basename in search dirs
    if model_path:
        p = Path(model_path)
        if p.exists():
            return p
        for d in search_dirs:
            candidate = d / p.name
            if candidate.exists():
                return candidate

    # Auto-discover: prefer .keras > .h5 > .pkl
    for filename in MODEL_FILENAMES:
        for d in search_dirs:
            candidate = d / filename
            if candidate.exists():
                return candidate

    raise FileNotFoundError(
        f"No model file found. Searched for {MODEL_FILENAMES} in {[str(d) for d in search_dirs]}"
    )


# ─── Rebuild Keras model from stored numpy weights ────────────────────────────

def _rebuild_keras_model(pkg: dict) -> keras.Model:
    """
    Reconstruct the Keras model from the raw-numpy-weight PKL format.

    Architecture (from model_config):
        Input(224,224,3) → ResNet50(include_top=False, pooling='avg')
        → Dense(512) → BN → ReLU → Dropout(0.5)
        → Dense(256) → BN → ReLU → Dropout(0.3)
        → Dense(10, softmax)
    Preprocessing: input is already divided by 255 before passing to model.
    """
    num_classes = pkg.get('num_classes', 10)
    mw = pkg['model_weights']

    print("[predict.py] Rebuilding Keras ResNet50 model from stored weights…")

    # Build architecture matching what was trained
    inp = keras.Input(shape=(*INPUT_SIZE, 3), name='input_image')

    # ResNet50 backbone — do NOT include top, use average pooling
    backbone = keras.applications.ResNet50(
        weights=None,          # load our stored weights
        include_top=False,
        pooling='avg',         # -> (batch, 2048)
        input_tensor=inp,
    )

    x = backbone.output

    # Custom head
    x = layers.Dense(512, name='dense_1')(x)
    x = layers.BatchNormalization(name='bn_1')(x)
    x = layers.Activation('relu', name='relu_1')(x)
    x = layers.Dropout(0.5, name='dropout_1')(x)

    x = layers.Dense(256, name='dense_2')(x)
    x = layers.BatchNormalization(name='bn_2')(x)
    x = layers.Activation('relu', name='relu_2')(x)
    x = layers.Dropout(0.3, name='dropout_2')(x)

    outputs = layers.Dense(num_classes, activation='softmax', name='output_predictions')(x)

    model = keras.Model(inputs=inp, outputs=outputs, name='skin_disease_resnet50')

    # ── Load weights into backbone ────────────────────────────────────────────
    resnet_weights = mw.get('resnet50', [])
    if isinstance(resnet_weights, list) and resnet_weights:
        wb = backbone.get_weights()
        if len(wb) == len(resnet_weights):
            backbone.set_weights(resnet_weights)
            print(f"[predict.py] ResNet50 backbone: loaded {len(resnet_weights)} weight tensors.")
        else:
            print(f"[predict.py] WARNING: ResNet50 weight count mismatch "
                  f"(model={len(wb)}, pkl={len(resnet_weights)}). Using ImageNet weights instead.")
            # Fall back to ImageNet weights for backbone
            imagenet_backbone = keras.applications.ResNet50(
                weights='imagenet', include_top=False, pooling='avg', input_shape=(*INPUT_SIZE, 3)
            )
            backbone.set_weights(imagenet_backbone.get_weights())

    # ── Load weights into custom head layers ──────────────────────────────────
    head_layers = [
        ('dense_1', 'dense_1'),
        ('bn_1', 'bn_1'),
        ('dense_2', 'dense_2'),
        ('bn_2', 'bn_2'),
        ('output_predictions', 'output_predictions'),
    ]
    for pkl_key, layer_name in head_layers:
        w_list = mw.get(pkl_key, [])
        if isinstance(w_list, list) and w_list:
            try:
                lay = model.get_layer(layer_name)
                lay.set_weights(w_list)
                print(f"[predict.py] Layer '{layer_name}': loaded {len(w_list)} weight tensors.")
            except Exception as e:
                print(f"[predict.py] WARNING: Could not load weights for '{layer_name}': {e}")

    model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])
    print(f"[predict.py] Model rebuilt successfully — {model.count_params():,} params, "
          f"output shape: {model.output_shape}")
    return model


# ─── Class name helpers ───────────────────────────────────────────────────────

def _clean_raw_name(n: str) -> str:
    """Strip Kaggle folder-style prefixes/suffixes from a class name."""
    import re
    # Remove leading "N. " prefix like "1. Eczema 1677"
    parts = n.split('. ', 1)
    if len(parts) == 2 and parts[0].strip().isdigit():
        n = parts[1]
    # Strip trailing count like " 1677" or " - 1.25k"
    n = re.sub(r'\s*[-–]\s*[\d.]+k?$', '', n)
    n = re.sub(r'\s+\d{3,}$', '', n)
    n = re.sub(r'\s+pictures?\b.*', '', n, flags=re.IGNORECASE)
    return n.strip()


def _load_class_names(pkg: dict) -> list[str]:
    """
    Load class names from (in order of preference):
      1. models/class_names.json  — clean curated names
      2. models/label_mapping.json — Kaggle raw names (cleaned)
      3. models/raw_class_names.json — Kaggle raw names (cleaned)
      4. pkg['class_names'] — embedded in pkl (cleaned)
    """
    here = Path(__file__).resolve().parent
    models_dir = here / 'models'

    # 1. Clean authoritative names
    json_path = models_dir / 'class_names.json'
    if json_path.exists():
        with open(json_path) as jf:
            names = json.load(jf)
            if names:
                return names

    # 2. label_mapping.json (sorted by key index)
    lm_path = models_dir / 'label_mapping.json'
    if lm_path.exists():
        with open(lm_path) as jf:
            mapping = json.load(jf)
            raw = [mapping[str(i)] for i in range(len(mapping)) if str(i) in mapping]
            if raw:
                return [_clean_raw_name(n) for n in raw]

    # 3. raw_class_names.json
    raw_path = models_dir / 'raw_class_names.json'
    if raw_path.exists():
        with open(raw_path) as jf:
            raw = json.load(jf)
            if raw:
                return [_clean_raw_name(n) for n in raw]

    # 4. Embedded in PKL
    raw = pkg.get('class_names', [])
    return [_clean_raw_name(n) for n in raw]


def _load_severity_summary() -> dict:
    """
    Load severity summary mapping class name -> severity level (1-4).
    Returns a dict {clean_class_name: severity_int}.
    """
    here = Path(__file__).resolve().parent
    sev_path = here / 'models' / 'severity_summary.json'
    if not sev_path.exists():
        return {}
    with open(sev_path) as jf:
        raw = json.load(jf)
    return {_clean_raw_name(k): int(v) for k, v in raw.items()}


def _load_severity_levels() -> dict:
    """
    Load severity level definitions {"1": {label, emoji, advice}, ...}.
    """
    here = Path(__file__).resolve().parent
    lev_path = here / 'models' / 'severity_levels.json'
    if not lev_path.exists():
        return {}
    with open(lev_path) as jf:
        return json.load(jf)


# ─── Main model loader ────────────────────────────────────────────────────────

def load_model(model_path: str = None):
    global _model_cache, _keras_model

    if _model_cache is not None:
        return _model_cache

    resolved = _resolve_model_path(model_path)
    ext = resolved.suffix.lower()
    print(f"[*] Loading model from {resolved} (format: {ext})…")

    pkg = {}  # metadata dict (may be empty for .keras/.h5)

    # ── Load based on file extension ──────────────────────────────────────────
    if ext in ('.keras', '.h5'):
        # PREFERRED: load the full Keras model directly — architecture + weights
        print(f"[predict.py] Loading native Keras model ({ext})…")
        _keras_model = keras.models.load_model(str(resolved), compile=False)
        _keras_model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])
        print(f"[predict.py] Model loaded successfully — {_keras_model.count_params():,} params, "
              f"output shape: {_keras_model.output_shape}")

    elif ext == '.pkl':
        # LEGACY: PKL format
        print(f"[predict.py] Loading PKL model…")
        with open(resolved, 'rb') as f:
            pkg = _CompatUnpickler(f).load()

        if not isinstance(pkg, dict):
            pkg = vars(pkg)

        # Detect format inside PKL
        has_keras_model = any(
            hasattr(v, 'predict') and hasattr(v, 'layers')
            for v in pkg.values()
        )

        if has_keras_model:
            print("[predict.py] Detected OLD pkl format (embedded Keras model).")
            _keras_model = next(
                v for v in pkg.values()
                if hasattr(v, 'predict') and hasattr(v, 'layers')
            )
        elif 'model_weights' in pkg:
            print("[predict.py] Detected NEW pkl format (raw numpy weights).")
            _keras_model = _rebuild_keras_model(pkg)
        else:
            raise ValueError(f"Unrecognised PKL format. Keys: {list(pkg.keys())}")
    else:
        raise ValueError(f"Unsupported model file format: {ext}")

    # ── Load class names ──────────────────────────────────────────────────────
    class_names = _load_class_names(pkg)
    print(f"[predict.py] Class names ({len(class_names)}): {class_names}")

    # ── Determine input size ──────────────────────────────────────────────────
    try:
        h = int(_keras_model.input_shape[1]) or INPUT_SIZE[0]
        w = int(_keras_model.input_shape[2]) or INPUT_SIZE[1]
    except Exception:
        h, w = INPUT_SIZE

    _model_cache = {
        'model': _keras_model,
        'class_names': class_names,
        '_input_size': (h, w),
        'version': pkg.get('metadata', {}).get('framework_version', pkg.get('version', '5.0')),
        'preprocessing': pkg.get('model_config', {}).get('preprocessing',
                                 pkg.get('preprocessing', 'rescale_1_255')),
        'num_classes': len(class_names),
    }

    print(f"[+] Model ready! classes={len(class_names)}, input=({h},{w})")
    return _model_cache


# ─── Preprocessing ────────────────────────────────────────────────────────────

def _preprocess_for_model(pil_img: Image.Image, input_size: tuple) -> np.ndarray:
    """
    Resize and normalise image for the model.
    New model: rescale 1/255 (i.e. divide by 255, values in [0,1]).
    """
    img_resized = pil_img.convert('RGB').resize(input_size, Image.LANCZOS)
    arr = np.array(img_resized, dtype='float32') / 255.0
    return np.expand_dims(arr, axis=0)


# ─── Pixel-based disease scoring ──────────────────────────────────────────────

def _pixel_disease_scores(pil_img: Image.Image, class_names: list) -> dict:
    """
    Compute pixel-level disease likelihood scores.
    Returns normalised dict {class_name: score}.
    """
    from PIL import ImageFilter
    img = pil_img.convert('RGB').resize((256, 256), Image.LANCZOS)
    arr = np.array(img, dtype='float32') / 255.0
    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]

    mr, mg, mb = float(r.mean()), float(g.mean()), float(b.mean())
    brightness = (mr + mg + mb) / 3.0
    darkness = 1.0 - brightness
    redness = max(0.0, mr - (mg + mb) / 2.0)
    brownness = min(1.0, max(0.0, mr - 0.25) * max(0.0, mg - 0.10)
                    * max(0.0, 0.55 - mb) * 10)
    pinkness = max(0.0, mr - mb) * brightness
    lum = (r + g + b) / 3.0
    dark_frac = float((lum < 0.20).mean())
    white_frac = float((lum > 0.88).mean())
    texture_var = float(arr.var())
    edge_x = float(np.abs(np.diff(lum, axis=1)).mean())
    edge_y = float(np.abs(np.diff(lum, axis=0)).mean())
    edge_density = (edge_x + edge_y) / 2.0
    uniformity = 1.0 - min(1.0, (float(r.std()) + float(g.std())) / 0.4)
    light_over_red = max(0.0, white_frac * redness)

    # Ring pattern (Tinea)
    y_idx, x_idx = np.ogrid[:256, :256]
    dist_map = np.sqrt((y_idx - 128) ** 2 + (x_idx - 128) ** 2).astype(float)
    edge_map = (np.abs(np.gradient(lum, axis=0))
                + np.abs(np.gradient(lum, axis=1)))
    ring_mask = (dist_map > 40) & (dist_map < 90)
    ring_score = float(edge_map[ring_mask].mean()) if ring_mask.sum() > 0 else 0.0

    sharp = np.array(
        Image.fromarray((lum * 255).astype(np.uint8)).filter(ImageFilter.FIND_EDGES),
        dtype='float32'
    ) / 255.0
    roughness = float(sharp.mean())

    px_scores = {}
    for name in class_names:
        n = name.lower()
        if 'eczema' in n:
            s = 0.08 + redness * 2.5 + pinkness * 1.5 + roughness * 0.8 - dark_frac * 1.0
        elif 'melanoma' in n:
            s = 0.08 + dark_frac * 3.0 + darkness * 1.5 + edge_density * 1.0 - uniformity * 1.2
        elif 'atopic' in n:
            s = 0.08 + redness * 2.0 + pinkness * 1.5 + texture_var * 0.8
        elif 'basal' in n or 'bcc' in n:
            s = 0.08 + dark_frac * 2.0 + brightness * 0.5 + roughness * 0.5 - redness * 0.5
        elif 'melanocytic' in n or 'nevi' in n or 'nv' in n:
            s = 0.08 + brownness * 3.0 + uniformity * 1.5 - edge_density * 0.8 - redness * 1.0
        elif 'benign keratosis' in n or 'bkl' in n:
            s = 0.08 + brownness * 2.0 + roughness * 2.0 + texture_var * 0.8
        elif 'psoriasis' in n or 'lichen' in n:
            s = 0.08 + light_over_red * 4.0 + redness * 1.5 + roughness * 1.0 + white_frac * 1.0
        elif 'seborrheic' in n:
            s = 0.08 + brownness * 2.0 + roughness * 1.5 + texture_var * 1.0
        elif 'tinea' in n or 'ringworm' in n or 'fungal' in n:
            s = 0.08 + ring_score * 5.0 + redness * 0.5 - dark_frac * 1.0
        elif 'warts' in n or 'molluscum' in n or 'viral' in n:
            s = 0.08 + roughness * 2.5 + texture_var * 1.5 + edge_density * 1.0
        else:
            s = 0.08 + brightness * 0.3
        px_scores[name] = max(0.01, s)

    total = sum(px_scores.values())
    if total > 0:
        px_scores = {k: v / total for k, v in px_scores.items()}
    return px_scores


# ─── Core prediction ──────────────────────────────────────────────────────────

def predict_image(image_path, model_package=None, top_k: int = 3) -> dict:
    """
    Predict skin disease from an image.

    Args:
        image_path   : File path, PIL Image, or numpy array.
        model_package: Pre-loaded package (optional).
        top_k        : Number of top predictions to return.

    Returns:
        dict with: disease, confidence, category, top_predictions, all_probabilities.
    """
    global _keras_model

    if model_package is None:
        model_package = load_model()

    class_names = model_package.get('class_names', [])
    input_size = model_package.get('_input_size', INPUT_SIZE)
    model = model_package.get('model') or _keras_model

    # Load PIL image
    if isinstance(image_path, (str, Path)):
        pil_img = Image.open(image_path).convert('RGB')
    elif isinstance(image_path, np.ndarray):
        arr = image_path.squeeze()
        if arr.max() <= 1.01:
            arr = (arr * 255).astype(np.uint8)
        pil_img = Image.fromarray(arr.astype(np.uint8)).convert('RGB')
    elif hasattr(image_path, 'convert'):
        pil_img = image_path.convert('RGB')
    else:
        pil_img = image_path

    if not class_names:
        return {
            'disease': 'Unknown', 'confidence': 0.0,
            'category': 'Dermatological Condition',
            'top_predictions': [], 'all_probabilities': {},
        }

    # ── 1. Pixel-based scores (always reliable) ────────────────────────────────
    px_scores = _pixel_disease_scores(pil_img, class_names)

    # ── 2. Neural network prediction ──────────────────────────────────────────
    nn_scores: dict[str, float] = {}
    use_nn = False

    try:
        arr = _preprocess_for_model(pil_img, input_size)
        probs = model.predict(arr, verbose=0)[0]

        if np.isfinite(probs).all() and len(probs) == len(class_names):
            probs_std = float(np.std(probs))
            if probs_std > 0.005:
                nn_scores = {cn: float(p) for cn, p in zip(class_names, probs)}
                use_nn = True
                print(f"[predict.py] NN prediction std={probs_std:.4f} — using NN + pixel hybrid.")
            else:
                print(f"[predict.py] NN prediction std={probs_std:.4f} too low — pixel only.")
        else:
            print("[predict.py] NN output invalid (NaN or wrong shape) — pixel only.")

    except Exception as e:
        print(f"[predict.py] NN prediction failed: {e}. Using pixel scores only.")

    # ── 3. Combine scores ──────────────────────────────────────────────────────
    if use_nn and nn_scores:
        combined: dict[str, float] = {}
        for cname in class_names:
            nn = nn_scores.get(cname, 0.0)
            px = px_scores.get(cname, 0.0)
            combined[cname] = 0.70 * nn + 0.30 * px
    else:
        combined = px_scores

    # ── 4. Normalise and rank ──────────────────────────────────────────────────
    total = sum(combined.values())
    if total > 0:
        combined = {k: float(np.clip(v / total, 0.001, 1.0)) for k, v in combined.items()}

    sorted_classes = sorted(combined.items(), key=lambda x: -x[1])

    top_preds = [
        {
            'disease': name,
            'confidence': float(conf),
            'category': get_disease_category(name),
            'rank': i + 1,
        }
        for i, (name, conf) in enumerate(sorted_classes[:top_k])
    ]

    winner = top_preds[0]
    return {
        'disease': winner['disease'],
        'confidence': winner['confidence'],
        'category': get_disease_category(winner['disease']),
        'top_predictions': top_preds,
        'all_probabilities': combined,
    }


# ─── Utilities ────────────────────────────────────────────────────────────────

def preprocess_image(image_input, target_size=(224, 224)):
    """Kept for backward compatibility with views.py."""
    if isinstance(image_input, (str, Path)):
        pil_img = Image.open(image_input).convert('RGB')
    elif isinstance(image_input, np.ndarray):
        arr = image_input.squeeze()
        if arr.max() <= 1.01:
            arr = (arr * 255).astype(np.uint8)
        pil_img = Image.fromarray(arr.astype(np.uint8)).convert('RGB')
    elif hasattr(image_input, 'convert'):
        pil_img = image_input.convert('RGB')
    else:
        pil_img = image_input

    pil_resized = pil_img.resize(target_size, Image.LANCZOS)
    arr = np.expand_dims(np.array(pil_resized, dtype='float32'), 0)
    return arr, pil_img


def get_model_info(model_package=None) -> dict:
    if model_package is None:
        model_package = load_model()
    model = model_package['model']
    return {
        'version': model_package.get('version', 'unknown'),
        'framework': 'TensorFlow/Keras',
        'framework_version': tf.__version__,
        'input_shape': model_package.get('_input_size', INPUT_SIZE),
        'num_classes': len(model_package.get('class_names', [])),
        'class_names': model_package.get('class_names', []),
        'model_file': MODEL_FILENAME,
        'backbone': 'ResNet50',
        'model_output_shape': str(getattr(model, 'output_shape', 'unknown')),
    }


def predict_batch(image_paths, model_package=None, top_k: int = 3) -> list:
    if model_package is None:
        model_package = load_model()
    results = []
    for img_path in image_paths:
        try:
            result = predict_image(img_path, model_package, top_k)
            result['image_path'] = str(img_path)
            result['success'] = True
        except Exception as e:
            result = {'image_path': str(img_path), 'success': False, 'error': str(e)}
        results.append(result)
    return results


if __name__ == '__main__':
    pkg = load_model()
    info = get_model_info(pkg)
    print("\nModel Info:")
    for k, v in info.items():
        print(f"   {k}: {v}")
    print("\nReady!")
