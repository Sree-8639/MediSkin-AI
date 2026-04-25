from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from .models import UserProfile, SkinPrediction
import os
import sys
import json
import random
import string
from pathlib import Path

# Add parent directory to path for ml module
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Pre-load ML model on server start for instant predictions
print("[*] Pre-loading ML model for fast predictions...")
try:
    from ml.predict import load_model
    load_model()  # Load model into cache immediately — path resolved by predict.py
    print("[+] ML model pre-loaded successfully! Predictions will be instant.")
except Exception as e:
    print(f"[!] Warning: Could not pre-load ML model: {e}")

# ─── Shared email utility ──────────────────────────────────────────────────────
def _send_email_safe(subject, body, recipient_email):
    """
    Send a plain-text email using Django's configured backend.
    - Uses explicit utf-8 encoding to prevent Windows charmap errors.
    - Logs success/failure but never raises, so callers are never interrupted.
    Returns True on success, False on failure.
    """
    try:
        from django.conf import settings as _cfg
        from django.core.mail import EmailMessage as _EM
        msg = _EM(
            subject=subject,
            body=body,
            from_email=_cfg.DEFAULT_FROM_EMAIL,
            to=[recipient_email],
        )
        msg.encoding = 'utf-8'
        msg.send(fail_silently=False)
        print(f"[EMAIL] Sent '{subject}' -> {recipient_email}")
        return True
    except Exception as _e:
        print(f"[EMAIL] Failed to send '{subject}' -> {recipient_email}: {_e}")
        return False



def split_full_name(full_name):
    """Split full name into first and last name"""
    if not full_name:
        return '', ''
    parts = full_name.strip().split(maxsplit=1)
    if len(parts) == 1:
        return parts[0], ''
    return parts[0], parts[1]

def combine_names(first_name, last_name):
    """Combine first and last name into full name"""
    names = [first_name.strip(), last_name.strip()]
    return ' '.join([n for n in names if n])

def _ctx(extra=None):
    """Return a base template context that includes the backend API base URL.
    config.js reads this value from the <meta name='api-base-url'> tag and
    exposes it as window.MEDISKIN_API_BASE so all JS fetch() calls work
    whether the frontend is same-origin (dev) or cross-origin (Vercel).
    """
    from django.conf import settings as _s
    ctx = {'API_BASE_URL': getattr(_s, 'API_BASE_URL', '')}
    if extra:
        ctx.update(extra)
    return ctx

def _site_url():
    """Return the public-facing site URL for use in email bodies.
    Uses API_BASE_URL in production; falls back to localhost in dev.
    """
    from django.conf import settings as _s
    base = getattr(_s, 'API_BASE_URL', '') or 'http://127.0.0.1:8000'
    return base.rstrip('/')

@login_required(login_url='/login/')
def home(request):
    """Home page view — requires login, prevents client-side flash redirect"""
    return render(request, 'home.html', _ctx())

def login_view(request):
    """Login page view"""
    return render(request, 'login.html', _ctx())

def create_account(request):
    """Create account page view"""
    return render(request, 'create-account.html', _ctx())

@login_required(login_url='/login/')
def diagnostics(request):
    """Diagnostics page view — requires authentication"""
    return render(request, 'diagnostics.html', _ctx())


@login_required(login_url='/login/')
def profile(request):
    """Profile page view — requires authentication"""
    return render(request, 'profile.html', _ctx())

def reset_password(request):
    """Reset password page — handles GET (display form) and POST (process reset)."""
    if request.method == 'GET':
        return render(request, 'reset-password.html', _ctx())

    # ── POST: process the password reset ─────────────────────────────────────
    email = request.POST.get('email', '').strip()

    if not email:
        return render(request, 'reset-password.html', _ctx({
            'form_error': 'Please enter your email address.'
        }))

    try:
        # Use filter().first() to avoid MultipleObjectsReturned when several
        # accounts share the same email — reset the most recently created one
        user = User.objects.filter(email=email).order_by('-date_joined').first()
        if user is None:
            raise User.DoesNotExist

        # 1. Generate a random 12-character temporary password
        temp_password = ''.join(
            random.choices(string.ascii_letters + string.digits, k=12)
        )

        # 2. Save it to the database immediately
        user.set_password(temp_password)
        user.save()
        print(f"[DEBUG] Temporary password set for: {user.username}")

        # 3. Build email body (ASCII-only — avoids Windows charmap errors)
        subject = 'MediSkin AI - Your Temporary Password'
        body = (
            f"Hello {user.username},\n\n"
            f"You requested a password reset for your MediSkin AI account.\n\n"
            f"Your temporary password is:\n\n"
            f"    {temp_password}\n\n"
            f"Please log in with this password, then change it from your Profile\n"
            f"under Account Security.\n\n"
            f"If you did not request this, contact us immediately.\n\n"
            f"-- MediSkin AI Team"
        )

        # 4. Send via SMTP — password is ONLY delivered by email, never shown on site
        email_sent = _send_email_safe(subject, body, email)
        print(f"[DEBUG] Reset email dispatched to: {email} (sent={email_sent})")

        # 5. Render success — never pass temp_password to the template
        context = {
            'reset_success': True,
            'reset_email': email,
            'email_sent': email_sent,
        }
        if not email_sent:
            context['email_error'] = (
                'We could not deliver the email right now. '
                'Please try again later or contact support.'
            )

        return render(request, 'reset-password.html', _ctx(context))

    except User.DoesNotExist:
        return render(request, 'reset-password.html', _ctx({
            'form_error': 'No account found with that email address.',
            'submitted_email': email,
        }))


