"""
MediSkin AI — Deploy to Hugging Face Spaces
=============================================
This script automates the full deployment:
  1. Creates a HF model repository and uploads the .h5 model file
  2. Creates a HF Space (Docker SDK) and pushes all project files
  3. Configures environment variables (secrets) on the Space

Prerequisites:
  pip install huggingface_hub
  huggingface-cli login    (or set HF_TOKEN env var)

Usage:
  python deploy_to_hf.py --username YOUR_HF_USERNAME
"""

import argparse
import os
import shutil
import sys
from pathlib import Path

try:
    from huggingface_hub import (
        HfApi,
        create_repo,
        upload_file,
        upload_folder,
    )
except ImportError:
    print("❌  huggingface_hub not installed. Run: pip install huggingface_hub")
    sys.exit(1)


# ─── Configuration ────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent
BACKEND_DIR = PROJECT_ROOT / "backend"
MODEL_DIR = BACKEND_DIR / "ml" / "models"
MODEL_FILE = MODEL_DIR / "skin_disease_classifier.h5"

# Files to copy to the Space repo
SPACE_FILES = [
    "Dockerfile",
    "hf_start.sh",
    "requirements.txt",
    ".dockerignore",
]

SPACE_DIRS = [
    "backend",
    "frontend",
]

# Files/dirs to EXCLUDE when uploading to Space
EXCLUDE_PATTERNS = [
    "*.pkl",
    "*.h5",
    "*.keras",
    "*.pt",
    "*.pth",
    "__pycache__",
    "*.pyc",
    "venv",
    ".venv",
    "db.sqlite3",
    "*.code-workspace",
    ".env",
    "temp_uploads",
    "media",
    ".ipynb_checkpoints",
]


def parse_args():
    parser = argparse.ArgumentParser(description="Deploy MediSkin AI to Hugging Face")
    parser.add_argument("--username", required=True, help="Your Hugging Face username")
    parser.add_argument("--model-repo", default="skin-disease-model",
                        help="Name for the model repository (default: skin-disease-model)")
    parser.add_argument("--space-name", default="mediskin-ai",
                        help="Name for the HF Space (default: mediskin-ai)")
    parser.add_argument("--skip-model", action="store_true",
                        help="Skip model upload (if already uploaded)")
    parser.add_argument("--private", action="store_true",
                        help="Make the Space private")
    return parser.parse_args()


def upload_model(api: HfApi, repo_id: str):
    """Upload the .h5 model file to a HF model repository."""
    print(f"\n{'='*60}")
    print(f"  Step 1: Upload Model to  {repo_id}")
    print(f"{'='*60}")

    # Create model repo
    create_repo(repo_id, repo_type="model", exist_ok=True)
    print(f"  ✅ Model repo ready: https://huggingface.co/{repo_id}")

    if not MODEL_FILE.exists():
        print(f"  ❌ Model file not found: {MODEL_FILE}")
        print(f"     Available files: {[f.name for f in MODEL_DIR.iterdir()]}")
        sys.exit(1)

    size_mb = MODEL_FILE.stat().st_size / (1024 * 1024)
    print(f"  📦 Uploading {MODEL_FILE.name} ({size_mb:.1f} MB)...")

    upload_file(
        path_or_fileobj=str(MODEL_FILE),
        path_in_repo="skin_disease_classifier.h5",
        repo_id=repo_id,
        repo_type="model",
    )
    print(f"  ✅ Model uploaded!")

    # Also upload the JSON metadata files
    json_files = [
        "class_names.json",
        "severity_codes.json",
        "severity_levels.json",
        "severity_summary.json",
        "label_mapping.json",
        "raw_class_names.json",
        "model_card.json",
    ]
    for jf in json_files:
        jf_path = MODEL_DIR / jf
        if jf_path.exists():
            upload_file(
                path_or_fileobj=str(jf_path),
                path_in_repo=jf,
                repo_id=repo_id,
                repo_type="model",
            )
            print(f"  ✅ Uploaded {jf}")


