// Login Page JavaScript

document.addEventListener('DOMContentLoaded', function () {
    const form = document.getElementById('loginForm');
    const usernameInput = document.getElementById('username');
    const passwordInput = document.getElementById('password');
    const rememberMeCheckbox = document.getElementById('rememberMe');
    const agreeTermsCheckbox = document.getElementById('agreeTerms');
    const loginError = document.getElementById('loginError');
    const loginErrorText = document.getElementById('loginErrorText');

    // Check if already logged in
    const currentUser = JSON.parse(sessionStorage.getItem('currentUser'));
    if (currentUser && currentUser.isLoggedIn) {
        window.location.href = '/';
        return;
    }

    // Check for registration success message
    const registrationSuccess = sessionStorage.getItem('registrationSuccess');
    if (registrationSuccess) {
        const successDiv = document.createElement('div');
        successDiv.className = 'alert alert-success';
        successDiv.style.marginBottom = 'var(--spacing-md)';
        successDiv.innerHTML = `
            <svg class="alert-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
            </svg>
            <span>${registrationSuccess}</span>
        `;
        form.parentElement.insertBefore(successDiv, form);
        sessionStorage.removeItem('registrationSuccess');

        // Auto-hide after 5 seconds
        setTimeout(() => {
            successDiv.style.transition = 'opacity 0.5s';
            successDiv.style.opacity = '0';
            setTimeout(() => successDiv.remove(), 500);
        }, 5000);
    }

    // Validation functions
    function validateUsername() {
        const value = usernameInput.value.trim();
        const error = document.getElementById('usernameError');

        if (value.length === 0) {
            error.classList.add('active');
            return false;
        }
        error.classList.remove('active');
        return true;
    }

    function validatePassword() {
        const value = passwordInput.value;
        const error = document.getElementById('passwordError');

        if (value.length === 0) {
            error.classList.add('active');
            return false;
        }
        error.classList.remove('active');
        return true;
    }

    function validateTerms() {
        const error = document.getElementById('termsError');

        if (!agreeTermsCheckbox.checked) {
            error.classList.add('active');
            return false;
        }
        error.classList.remove('active');
        return true;
    }

    // Add blur event listeners
    usernameInput.addEventListener('blur', validateUsername);
    passwordInput.addEventListener('blur', validatePassword);

    // Form submission
    form.addEventListener('submit', async function (e) {
        e.preventDefault();

        // Validate all fields
        const isUsernameValid = validateUsername();
        const isPasswordValid = validatePassword();
        const isTermsValid = validateTerms();

        if (isUsernameValid && isPasswordValid && isTermsValid) {
            // Show loading state
            const btnText = form.querySelector('.btn-text');
            const btnLoader = form.querySelector('.btn-loader');
            btnText.classList.add('hidden');
            btnLoader.classList.remove('hidden');

            // Prepare login data
            const loginData = {
                username: usernameInput.value.trim(),
                password: passwordInput.value
            };

            try {
                // Send POST request to Django backend
                const apiBase = (window.MEDISKIN_API_BASE || '');
                const response = await fetch(apiBase + '/api/auth/login/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(loginData)
                });

                const data = await response.json();

                if (data.success) {
                    // Store user data in sessionStorage
                    const userData = {
                        ...data.user,
                        isLoggedIn: true
                    };
                    sessionStorage.setItem('currentUser', JSON.stringify(userData));

                    // Redirect to home
                    window.location.href = '/';
                } else {
                    // Show error
                    loginError.classList.remove('hidden');
                    loginErrorText.textContent = data.error || 'Invalid username or password';

                    // Hide loading state
                    btnText.classList.remove('hidden');
                    btnLoader.classList.add('hidden');
                }
            } catch (error) {
                console.error('Login error:', error);
                loginError.classList.remove('hidden');
                loginErrorText.textContent = 'An error occurred. Please try again.';

                // Hide loading state
                btnText.classList.remove('hidden');
                btnLoader.classList.add('hidden');
            }
        }
    });

    // Hide error on input
    usernameInput.addEventListener('input', () => {
        loginError.classList.add('hidden');
    });

    passwordInput.addEventListener('input', () => {
        loginError.classList.add('hidden');
    });
});
