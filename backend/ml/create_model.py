"""
MediSkin AI - Model Creation Script
Creates an EfficientNetB0-based model for skin disease classification.
Preprocessing is EMBEDDED inside the model graph so predict.py never
needs to know which scaler to apply — it just passes raw [0-255] pixels.
"""

import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
import pickle
import json
from pathlib import Path
import numpy as np
import sys
import io

# Fix Windows encoding issues
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Skin disease classes (from the dataset — must match Kaggle training order)
CLASS_NAMES = [
    "Eczema",
    "Melanoma",
    "Atopic Dermatitis",
    "Basal Cell Carcinoma (BCC)",
    "Melanocytic Nevi (NV)",
    "Benign Keratosis-like Lesions (BKL)",
    "Psoriasis Lichen Planus",
    "Seborrheic Keratoses",
    "Tinea Ringworm Fungal Infections",
    "Warts Molluscum Viral Infections"
]


def create_model(num_classes=10, input_shape=(224, 224, 3)):
    """
    Create an EfficientNetB0-based model for skin disease classification.
    Preprocessing (scaling to [-1,1]) is embedded in the model graph via a
    Rescaling layer so inference code simply passes raw [0-255] pixel arrays.

    Args:
        num_classes   : Number of disease classes.
        input_shape   : Input image shape (H, W, 3).

    Returns:
        Compiled Keras model.
    """
    print("[*] Creating EfficientNetB0 model architecture...")

    # ── Inputs ────────────────────────────────────────────────────────────────
    inputs = keras.Input(shape=input_shape, name='input_image')

    # ── Preprocessing embedded in graph ([-1, 1] scaling) ────────────────────
    # This means predict.py can always pass raw [0-255] uint8/float images.
    x = layers.Rescaling(scale=1.0 / 127.5, offset=-1.0, name='rescaling')(inputs)

    # ── EfficientNetB0 backbone (without top) ─────────────────────────────────
    base_model = keras.applications.EfficientNetB0(
        weights='imagenet',
        include_top=False,
        input_tensor=x,
    )
    # Freeze backbone initially — fine-tuning should be done in Kaggle
    base_model.trainable = False

    # ── Classification head ───────────────────────────────────────────────────
    x = base_model.output
    x = layers.GlobalAveragePooling2D(name='global_avg_pool')(x)
    x = layers.BatchNormalization(name='head_bn')(x)
    x = layers.Dense(512, activation='relu', name='dense_1')(x)
    x = layers.Dropout(0.5, name='dropout_1')(x)
    x = layers.Dense(256, activation='relu', name='dense_2')(x)
    x = layers.Dropout(0.3, name='dropout_2')(x)

    # ── Output ────────────────────────────────────────────────────────────────
    outputs = layers.Dense(num_classes, activation='softmax', name='predictions')(x)

    # ── Full model ────────────────────────────────────────────────────────────
    model = keras.Model(inputs=inputs, outputs=outputs,
                        name='mediskin_efficientnetb0')

    # ── Compile ───────────────────────────────────────────────────────────────
    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=1e-3),
        loss='categorical_crossentropy',
        metrics=[
            'accuracy',
            keras.metrics.TopKCategoricalAccuracy(k=3, name='top_3_accuracy'),
            keras.metrics.Precision(name='precision'),
            keras.metrics.Recall(name='recall'),
        ]
    )

    total_params = model.count_params()
    trainable    = sum(tf.size(w).numpy() for w in model.trainable_weights)
    print(f"[+] Model created — total params: {total_params:,} | trainable: {trainable:,}")
    return model


def save_model_as_pkl(model, class_names,
                      save_path='ml/models/skin_disease_classifier.pkl'):
    """
    Save model and metadata as a PKL file.

    Args:
        model       : Compiled Keras model.
        class_names : Ordered list of class names.
        save_path   : Output path for the PKL file.
    """
    print("\n[*] Saving model as PKL file...")

    save_path = Path(save_path)
    save_path.parent.mkdir(parents=True, exist_ok=True)

    # 'preprocessing' = 'builtin' tells predict.py that rescaling is inside
    # the model graph and raw [0-255] float arrays should be passed directly.
    model_package = {
        'model'            : model,
        'class_names'      : class_names,
        'input_shape'      : model.input_shape[1:],   # (H, W, C)
        'preprocessing'    : 'builtin',
        'version'          : '2.0',
        'framework'        : 'tensorflow',
        'framework_version': tf.__version__,
    }

    with open(save_path, 'wb') as f:
        pickle.dump(model_package, f, protocol=pickle.HIGHEST_PROTOCOL)

    file_size = save_path.stat().st_size / (1024 * 1024)
    print(f"[+] Model saved → {save_path.absolute()}  ({file_size:.2f} MB)")

    # Also persist class names as JSON
    class_names_path = save_path.parent / 'class_names.json'
    with open(class_names_path, 'w') as f:
        json.dump(class_names, f, indent=2)
    print(f"    Class names  → {class_names_path}")

    return save_path


if __name__ == "__main__":
    print("=" * 60)
    print("MediSkin AI - Local Model Creation (EfficientNetB0)")
    print("=" * 60)

    model = create_model(num_classes=len(CLASS_NAMES))
    model.summary()
    pkl_path = save_model_as_pkl(model, CLASS_NAMES)

    print("\n" + "=" * 60)
    print("[+] Model creation complete!")
    print(f"    PKL saved to: {pkl_path}")
    print("=" * 60)
    print("\nNext steps:")
    print("  1. Fine-tune on the skin dataset using the Kaggle notebook.")
    print("  2. Copy the resulting PKL to backend/ml/models/")
    print("  3. Test with: python ml/test_predictions.py")
