// Create Account Page JavaScript

document.addEventListener('DOMContentLoaded', function () {
    const form = document.getElementById('registerForm');
    const fullNameInput = document.getElementById('fullName');
    const usernameInput = document.getElementById('username');
    const emailInput = document.getElementById('email');
    const phoneInput = document.getElementById('phone');
    const passwordInput = document.getElementById('password');
    const confirmPasswordInput = document.getElementById('confirmPassword');
    const agreeTermsCheckbox = document.getElementById('agreeTerms');
    const successMessage = document.getElementById('successMessage');

    // Validation functions
    function validateFullName() {
        const value = fullNameInput.value.trim();
        const error = document.getElementById('fullNameError');

        if (value.length < 2) {
            error.classList.add('active');
            return false;
        }
        error.classList.remove('active');
        return true;
    }

    function validateUsername() {
        const value = usernameInput.value.trim();
        const error = document.getElementById('usernameError');

        if (value.length < 3 || value.length > 20) {
            error.classList.add('active');
            return false;
        }
        error.classList.remove('active');
        return true;
    }

    function validateEmail() {
        const value = emailInput.value.trim();
        const error = document.getElementById('emailError');
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

        if (!emailRegex.test(value)) {
            error.classList.add('active');
            return false;
        }
        error.classList.remove('active');
        return true;
    }

    function validatePhone() {
        const value = phoneInput.value.trim();
        const error = document.getElementById('phoneError');

        if (!value) {
            error.classList.remove('active');
            return true;
        }

        if (value.length < 10) {
            error.classList.add('active');
            return false;
        }
        error.classList.remove('active');
        return true;
    }

    function validatePassword() {
        const value = passwordInput.value;
        const error = document.getElementById('passwordError');

        if (value.length < 8) {
            error.classList.add('active');
            return false;
        }
        error.classList.remove('active');
        return true;
    }

    function validateConfirmPassword() {
        const password = passwordInput.value;
        const confirmPassword = confirmPasswordInput.value;
        const error = document.getElementById('confirmPasswordError');

        if (password !== confirmPassword) {
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

    // Add blur event listeners for real-time validation
    fullNameInput.addEventListener('blur', validateFullName);
    usernameInput.addEventListener('blur', validateUsername);
    emailInput.addEventListener('blur', validateEmail);
    phoneInput.addEventListener('blur', validatePhone);
    passwordInput.addEventListener('blur', validatePassword);
    confirmPasswordInput.addEventListener('blur', validateConfirmPassword);

    // Form submission
    form.addEventListener('submit', async function (e) {
        e.preventDefault();

        // Validate all fields
        const isFullNameValid = validateFullName();
        const isUsernameValid = validateUsername();
        const isEmailValid = validateEmail();
        const isPhoneValid = validatePhone();
        const isPasswordValid = validatePassword();
        const isConfirmPasswordValid = validateConfirmPassword();
        const isTermsValid = validateTerms();

        if (isFullNameValid && isUsernameValid && isEmailValid && isPhoneValid &&
            isPasswordValid && isConfirmPasswordValid && isTermsValid) {

            // Show loading state
            const btnText = form.querySelector('.btn-text');
            const btnLoader = form.querySelector('.btn-loader');
            btnText.classList.add('hidden');
            btnLoader.classList.remove('hidden');

            // Prepare data for backend
            const formData = {
                fullName: fullNameInput.value.trim(),
                username: usernameInput.value.trim(),
                email: emailInput.value.trim(),
                phone: phoneInput.value.trim(),
                password: passwordInput.value
            };

            try {
                // Send POST request to Django backend
                const apiBase = (window.MEDISKIN_API_BASE || '');
                const response = await fetch(apiBase + '/api/auth/register/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(formData)
                });

                const data = await response.json();

                if (data.success) {
                    // Show success message
                    if (successMessage) {
                        successMessage.classList.remove('hidden');
                    }

                    // Redirect to login page after 1.5 seconds (no auto-login)
                    setTimeout(() => {
                        // Store success message for login page
                        sessionStorage.setItem('registrationSuccess', 'Account created successfully! Please login with your credentials.');
                        window.location.href = '/login/';
                    }, 1500);
                } else {
                    // Show error
                    alert(data.error || 'Registration failed. Please try again.');

                    // Hide loading state
                    btnText.classList.remove('hidden');
                    btnLoader.classList.add('hidden');
                }
            } catch (error) {
                console.error('Registration error:', error);
                alert('An error occurred. Please try again.');

                // Hide loading state
                btnText.classList.remove('hidden');
                btnLoader.classList.add('hidden');
            }
        }
    });
});