def google_oauth_complete(request):
    """
    Bridge view: called by allauth's LOGIN_REDIRECT_URL after a successful
    Google OAuth login.  Converts the Django session user into the same
    sessionStorage shape that the existing JS auth flow expects, then
    redirects to the home page so the user lands fully authenticated.
    """
    if not request.user.is_authenticated:
        return redirect('/login/')

    user = request.user

    # Build user data — mirror the shape returned by /api/auth/login/
    try:
        prof = user.profile
        full_name = prof.full_name or user.get_full_name() or user.username
        first, *rest = full_name.split(' ', 1)
        last = rest[0] if rest else ''
        picture_url = prof.profile_picture.url if prof.profile_picture else ''
        phone = prof.phone or ''
        country = prof.country or ''
        state = prof.state or ''
        district = prof.district or ''
        city = prof.city or ''
        pincode = prof.pincode or ''
        profile_complete = prof.profile_complete
    except UserProfile.DoesNotExist:
        full_name = user.get_full_name() or user.username
        first, *rest = full_name.split(' ', 1)
        last = rest[0] if rest else ''
        picture_url = profile_complete = ''
        phone = country = state = district = city = pincode = ''
        profile_complete = False

    # ── Send greeting email in background (non-blocking) ──────────────────────
    display_name = full_name.split()[0] if full_name else user.username
    if user.email:
        import threading
        _email_addr = user.email
        _body = (
            f"Hi {display_name},\n\n"
            f"Welcome to MediSkin AI! You have successfully signed in with Google.\n\n"
            f"Account : {user.username}\n"
            f"Email   : {user.email}\n\n"
            f"Head to your dashboard to upload a skin image and get\n"
            f"an AI-powered skin disease diagnosis in seconds.\n\n"
            f"Dashboard : {_site_url()}/diagnostics/\n\n"
            f"If this wasn't you, please contact us immediately.\n\n"
            f"-- MediSkin AI Team"
        )
        threading.Thread(
            target=_send_email_safe,
            args=('Welcome to MediSkin AI!', _body, _email_addr),
            daemon=True,
        ).start()
        print(f"[EMAIL] Greeting queued for {user.email} on Google OAuth login")

    user_data = {
        'username': user.username,
        'email': user.email,
        'firstName': first,
        'lastName': last,
        'fullName': full_name,
        'phone': phone,
        'profileComplete': profile_complete,
        'country': country,
        'state': state,
        'district': district,
        'city': city,
        'pincode': pincode,
        'profilePictureUrl': picture_url,
        'isLoggedIn': True,
        'loginMethod': 'google',
    }

    # Inline HTML page that writes to sessionStorage then navigates to /
    # This is the simplest, most reliable bridge between server session and
    # the client-side sessionStorage used by the existing JS auth system.
    user_data_json = json.dumps(user_data)
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Signing in with Google…</title>
    <style>
        body {{
            background: #0a1628;
            display: flex;
            align-items: center;
            justify-content: center;
            height: 100vh;
            margin: 0;
            font-family: 'Segoe UI', sans-serif;
            color: #e2e8f0;
        }}
        .spinner {{
            width: 48px; height: 48px;
            border: 4px solid #1e3a5f;
            border-top-color: #3b82f6;
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
            margin-bottom: 16px;
        }}
        @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
        .msg {{ font-size: 1rem; opacity: .8; }}
        .box {{ text-align: center; }}
    </style>
</head>
<body>
    <div class="box">
        <div class="spinner"></div>
        <div class="msg">Signing you in with Google…</div>
    </div>
    <script>
        try {{
            sessionStorage.setItem('currentUser', JSON.stringify({user_data_json}));
        }} catch(e) {{
            console.warn('sessionStorage unavailable', e);
        }}
        window.location.replace('/');
    </script>