def prepare_space_staging(staging_dir: Path):
    """Copy project files to a staging directory for upload, excluding model files."""
    if staging_dir.exists():
        shutil.rmtree(staging_dir)
    staging_dir.mkdir(parents=True)

    # Copy individual files
    for fname in SPACE_FILES:
        src = PROJECT_ROOT / fname
        if src.exists():
            shutil.copy2(src, staging_dir / fname)
            print(f"  📄 {fname}")

    # Copy the HF README as the Space's README.md
    hf_readme = PROJECT_ROOT / "HF_README.md"
    if hf_readme.exists():
        shutil.copy2(hf_readme, staging_dir / "README.md")
        print(f"  📄 README.md (from HF_README.md)")

    # Copy directories with exclusions
    for dname in SPACE_DIRS:
        src_dir = PROJECT_ROOT / dname
        dst_dir = staging_dir / dname
        if src_dir.exists():
            _copy_filtered(src_dir, dst_dir)
            print(f"  📁 {dname}/")


def _copy_filtered(src: Path, dst: Path):
    """Copy directory tree, excluding patterns."""
    import fnmatch

    for item in src.iterdir():
        rel_name = item.name

        # Check exclude patterns
        skip = False
        for pat in EXCLUDE_PATTERNS:
            if fnmatch.fnmatch(rel_name, pat):
                skip = True
                break
        if skip:
            continue

        dest_item = dst / rel_name
        if item.is_dir():
            _copy_filtered(item, dest_item)
        else:
            dest_item.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, dest_item)


def deploy_space(api: HfApi, space_id: str, model_repo_id: str, private: bool):
    """Create the HF Space and upload project files."""
    print(f"\n{'='*60}")
    print(f"  Step 2: Deploy Space to  {space_id}")
    print(f"{'='*60}")

    # Create Space
    create_repo(
        space_id,
        repo_type="space",
        space_sdk="docker",
        private=private,
        exist_ok=True,
    )
    print(f"  ✅ Space created: https://huggingface.co/spaces/{space_id}")

    # Prepare staging directory
    staging_dir = PROJECT_ROOT / "_hf_staging"
    print(f"\n  Preparing files...")
    prepare_space_staging(staging_dir)

    # Upload
    print(f"\n  Uploading to HF Space...")
    upload_folder(
        folder_path=str(staging_dir),
        repo_id=space_id,
        repo_type="space",
    )
    print(f"  ✅ Files uploaded!")

    # Clean up staging
    shutil.rmtree(staging_dir, ignore_errors=True)

    # Set secrets / environment variables
    print(f"\n  Setting environment variables...")
    secrets = {
        "HF_MODEL_REPO": model_repo_id,
        "SECRET_KEY": "django-production-" + os.urandom(16).hex(),
        "DEBUG": "False",
        "ALLOWED_HOSTS": "*",
    }
    for key, value in secrets.items():
        try:
            api.add_space_secret(space_id, key, value)
            print(f"  🔑 {key} = {'***' if 'KEY' in key or 'SECRET' in key else value}")
        except Exception as e:
            print(f"  ⚠️  Could not set {key}: {e}")


def main():
    args = parse_args()

    api = HfApi()
    model_repo_id = f"{args.username}/{args.model_repo}"
    space_id = f"{args.username}/{args.space_name}"

    print("\n🧬 MediSkin AI — Hugging Face Deployment")
    print(f"   Username:    {args.username}")
    print(f"   Model repo:  {model_repo_id}")
    print(f"   Space:       {space_id}")
    print(f"   Private:     {args.private}")

    # Step 1: Upload model
    if not args.skip_model:
        upload_model(api, model_repo_id)
    else:
        print("\n  ⏭️  Skipping model upload (--skip-model)")

    # Step 2: Deploy Space
    deploy_space(api, space_id, model_repo_id, args.private)

    # Done
    print(f"\n{'='*60}")
    print(f"  🎉 Deployment complete!")
    print(f"{'='*60}")
    print(f"\n  🌐 Your app: https://huggingface.co/spaces/{space_id}")
    print(f"  📦 Model:    https://huggingface.co/{model_repo_id}")
    print(f"\n  ⏳ The Space may take 3-5 minutes to build the Docker image.")
    print(f"  📝 Demo login: demo / demo123")
    print()


if __name__ == "__main__":
    main()
