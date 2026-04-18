"""
MediSkin AI - Test Prediction Pipeline
Run this from the backend/ directory to verify that predictions differ
for different types of input images.

Usage:
    cd c:\\Users\\shanm\\Downloads\\pro\\backend
    python ml/test_predictions.py
"""

import sys
import os
from pathlib import Path

# Ensure console uses UTF-8 on Windows to avoid emoji encoding crashes
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Make sure backend/ is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
from PIL import Image


# --- Create synthetic test images --------------------------------------------

def make_red_image(size=(224, 224)):
    """Simulate a red/inflamed skin image (Eczema, Psoriasis)."""
    img = np.zeros((*size, 3), dtype=np.uint8)
    img[:, :, 0] = 210   # High red
    img[:, :, 1] = 80    # Low green
    img[:, :, 2] = 80    # Low blue
    noise = np.random.randint(-30, 30, img.shape, dtype=np.int16)
    img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    return Image.fromarray(img)


def make_dark_spotted_image(size=(224, 224)):
    """Simulate a dark lesion image (Melanoma, BCC)."""
    img = np.ones((*size, 3), dtype=np.uint8) * 180
    cx, cy = size[0] // 2, size[1] // 2
    # Vectorised dark circle
    y_arr = np.arange(size[0])[:, None]
    x_arr = np.arange(size[1])[None, :]
    mask  = ((y_arr - cx)**2 + (x_arr - cy)**2) < (size[0] * 0.2) ** 2
    img[mask] = [20, 10, 15]
    noise = np.random.randint(-20, 20, img.shape, dtype=np.int16)
    img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    return Image.fromarray(img)


def make_ring_image(size=(224, 224)):
    """Simulate a ring/annular pattern (Tinea / Ringworm)."""
    img = np.ones((*size, 3), dtype=np.uint8) * [200, 170, 150]
    cx, cy = size[0] // 2, size[1] // 2
    y_arr = np.arange(size[0])[:, None]
    x_arr = np.arange(size[1])[None, :]
    dist  = np.sqrt((y_arr - cx)**2 + (x_arr - cy)**2)
    ring_mask = (dist > 55) & (dist < 80)
    img[ring_mask] = [220, 100, 90]  # reddish ring
    inner_mask = dist < 55
    img[inner_mask] = np.clip(img[inner_mask].astype(int) + 30, 0, 255)  # lighter centre
    noise = np.random.randint(-15, 15, img.shape, dtype=np.int16)
    img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    return Image.fromarray(img)


def make_bumpy_wart_image(size=(224, 224)):
    """Simulate rough verrucous surface (Warts)."""
    img = np.random.randint(120, 200, (*size, 3), dtype=np.uint8)
    return Image.fromarray(img)


def make_normal_skin_image(size=(224, 224)):
    """Simulate normal, even-toned skin."""
    img = np.ones((*size, 3), dtype=np.uint8) * [210, 170, 140]
    noise = np.random.randint(-10, 10, img.shape, dtype=np.int16)
    img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    return Image.fromarray(img)


# --- Run tests ---------------------------------------------------------------

def run_tests():
    print("=" * 65)
    print("   MediSkin AI - Prediction Pipeline Test")
    print("=" * 65)

    from ml.predict import load_model, predict_image, get_model_info

    print("\n[1/6] Loading model...")
    try:
        pkg  = load_model()
        info = get_model_info(pkg)
    except Exception as e:
        print(f"\n[FAIL] Model load FAILED: {e}")
        return False

    print(f"\nModel Info:")
    print(f"   Classes      : {info['num_classes']}")
    print(f"   Input size   : {info['input_shape']}")
    print(f"   Class names  : {info['class_names']}")

    test_cases = [
        ("Red/Inflamed Skin  -- expect Eczema / Psoriasis high",
         make_red_image()),
        ("Dark Spotted Lesion -- expect Melanoma / BCC high",
         make_dark_spotted_image()),
        ("Ring Pattern (Tinea/Ringworm)",
         make_ring_image()),
        ("Bumpy/Rough Patch   -- expect Warts high",
         make_bumpy_wart_image()),
        ("Normal Even-Toned Skin",
         make_normal_skin_image()),
    ]

    top1_diseases = []

    for label, pil_img in test_cases:
        print(f"\n{'─'*65}")
        print(f"  {label}")
        print(f"{'─'*65}")

        result = predict_image(pil_img, model_package=pkg, top_k=3)
        top1   = result['disease']
        conf   = result['confidence']

        print(f"  -> Top prediction: {top1}  ({conf*100:.1f}%)")
        print("  -> Top-3 predictions:")
        for p in result['top_predictions']:
            safe_conf = float(np.nan_to_num(p.get('confidence', 0.0), nan=0.0))
            bar = '#' * int(safe_conf * 20)
            print(f"       {p['rank']}. {p['disease']:<45} {safe_conf*100:5.1f}%  {bar}")

        top1_diseases.append(top1)

    # Diversity check
    print(f"\n{'='*65}")
    unique_top1 = len(set(top1_diseases))
    print(f"  Top-1 results for {len(test_cases)} images: {unique_top1} unique class(es)")
    print(f"  Top-1 predictions: {top1_diseases}")

    if unique_top1 == 1:
        print("\n  [WARNING] All images got the same top-1 prediction.")
        all_passed = False
    elif unique_top1 < len(test_cases) // 2:
        print("\n  [PARTIAL] Some diversity — model partially distinguishing images.")
        all_passed = True
    else:
        print("\n  [PASS] Predictions vary meaningfully across different images!")
        all_passed = True

    print(f"\n{'='*65}")
    return all_passed


if __name__ == '__main__':
    np.random.seed(42)
    success = run_tests()
    sys.exit(0 if success else 1)