</body>
</html>"""
    return HttpResponse(html)

@csrf_exempt
def predict_skin_disease(request):
    """
    API endpoint for skin disease prediction
    Accepts image upload and returns ML prediction
    """
    if request.method != 'POST':
        return JsonResponse({
            'success': False,
            'error': 'Only POST requests are allowed'
        }, status=405)
    
    if 'image' not in request.FILES:
        return JsonResponse({
            'success': False,
            'error': 'No image file provided'
        }, status=400)
    
    try:
        # Get uploaded image
        image_file = request.FILES['image']
        
        # Save temporarily
        temp_dir = Path('temp_uploads')
        temp_dir.mkdir(exist_ok=True)
        
        temp_path = temp_dir / image_file.name
        with open(temp_path, 'wb+') as destination:
            for chunk in image_file.chunks():
                destination.write(chunk)
        
        # Import and use ML prediction (model is already cached)
        from ml.predict import predict_image
        
        # Make prediction (FAST - model is pre-loaded)
        result = predict_image(str(temp_path), top_k=3)
        
        # Clean up temp file
        if temp_path.exists():
            temp_path.unlink()

        # Persist prediction — save by username from POST data (session auth not required)
        username_for_save = request.POST.get('username', '').strip()
        if not username_for_save and request.user.is_authenticated:
            username_for_save = request.user.username
        
        if username_for_save:
            try:
                from django.contrib.auth.models import User as AuthUser
                save_user = AuthUser.objects.get(username=username_for_save)
                SkinPrediction.objects.create(
                    user=save_user,
                    disease=result['disease'],
                    confidence=round(result['confidence'] * 100, 2),
                    image_name=image_file.name,
                    top_predictions=[
                        {
                            'rank': pred['rank'],
                            'disease': pred['disease'],
                            'confidence': round(pred['confidence'] * 100, 2)
                        }
                        for pred in result['top_predictions']
                    ]
                )
                print(f"[DEBUG] Prediction saved for user: {username_for_save}")
            except Exception as save_error:
                print(f"[DEBUG] Failed to save prediction: {save_error}")
        
        # Return successful response
        return JsonResponse({
            'success': True,
            'prediction': {
                'disease': result['disease'],
                'confidence': round(result['confidence'] * 100, 2),
                'category': result.get('category', 'Dermatological Condition'),
                'top_predictions': [
                    {
                        'rank': pred['rank'],
                        'disease': pred['disease'],
                        'confidence': round(pred['confidence'] * 100, 2),
                        'category': pred.get('category', 'Dermatological Condition')
                    }
                    for pred in result['top_predictions']
                ]
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@csrf_exempt
def register_user(request):
    """API endpoint for user registration"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Only POST allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        
        # Extract data
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '')
        full_name = data.get('fullName', '').strip()
        phone = data.get('phone', '').strip()
        
        print(f"[DEBUG] Registration attempt - Username: {username}, Email: {email}")
        
        # Validation - phone is optional
        if not all([username, email, password, full_name]):
            return JsonResponse({'success': False, 'error': 'All required fields must be filled'}, status=400)
        
        # Check if username exists
        if User.objects.filter(username=username).exists():
            print(f"[DEBUG] Username already exists: {username}")
            return JsonResponse({'success': False, 'error': 'Username already exists'}, status=400)
        
        # Check if email exists
        if User.objects.filter(email=email).exists():
            print(f"[DEBUG] Email already registered: {email}")
            return JsonResponse({'success': False, 'error': 'Email already registered'}, status=400)
        
        # Create user
        user = User.objects.create_user(username=username, email=email, password=password)
        print(f"[DEBUG] User created successfully: {user.username} (ID: {user.id})")
        
        # Create profile
        profile = UserProfile.objects.create(
            user=user,
            full_name=full_name,
            phone=phone or None,
            profile_complete=False
        )
        print(f"[DEBUG] Profile created successfully for user: {user.username}")

        # Send personalised welcome email immediately after signup
        first_name = full_name.split()[0] if full_name else username
        _send_email_safe(
            subject='Welcome to MediSkin AI!',
            body=(
                f"Hi {first_name},\n\n"
                f"Welcome to MediSkin AI! Your account has been created successfully.\n\n"
                f"Username: {username}\n"
                f"Email: {email}\n\n"
                f"You can now log in and start using our AI-powered skin disease\n"
                f"diagnosis platform. Upload a photo and get an instant analysis.\n\n"
                f"Get started: {_site_url()}/login/\n\n"
                f"-- MediSkin AI Team"
            ),
            recipient_email=email,
        )

        # Do not auto-login after registration - require user to login manually

        return JsonResponse({
            'success': True,
            'message': 'Account created successfully',
            'user': {
                'username': user.username,
                'email': user.email,
                'fullName': full_name,
                'phone': phone,
                'profileComplete': False
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        print(f"[DEBUG] Exception in registration: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@csrf_exempt
def login_user(request):
    """API endpoint for user login"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Only POST allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        print(f"[DEBUG] Login attempt - Username: {username}")
        
        if not username or not password:
            return JsonResponse({'success': False, 'error': 'Username and password required'}, status=400)
        
        # Check if user exists
        try:
            user_exists = User.objects.filter(username=username).exists()
            print(f"[DEBUG] User exists in database: {user_exists}")
        except Exception as e:
            print(f"[DEBUG] Error checking user: {e}")
        
        # Authenticate user
        user = authenticate(request, username=username, password=password)
        print(f"[DEBUG] Authentication result: {user}")
        
        if user is not None:
            login(request, user)

            # ── Send greeting email in background (non-blocking for fast login) ─
            if user.email:
                import threading
                try:
                    prof = user.profile
                    display_name = prof.full_name.split()[0] if prof.full_name else user.username
                except Exception:
                    display_name = user.username
                _email_user = user.email
                _email_name = display_name
                _email_username = user.username
                def _send_login_email():
                    _send_email_safe(
                        subject='Welcome to MediSkin AI!',
                        body=(
                            f"Hi {_email_name},\n\n"
                            f"Welcome to MediSkin AI! You have successfully signed in.\n\n"
                            f"Account : {_email_username}\n"
                            f"Email   : {_email_user}\n\n"
                            f"Head to your dashboard to upload a skin image and get\n"
                            f"an AI-powered skin disease diagnosis in seconds.\n\n"
                            f"Dashboard : {_site_url()}/diagnostics/\n\n"
                            f"If this wasn't you, please reset your password immediately.\n\n"
                            f"-- MediSkin AI Team"
                        ),
                        recipient_email=_email_user,
                    )
                threading.Thread(target=_send_login_email, daemon=True).start()
                print(f"[EMAIL] Greeting email queued for {user.email} on login")

            # Get profile data
            try:
                profile = user.profile
                first_name, last_name = split_full_name(profile.full_name)
                picture_url = profile.profile_picture.url if profile.profile_picture else None
                user_data = {
                    'username': user.username,
                    'email': user.email,
                    'firstName': first_name,
                    'lastName': last_name,
                    'fullName': profile.full_name,
                    'phone': profile.phone,
                    'profileComplete': profile.profile_complete,
                    'country': profile.country or '',
                    'state': profile.state or '',
                    'district': profile.district or '',
                    'city': profile.city or '',
                    'pincode': profile.pincode or '',
                    'profilePictureUrl': picture_url or ''
                }
            except UserProfile.DoesNotExist:
                first_name, last_name = split_full_name(username)
                user_data = {
                    'username': user.username,
                    'email': user.email,
                    'firstName': first_name,
                    'lastName': last_name,
                    'fullName': username,
                    'phone': '',
                    'profileComplete': False
                }
            
            return JsonResponse({
                'success': True,
                'message': 'Login successful',
                'user': user_data
            })
        else:
            print(f"[DEBUG] Authentication failed for username: {username}")
            return JsonResponse({'success': False, 'error': 'Invalid username or password'}, status=401)
            
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        print(f"[DEBUG] Exception in login: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@csrf_exempt
def logout_user(request):
    """API endpoint for user logout"""
    logout(request)
    return JsonResponse({'success': True, 'message': 'Logged out successfully'})

@csrf_exempt
def reset_password_user(request):
    """API endpoint for password reset — generates a temporary password and emails it.
    The temporary password is NEVER returned in the HTTP response; it is sent by email only.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Only POST allowed'}, status=405)

    try:
        data = json.loads(request.body)
        email = data.get('email', '').strip()

        if not email:
            return JsonResponse({'success': False, 'error': 'Email required'}, status=400)

        # Find user by email — use filter to avoid MultipleObjectsReturned
        user = User.objects.filter(email=email).order_by('-date_joined').first()
        if user is None:
            return JsonResponse(
                {'success': False, 'error': 'No account found with that email address'},
                status=404
            )

        # 1. Generate a random 12-character temporary password
        temp_password = ''.join(
            random.choices(string.ascii_letters + string.digits, k=12)
        )

        # 2. Persist immediately so the user can log in as soon as the email arrives
        user.set_password(temp_password)
        user.save()
        print(f"[DEBUG] Temporary password set for: {user.username}")

        # 3. Build secure email — password travels via email, NEVER via HTTP response
        subject = 'MediSkin AI - Your Temporary Password'
        body = (
            f"Hello {user.username},\n\n"
            f"You requested a password reset for your MediSkin AI account.\n\n"
            f"Your temporary password is:\n\n"
            f"    {temp_password}\n\n"
            f"Please log in using this temporary password and then change it immediately "
            f"from your Profile -> Account Security section.\n\n"
            f"If you did not request this reset, please contact us immediately.\n\n"
            f"-- MediSkin AI Team"
        )

        # 4. Send — never expose the password in the response regardless of outcome
        email_sent = _send_email_safe(subject, body, email)
        print(f"[DEBUG] Password reset email dispatched to: {email} (sent={email_sent})")

        if email_sent:
            return JsonResponse({
                'success': True,
                'message': (
                    f'A temporary password has been sent to {email}. '
                    f'Please check your inbox (and spam folder).'
                )
            })
        else:
            # Email failed — user is already locked out of the old password.
            # Inform them to retry or contact support; do NOT reveal the password here.
            return JsonResponse({
                'success': False,
                'error': (
                    'Your password was reset but we could not deliver the email. '
                    'Please try again or contact support.'
                )
            }, status=503)

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        print(f"[DEBUG] Exception in reset_password_user: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@csrf_exempt
def change_password(request):
    """API endpoint for changing password (requires current password)"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Only POST allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        username = data.get('username', '').strip()
        current_password = data.get('currentPassword', '')
        new_password = data.get('newPassword', '')
        
        if not username or not current_password or not new_password:
            return JsonResponse({'success': False, 'error': 'All fields required'}, status=400)
        
        # Authenticate user with current password
        user = authenticate(request, username=username, password=current_password)
        
        if user is not None:
            # Set new password
            user.set_password(new_password)
            user.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Password changed successfully'
            })
        else:
            return JsonResponse({'success': False, 'error': 'Current password is incorrect'}, status=401)
            
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@csrf_exempt
def get_prediction_history(request):
    """API endpoint to get user's prediction history"""
    if request.method != 'GET':
        return JsonResponse({'success': False, 'error': 'Only GET allowed'}, status=405)
    
    try:
        # Get username from query params
        username = request.GET.get('username', '').strip()
        
        if not username:
            return JsonResponse({'success': False, 'error': 'Username required'}, status=400)
        
        # Find user
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'User not found'}, status=404)
        
        # Get user's predictions, ordered by most recent first
        predictions = SkinPrediction.objects.filter(user=user).order_by('-created_at')
        
        # Format predictions for response — all times in IST (Asia/Kolkata)
        import pytz
        ist = pytz.timezone('Asia/Kolkata')
        
        history = []
        for pred in predictions:
            # Convert to IST
            created_ist = pred.created_at.astimezone(ist) if pred.created_at.tzinfo else pred.created_at
            history.append({
                'id': pred.id,
                'disease': pred.disease,
                'confidence': float(pred.confidence),
                'imageName': pred.image_name,
                'topPredictions': pred.top_predictions,
                'createdAt': created_ist.strftime('%Y-%m-%d %H:%M:%S'),
                'date': created_ist.strftime('%d %B %Y'),
                'time': created_ist.strftime('%I:%M %p IST')
            })
        
        return JsonResponse({
            'success': True,
            'history': history,
            'count': len(history)
        })
        
    except Exception as e:
        print(f"[DEBUG] Exception in get_prediction_history: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@csrf_exempt
def update_profile_location(request):
    """API endpoint to update user's location details"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Only POST allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        username = data.get('username', '').strip()
        
        if not username:
            return JsonResponse({'success': False, 'error': 'Username required'}, status=400)
        
        # Find user
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'User not found'}, status=404)
        
        # Get or create user profile
        profile, created = UserProfile.objects.get_or_create(user=user)
        
        # Update location fields
        profile.country = data.get('country', '')
        profile.state = data.get('state', '')
        profile.district = data.get('district', '')
        profile.city = data.get('city', '')
        profile.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Location updated successfully'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        print(f"[DEBUG] Exception in update_profile_location: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@csrf_exempt
def update_profile_picture(request):
    """API endpoint to update user's profile picture"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Only POST allowed'}, status=405)
    
    try:
        username = request.POST.get('username', '').strip()
        
        if not username:
            return JsonResponse({'success': False, 'error': 'Username required'}, status=400)
        
        if 'profile_picture' not in request.FILES:
            return JsonResponse({'success': False, 'error': 'No image file provided'}, status=400)
        
        # Find user
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'User not found'}, status=404)
        
        # Get or create user profile
        profile, created = UserProfile.objects.get_or_create(user=user)
        
        # Save the profile picture
        profile_picture = request.FILES['profile_picture']
        
        # Delete old profile picture if exists
        if profile.profile_picture:
            try:
                default_storage.delete(profile.profile_picture.name)
            except:
                pass
        
        # Save new profile picture
        profile.profile_picture = profile_picture
        profile.save()
        
        # Return the URL of the saved image
        picture_url = profile.profile_picture.url if profile.profile_picture else None
        
        return JsonResponse({
            'success': True,
            'message': 'Profile picture updated successfully',
            'picture_url': picture_url
        })
        
    except Exception as e:
        print(f"[DEBUG] Exception in update_profile_picture: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@csrf_exempt
def get_profile_data(request):
    """API endpoint to get user's profile data"""
    if request.method != 'GET':
        return JsonResponse({'success': False, 'error': 'Only GET allowed'}, status=405)
    
    try:
        username = request.GET.get('username', '').strip()
        
        if not username:
            return JsonResponse({'success': False, 'error': 'Username required'}, status=400)
        
        # Find user
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'User not found'}, status=404)
        
        # Get user profile
        try:
            profile = UserProfile.objects.get(user=user)
            picture_url = profile.profile_picture.url if profile.profile_picture else None
        except UserProfile.DoesNotExist:
            profile = None
            picture_url = None
        
        return JsonResponse({
            'success': True,
            'profile': {
                'country': profile.country if profile else '',
                'state': profile.state if profile else '',
                'district': profile.district if profile else '',
                'city': profile.city if profile else '',
                'phone': profile.phone if profile else '',
                'profile_picture_url': picture_url
            }
        })
        
    except Exception as e:
        print(f"[DEBUG] Exception in get_profile_data: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# ─────────────────────────────────────────────────────────────────────────────
# PDF Report Generation  (server-side, ReportLab)
# ─────────────────────────────────────────────────────────────────────────────

DISEASE_INFO = {
    "acne": [
        "Acne vulgaris is a chronic inflammatory condition of the pilosebaceous unit. It arises when hair follicles become plugged with oil (sebum) and dead skin cells, creating an environment for Cutibacterium acnes bacteria to proliferate.",
        "Management includes topical retinoids, benzoyl peroxide, antibiotics, and (in severe cases) oral isotretinoin. Regular gentle cleansing, avoiding comedogenic products, and not picking lesions are key lifestyle measures."
    ],
    "eczema": [
        "Atopic dermatitis (eczema) is a chronic, relapsing inflammatory skin disorder characterised by pruritus, erythema, and lichenification. It results from a combination of genetic epidermal barrier defects and dysregulated immune responses (Th2 polarisation).",
        "First-line treatment involves daily emollient use, mild topical corticosteroids during flares, and avoiding known triggers such as harsh soaps, allergens and extreme temperatures."
    ],
    "psoriasis": [
        "Psoriasis is an immune-mediated condition in which T-cell activation drives keratinocyte hyperproliferation, producing the characteristic silvery-scaled erythematous plaques. It affects approximately 2–3 % of the global population.",
        "Therapies range from topical corticosteroids and vitamin D analogues for mild disease to phototherapy, methotrexate, cyclosporin, or biologic agents (TNF-α, IL-17, IL-23 inhibitors) for moderate-to-severe cases."
    ],
    "melanoma": [
        "Melanoma is the most aggressive form of skin cancer, originating from melanocytes. Risk factors include UV exposure, fair skin, personal or family history, and multiple atypical nevi. It can metastasise rapidly if not detected early.",
        "Immediate dermatological evaluation is essential. Early-stage lesions are treated by surgical excision; advanced disease may require immunotherapy (checkpoint inhibitors), targeted therapy (BRAF/MEK inhibitors), or combination approaches."
    ],
    "rosacea": [
        "Rosacea is a chronic vascular and inflammatory facial dermatosis presenting with persistent erythema, telangiectasia, papules, pustules, and sometimes rhinophyma. Triggers include UV, heat, alcohol, spicy food, and emotional stress.",
        "Treatment includes topical metronidazole, azelaic acid, or ivermectin; oral doxycycline for papulopustular subtypes; and laser/IPL for vascular features. Broad-spectrum SPF 30+ sunscreen is essential daily."
    ],
}

DEFAULT_DISEASE_INFO = [
    "This skin condition requires professional clinical evaluation for accurate diagnosis and appropriate management. Presentation can vary significantly between individuals.",
    "A board-certified dermatologist can perform dermoscopy, biopsies, or patch testing as needed and will recommend the most evidence-based treatment pathway for your specific case."
]


def _get_disease_info(disease_name: str):
    key = (disease_name or '').strip().lower()
    if key in DISEASE_INFO:
        return DISEASE_INFO[key]
    for k in DISEASE_INFO:
        if k in key or key in k:
            return DISEASE_INFO[k]
    return DEFAULT_DISEASE_INFO


def _severity_label(confidence: float) -> str:
    if confidence >= 80:
        return 'High'
    if confidence >= 50:
        return 'Moderate'
    return 'Low'


def _severity_color(label: str):
    """Returns (R, G, B) tuples for severity label."""
    return {
        'High': (0.87, 0.20, 0.20),
        'Moderate': (0.91, 0.54, 0.13),
        'Low': (0.13, 0.65, 0.40),
    }.get(label, (0.39, 0.39, 0.39))


@csrf_exempt
def generate_pdf_report(request):
    """
    Generate a complete diagnostic PDF report using ReportLab.
    Accepts POST with JSON: {
        username, disease, confidence, category,
        top_predictions: [{rank, disease, confidence, category}, ...],
        hospitals: [{name, specialty, location, contact}, ...]
    }
    Returns: application/pdf binary response.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Only POST allowed'}, status=405)

    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.units import mm
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
            HRFlowable, KeepTogether
        )
        from io import BytesIO
        import pytz
        from datetime import datetime
    except ImportError as ie:
        return JsonResponse({'success': False, 'error': f'Missing library: {ie}'}, status=500)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)

    # ── Extract request payload ───────────────────────────────────────────────
    username     = data.get('username', 'Patient')
    disease      = data.get('disease', 'Unknown')
    confidence   = float(data.get('confidence', 0))
    category     = data.get('category', 'Dermatological Condition')
    top_preds    = data.get('top_predictions', [])
    hospitals    = data.get('hospitals', [])

    severity    = _severity_label(confidence)
    sev_color   = _severity_color(severity)
    desc        = _get_disease_info(disease)

    ist = pytz.timezone('Asia/Kolkata')
    now_ist = datetime.now(ist)
    report_date = now_ist.strftime('%d %B %Y')
    report_time = now_ist.strftime('%I:%M %p IST')

    # ── Enrich username with full name from DB if available ────────────────
    full_name = username
    try:
        u = User.objects.get(username=username)
        prof = u.profile
        if prof.full_name:
            full_name = prof.full_name
    except Exception:
        pass

    # ── Colour palette ────────────────────────────────────────────────────────
    BRAND_BLUE   = colors.HexColor('#1e40af')
    LIGHT_BLUE   = colors.HexColor('#eff6ff')
    BRAND_GRAY   = colors.HexColor('#475569')
    BORDER_GRAY  = colors.HexColor('#e2e8f0')
    SEV_COLOR    = colors.Color(*sev_color)
    WHITE        = colors.white
    DARK         = colors.HexColor('#0f172a')

    # ── Build PDF in memory ────────────────────────────────────────────────────
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=18*mm, rightMargin=18*mm,
        topMargin=18*mm, bottomMargin=18*mm,
    )

    styles = getSampleStyleSheet()

    def style(name, **kw):
        base = styles[name]
        p = ParagraphStyle(name + '_custom', parent=base)
        for k, v in kw.items():
            setattr(p, k, v)
        return p

    title_style    = style('Title',  textColor=DARK, fontSize=20, spaceAfter=2)
    h2_style       = style('Heading2', textColor=BRAND_BLUE, fontSize=12, spaceBefore=8, spaceAfter=4)
    body_style     = style('Normal', textColor=BRAND_GRAY, fontSize=9.5, leading=14, spaceAfter=4)
    small_style    = style('Normal', textColor=BRAND_GRAY, fontSize=8, leading=11)
    center_style   = style('Normal', alignment=TA_CENTER, textColor=BRAND_GRAY, fontSize=8)
    bold_style     = style('Normal', textColor=DARK, fontSize=9.5, fontName='Helvetica-Bold')
    disclaimer_style = style('Normal', textColor=colors.HexColor('#991b1b'),
                             fontSize=8.5, leading=12, fontName='Helvetica-Bold')

    story = []

    # ── HEADER ──────────────────────────────────────────────────────────────
    header_data = [[
        Paragraph('<b>🧬 MediSkin AI</b>', style('Normal', fontSize=16, textColor=WHITE, fontName='Helvetica-Bold')),
        Paragraph(f'<font size=8>Diagnostic Report<br/>{report_date} · {report_time}</font>',
                  style('Normal', textColor=colors.HexColor('#bfdbfe'), alignment=TA_RIGHT, fontSize=8)),
    ]]
    header_table = Table(header_data, colWidths=[doc.width * 0.6, doc.width * 0.4])
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), BRAND_BLUE),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('LEFTPADDING', (0, 0), (0, -1), 14),
        ('RIGHTPADDING', (-1, 0), (-1, -1), 14),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 8))

    # ── PATIENT INFO ─────────────────────────────────────────────────────────
    info_data = [[
        Paragraph(f'<b>Patient:</b>  {full_name}', body_style),
        Paragraph(f'<b>Username:</b>  {username}', body_style),
        Paragraph(f'<b>Date:</b>  {report_date}', body_style),
    ]]
    info_table = Table(info_data, colWidths=[doc.width / 3] * 3)
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), LIGHT_BLUE),
        ('BOX', (0, 0), (-1, -1), 0.5, BORDER_GRAY),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 10))

    # ── PREDICTION SUMMARY CARDS ──────────────────────────────────────────────
    story.append(Paragraph('Prediction Summary', h2_style))
    story.append(HRFlowable(width='100%', thickness=0.5, color=BORDER_GRAY, spaceAfter=6))

    card_data = [[
        # Disease card
        Table(
            [[Paragraph('<font size=7 color="#0c4a6e">DETECTED CONDITION</font>', small_style)],
             [Paragraph(f'<b>{disease}</b>', style('Normal', fontSize=13, textColor=DARK, fontName='Helvetica-Bold'))],
             [Paragraph(category, style('Normal', fontSize=8, textColor=BRAND_BLUE))]],
            colWidths=[doc.width / 3 - 12]
        ),
        # Confidence card
        Table(
            [[Paragraph('<font size=7 color="#166534">CONFIDENCE SCORE</font>', small_style)],
             [Paragraph(f'<b>{confidence:.1f}%</b>', style('Normal', fontSize=13, textColor=DARK, fontName='Helvetica-Bold'))],
             [Paragraph('Model prediction certainty', small_style)]],
            colWidths=[doc.width / 3 - 12]
        ),
        # Severity card
        Table(
            [[Paragraph('<font size=7>SEVERITY LEVEL</font>', small_style)],
             [Paragraph(f'<b>{severity}</b>', style('Normal', fontSize=13, textColor=SEV_COLOR, fontName='Helvetica-Bold'))],
             [Paragraph('Based on confidence threshold', small_style)]],
            colWidths=[doc.width / 3 - 12]
        ),
    ]]
    card_table = Table(card_data, colWidths=[doc.width / 3] * 3, hAlign='LEFT')
    card_table.setStyle(TableStyle([
        ('BOX', (0, 0), (0, -1), 0.8, colors.HexColor('#0284c7')),
        ('BOX', (1, 0), (1, -1), 0.8, colors.HexColor('#16a34a')),
        ('BOX', (2, 0), (2, -1), 0.8, SEV_COLOR),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f9ff')),
        ('BACKGROUND', (1, 0), (1, -1), colors.HexColor('#f0fdf4')),
        ('BACKGROUND', (2, 0), (2, -1), colors.HexColor('#fefce8')),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LINEAFTER', (0, 0), (1, -1), 0.5, WHITE),
    ]))
    story.append(card_table)
    story.append(Spacer(1, 10))

    # ── TOP DIFFERENTIAL DIAGNOSES ─────────────────────────────────────────────
    if top_preds:
        story.append(Paragraph('Top Differential Diagnoses', h2_style))
        story.append(HRFlowable(width='100%', thickness=0.5, color=BORDER_GRAY, spaceAfter=6))

        diff_rows = [[
            Paragraph('<b>Rank</b>', bold_style),
            Paragraph('<b>Condition</b>', bold_style),
            Paragraph('<b>Category</b>', bold_style),
            Paragraph('<b>Confidence</b>', bold_style),
        ]]
        for pred in top_preds:
            diff_rows.append([
                Paragraph(str(pred.get('rank', '')), body_style),
                Paragraph(str(pred.get('disease', '')), body_style),
                Paragraph(str(pred.get('category', 'Dermatological')), body_style),
                Paragraph(f"{float(pred.get('confidence', 0)):.1f}%", body_style),
            ])

        diff_col_w = [doc.width * r for r in (0.08, 0.38, 0.30, 0.24)]
        diff_table = Table(diff_rows, colWidths=diff_col_w)
        diff_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), BRAND_BLUE),
            ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, LIGHT_BLUE]),
            ('GRID', (0, 0), (-1, -1), 0.4, BORDER_GRAY),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(diff_table)
        story.append(Spacer(1, 10))

    # ── MEDICAL INFORMATION ────────────────────────────────────────────────────
    story.append(Paragraph('Medical Information', h2_style))
    story.append(HRFlowable(width='100%', thickness=0.5, color=BORDER_GRAY, spaceAfter=6))
    story.append(Paragraph(desc[0], body_style))
    story.append(Spacer(1, 4))
    story.append(Paragraph(desc[1], body_style))
    story.append(Spacer(1, 6))

    # Disclaimer box
    disclaimer_data = [[
        Paragraph(
            '⚠ <b>Medical Disclaimer:</b> This AI-generated report is for informational '
            'purposes only and does not constitute a professional medical diagnosis. '
            'Always consult a board-certified dermatologist for clinical evaluation and treatment.',
            style('Normal', textColor=colors.HexColor('#7f1d1d'), fontSize=8.5,
                  leading=12, fontName='Helvetica'))
    ]]
    disc_table = Table(disclaimer_data, colWidths=[doc.width])
    disc_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#fef2f2')),
        ('BOX', (0, 0), (-1, -1), 0.8, colors.HexColor('#fca5a5')),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
    ]))
    story.append(disc_table)
    story.append(Spacer(1, 10))

    # ── RECOMMENDED HOSPITALS ──────────────────────────────────────────────────
    story.append(Paragraph('Recommended Dermatology Hospitals', h2_style))
    story.append(HRFlowable(width='100%', thickness=0.5, color=BORDER_GRAY, spaceAfter=6))

    if hospitals:
        for h in hospitals:
            hosp_rows = [
                [Paragraph(f"<b>{h.get('name', 'N/A')}</b>",
                           style('Normal', fontSize=10, textColor=DARK, fontName='Helvetica-Bold'))],
                [Paragraph(f"<font size=8 color='#2563eb'>🏥 {h.get('specialty', '')}</font>",
                           body_style)],
                [Paragraph(f"📍 {h.get('location', '')}", small_style)],
                [Paragraph(f"📞 {h.get('contact', '')}", small_style)],
            ]
            hosp_table = Table(hosp_rows, colWidths=[doc.width])
            hosp_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), WHITE),
                ('BOX', (0, 0), (-1, -1), 0.5, BORDER_GRAY),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ]))
            story.append(hosp_table)
            story.append(Spacer(1, 5))
    else:
        story.append(Paragraph('No hospital recommendations were selected for this report.', body_style))

    # ── FOOTER ─────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 12))
    story.append(HRFlowable(width='100%', thickness=0.5, color=BORDER_GRAY))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        f'MediSkin AI © 2026 · Confidential Medical Report · Generated {report_date} at {report_time} · For informational purposes only',
        center_style
    ))

    # ── Build & return PDF ─────────────────────────────────────────────────────
    doc.build(story)
    pdf_bytes = buf.getvalue()
    buf.close()

    filename = f"MediSkin_AI_Report_{now_ist.strftime('%Y%m%d_%H%M%S')}.pdf"
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    response['Content-Length'] = len(pdf_bytes)
    return response


# ─── Google Maps Proxy Views ──────────────────────────────────────────────────
# These keep the GOOGLE_MAPS_API_KEY server-side so it is never exposed in JS.

import urllib.request
import urllib.parse

# Keywords that indicate a non-dermatology place — we exclude these
_EXCLUDE_KEYWORDS = {
    'medplus', 'pharmacy', 'chemist', 'drugstore', 'medical store',
    'retail', 'supermarket', 'grocery', 'store', 'shop', 'mart',
    'restaurant', 'hotel', 'salon', 'beauty', 'spa', 'fitness',
    'gym', 'laboratory', 'lab', 'diagnostic centre', 'pathology',
    'dental', 'dentist', 'eye', 'optical', 'ortho'
}

# Words that indicate a place IS relevant
_DERMA_KEYWORDS = {
    'dermatolog', 'skin', 'cosmetol', 'tricholog', 'hair', 'laser skin',
    'venereol', 'aesthetic', 'plastic surgery', 'derm'
}


def _is_dermatology_place(place: dict) -> bool:
    """Return True if the place is a genuine dermatology clinic / hospital."""
    name_lower = (place.get('name') or '').lower()
    types = place.get('types', [])

    # Hard-exclude blacklisted keywords
    for kw in _EXCLUDE_KEYWORDS:
        if kw in name_lower:
            return False

    # Hard-exclude if it's clearly a pharmacy / store type
    bad_types = {'pharmacy', 'store', 'grocery_or_supermarket', 'food',
                 'restaurant', 'beauty_salon', 'hair_care', 'gym',
                 'lodging', 'bank', 'finance'}
    if bad_types.intersection(set(types)):
        return False

    # Allow if name contains a dermatology keyword
    for kw in _DERMA_KEYWORDS:
        if kw in name_lower:
            return True

    # Allow hospitals / clinics / health types even without explicit name match
    good_types = {'hospital', 'health', 'doctor', 'physiotherapist',
                  'medical_clinic_or_doctor'}
    if good_types.intersection(set(types)):
        return True

    return False


@csrf_exempt
def nearby_dermatology_clinics(request):
    """
    Proxy the Google Places Nearby Search API to find dermatology clinics.
    Query params:
        lat, lng   — centre coordinates  (preferred)
        city       — city name fallback
        state      — state name fallback
    Returns top 3 filtered results.
    """
    from django.conf import settings as django_settings

    api_key = django_settings.GOOGLE_MAPS_API_KEY
    if not api_key or api_key == '[YOUR_MAPS_API_KEY]':
        return JsonResponse({'success': False, 'error': 'Google Maps API key not configured.'}, status=503)

    lat = request.GET.get('lat', '').strip()
    lng = request.GET.get('lng', '').strip()
    city = request.GET.get('city', '').strip()
    state = request.GET.get('state', '').strip()

    # If no coords provided, geocode from city+state first
    if not (lat and lng):
        location_str = ', '.join(filter(None, [city, state, 'India']))
        geo_url = (
            'https://maps.googleapis.com/maps/api/geocode/json?'
            + urllib.parse.urlencode({'address': location_str, 'key': api_key})
        )
        try:
            with urllib.request.urlopen(geo_url, timeout=8) as r:
                geo_data = json.loads(r.read().decode())
            if geo_data.get('results'):
                loc = geo_data['results'][0]['geometry']['location']
                lat, lng = str(loc['lat']), str(loc['lng'])
            else:
                return JsonResponse({'success': False, 'error': 'Could not geocode location.'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': f'Geocoding failed: {e}'})

    all_results = []

    # Search with two keyword variations to maximise recall
    for keyword in ['dermatologist', 'skin clinic']:
        params = urllib.parse.urlencode({
            'location': f'{lat},{lng}',
            'radius': 10000,          # 10 km radius
            'type': 'hospital',
            'keyword': keyword,
            'key': api_key,
        })
        url = 'https://maps.googleapis.com/maps/api/place/nearbysearch/json?' + params
        try:
            with urllib.request.urlopen(url, timeout=8) as r:
                data = json.loads(r.read().decode())
            all_results.extend(data.get('results', []))
        except Exception as e:
            print(f'[Maps] Places API error ({keyword}): {e}')

    # De-duplicate by place_id
    seen = set()
    unique = []
    for p in all_results:
        pid = p.get('place_id')
        if pid and pid not in seen:
            seen.add(pid)
            unique.append(p)

    # Filter to dermatology-only places
    filtered = [p for p in unique if _is_dermatology_place(p)]

    # Sort by rating (desc), then user_ratings_total (desc)
    filtered.sort(key=lambda p: (-(p.get('rating') or 0), -(p.get('user_ratings_total') or 0)))

    # Take top 3
    top3 = filtered[:3]

    clinics = []
    for p in top3:
        loc = p.get('geometry', {}).get('location', {})
        clinics.append({
            'place_id': p.get('place_id', ''),
            'name': p.get('name', ''),
            'address': p.get('vicinity', ''),
            'rating': p.get('rating'),
            'total_ratings': p.get('user_ratings_total'),
            'open_now': p.get('opening_hours', {}).get('open_now'),
            'types': p.get('types', []),
            'lat': loc.get('lat'),
            'lng': loc.get('lng'),
            'photo_ref': (p.get('photos') or [{}])[0].get('photo_reference', ''),
        })

    return JsonResponse({'success': True, 'clinics': clinics, 'center': {'lat': lat, 'lng': lng}})


def geocode_location(request):
    """Proxy Geocoding API — converts city/state to lat/lng."""
    from django.conf import settings as django_settings

    api_key = django_settings.GOOGLE_MAPS_API_KEY
    if not api_key or api_key == '[YOUR_MAPS_API_KEY]':
        return JsonResponse({'success': False, 'error': 'Maps API key not configured.'}, status=503)

    address = request.GET.get('address', '').strip()
    if not address:
        return JsonResponse({'success': False, 'error': 'address param required.'}, status=400)

    url = ('https://maps.googleapis.com/maps/api/geocode/json?'
           + urllib.parse.urlencode({'address': address, 'key': api_key}))
    try:
        with urllib.request.urlopen(url, timeout=8) as r:
            data = json.loads(r.read().decode())
        return JsonResponse({'success': True, 'results': data.get('results', [])})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


def get_maps_key(request):
    """Safely expose only the Maps JS API key to the frontend (GET requests only)."""
    from django.conf import settings as django_settings
    key = django_settings.GOOGLE_MAPS_API_KEY
    if not key or key == '[YOUR_MAPS_API_KEY]':
        return JsonResponse({'key': '', 'configured': False})
    return JsonResponse({'key': key, 'configured': True})
