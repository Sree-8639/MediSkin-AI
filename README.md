# 🧬 MediSkin AI — Automated Skin Disease Identification Platform

<div align="center">

![MediSkin AI](https://img.shields.io/badge/MediSkin-AI-blue?style=for-the-badge&logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCI+PHBhdGggZmlsbD0id2hpdGUiIGQ9Ik0xMiAyQzYuNDggMiAyIDYuNDggMiAxMnM0LjQ4IDEwIDEwIDEwIDEwLTQuNDggMTAtMTBTMTcuNTIgMiAxMiAyem0tMiAxNXYtNEg3bDUtOS41VjExaDNsLTUgOXoiLz48L3N2Zz4=)
![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-5.0-092E20?style=for-the-badge&logo=django&logoColor=white)
![TensorFlow](https://img.shields.io/badge/TensorFlow-2.19-FF6F00?style=for-the-badge&logo=tensorflow&logoColor=white)
![Render](https://img.shields.io/badge/Deployed_on-Render-46E3B7?style=for-the-badge&logo=render&logoColor=white)

**🌐 Live Demo: [https://mediskin-backend.onrender.com](https://mediskin-backend.onrender.com)**

*AI-powered skin disease diagnosis · Hospital recommendations · PDF reports*

</div>

---

## ✨ Features

| Feature | Description |
|---|---|
| 🤖 **AI Diagnosis** | ResNet50 deep learning model — 81.6% accuracy across 10 skin disease classes |
| 🔐 **Authentication** | Username/password + Google OAuth 2.0 sign-in |
| 🏥 **Hospital Finder** | Curated dermatology clinic database across 15+ Indian cities |
| 📄 **PDF Reports** | Downloadable diagnostic reports with confidence scores |
| 📊 **History** | Full prediction history with timestamps in IST |
| 📱 **Responsive** | Mobile-first design, works on all screen sizes |
| 📧 **Email Alerts** | Gmail SMTP — login notifications + password reset |

---

## 🎯 Detected Conditions (10 Classes)

| # | Condition | Severity |
|---|---|---|
| 1 | Eczema | 🟡 Moderate |
| 2 | Melanoma | 🔴 Critical |
| 3 | Atopic Dermatitis | 🟡 Moderate |
| 4 | Basal Cell Carcinoma (BCC) | 🔴 Critical |
| 5 | Melanocytic Nevi (NV) | 🟠 High |
| 6 | Benign Keratosis-like Lesions (BKL) | 🟡 Moderate |
| 7 | Psoriasis / Lichen Planus | 🟡 Moderate |
| 8 | Seborrheic Keratoses | 🟢 Low |
| 9 | Tinea / Ringworm / Fungal Infections | 🟡 Moderate |
| 10 | Warts / Molluscum / Viral Infections | 🟡 Moderate |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Render Cloud                      │
│                                                     │
│  Django (Gunicorn)                                  │
│  ├── HTML Templates (Django-rendered)               │
│  ├── REST API Endpoints (/api/*)                    │
│  ├── Google OAuth 2.0 (django-allauth)              │
│  ├── Static Files (WhiteNoise)                      │
│  └── ML Inference (ResNet50 / TensorFlow)           │
│                                                     │
│  PostgreSQL (Render managed DB)                     │
└─────────────────────────────────────────────────────┘
```

---

## 🚀 Tech Stack

**Backend**
- [Django 5.0](https://djangoproject.com/) — web framework
- [Gunicorn](https://gunicorn.org/) — WSGI server
- [PostgreSQL](https://postgresql.org/) + [dj-database-url](https://github.com/jazzband/dj-database-url) — production DB
- [WhiteNoise](https://whitenoise.readthedocs.io/) — static file serving
- [django-allauth](https://django-allauth.readthedocs.io/) — Google OAuth
- [django-cors-headers](https://github.com/adamchainz/django-cors-headers) — CORS support

**Machine Learning**
- [TensorFlow 2.19](https://tensorflow.org/) + Keras
- ResNet50 fine-tuned on [ISIC / Kaggle Skin Disease Dataset](https://www.kaggle.com/)
- ~25.6M parameters, 224×224 RGB input

**Frontend**
- Vanilla HTML5, CSS3, JavaScript (no framework needed)
- [html2pdf.js](https://github.com/eKoopmans/html2pdf.js) — PDF report generation
- Google Maps Embed API — clinic locator

---

## 📁 Project Structure

```
pro/
├── backend/
│   ├── main/               # Core Django app
│   │   ├── views.py        # All page + API views
│   │   ├── models.py       # UserProfile, SkinPrediction
│   │   ├── urls.py         # URL routing
│   │   └── adapters.py     # Google OAuth adapters
│   ├── mediskin/
│   │   ├── settings.py     # Development settings
│   │   ├── settings_prod.py # Production settings (Render)
│   │   └── urls.py         # Root URL config
│   ├── ml/
│   │   ├── predict.py      # ML inference engine
│   │   ├── models/         # Model weights + metadata (Git-ignored)
│   │   └── create_model.py # Model training script
│   └── manage.py
├── frontend/
│   ├── templates/          # Django HTML templates
│   │   ├── home.html
│   │   ├── login.html
│   │   ├── create-account.html
│   │   ├── diagnostics.html
│   │   ├── profile.html
│   │   └── reset-password.html
│   └── static/
│       ├── css/            # Stylesheets
│       ├── js/             # JavaScript files
│       │   ├── config.js   # API base URL config
│       │   ├── login.js
│       │   ├── diagnostics.js
│       │   └── profile.js
│       └── images/         # Logos, icons
├── requirements.txt        # Python dependencies
├── render.yaml             # Render deployment config
├── render-build.sh         # Build script for Render
└── README.md
```

---

## ⚡ Local Development

### Prerequisites
- Python 3.11+
- Git

### Setup

```powershell
# 1. Clone the repository
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git
cd pro

# 2. Create virtual environment
python -m venv venv
venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
copy backend\.env.example backend\.env
# Edit backend\.env with your credentials

# 5. Download ML model files
# Place skin_disease_classifier.keras in backend/ml/models/
# (File is too large for Git — download from Kaggle or your storage)

# 6. Run migrations
cd backend
python manage.py migrate

# 7. Start development server
python manage.py runserver
```

Open **http://127.0.0.1:8000** in your browser.

---

## ☁️ Deploy on Render (Production)

### 1. Push to GitHub

```bash
git add -A
git commit -m "deploy: production ready"
git push origin main
```

### 2. Create Render Web Service

- Go to [render.com](https://render.com) → **New → Web Service**
- Connect your GitHub repo
- **Build Command:** `./render-build.sh`
- **Start Command:** `cd backend && gunicorn mediskin.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 120`

### 3. Create PostgreSQL Database

- Render Dashboard → **New → PostgreSQL** → name `mediskin-db` → Free plan
- Link it to your web service (auto-sets `DATABASE_URL`)

### 4. Required Environment Variables

| Variable | Value |
|---|---|
| `DJANGO_SETTINGS_MODULE` | `mediskin.settings_prod` |
| `SECRET_KEY` | *(click Generate in Render)* |
| `DEBUG` | `False` |
| `ALLOWED_HOSTS` | `your-app.onrender.com` |
| `CORS_ALLOWED_ORIGINS` | `https://your-app.onrender.com` |
| `CSRF_TRUSTED_ORIGINS` | `https://your-app.onrender.com` |
| `API_BASE_URL` | `https://your-app.onrender.com` |
| `EMAIL_HOST_USER` | `your-gmail@gmail.com` |
| `EMAIL_HOST_PASSWORD` | *(Gmail App Password — 16 chars)* |
| `GOOGLE_CLIENT_ID` | *(from Google Cloud Console)* |
| `GOOGLE_CLIENT_SECRET` | *(from Google Cloud Console)* |
| `SITE_ID` | `1` |

> **ML Model on Render:** The model file (~473MB) cannot be committed to Git. You must use one of:
> - **Git LFS** — `git lfs track "*.keras"` then push
> - **Render Disk** — mount a persistent disk, upload the model file
> - **Remote URL** — download at startup in `render-build.sh`

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/auth/register/` | Create new account |
| `POST` | `/api/auth/login/` | Login with username/password |
| `POST` | `/api/auth/logout/` | Logout |
| `POST` | `/api/auth/reset-password/` | Send temp password via email |
| `POST` | `/api/auth/change-password/` | Change password |
| `POST` | `/api/predict/` | Upload image → AI diagnosis |
| `GET`  | `/api/history/?username=` | Prediction history |
| `GET`  | `/api/profile/data/?username=` | Profile data |
| `POST` | `/api/profile/picture/` | Upload profile picture |
| `POST` | `/api/profile/location/` | Update location |

---

## 🛡️ Security

- All secrets loaded from environment variables (never hardcoded)
- CSRF protection enabled on all form submissions
- HTTPS enforced in production (`SECURE_SSL_REDIRECT = True`)
- HSTS headers set (1 year)
- Session cookies marked `Secure` and `HttpOnly`
- `debug=False` in production
- `.env` excluded from Git

---

## 📊 Model Performance

| Metric | Score |
|---|---|
| Test Accuracy | **81.6%** |
| Precision (macro) | 75.6% |
| Recall (macro) | 77.3% |
| F1 Score (macro) | **76.1%** |
| F1 Score (weighted) | 81.7% |

---

## 📜 License

This project is developed as part of the **Springboard Internship 2025 — Batch 7** program.

---

## ⚕️ Medical Disclaimer

> **This application is for informational and educational purposes only.** It does not constitute medical advice, diagnosis, or treatment. Always consult a qualified dermatologist for professional medical evaluation.

---

<div align="center">
Made with ❤️ by the MediSkin AI Team · Springboard Internship 2025
</div>
