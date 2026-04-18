// Reset Password — UI only (form submits natively to Django view)

document.addEventListener('DOMContentLoaded', function () {
    const form = document.getElementById('resetForm');
    const emailInput = document.getElementById('email');

    if (!form) return; // not shown on success state

    // ── Client-side email validation on blur ─────────────────────────────────
    if (emailInput) {
        emailInput.addEventListener('blur', validateEmail);
    }

    // ── Show loading spinner on submit (HTML5 validation passes first) ────────
    form.addEventListener('submit', function (e) {
        if (!validateEmail()) {
            e.preventDefault();
            return;
        }
        const btnText   = form.querySelector('.btn-text');
        const btnLoader = form.querySelector('.btn-loader');
        const submitBtn = form.querySelector('#resetSubmitBtn');
        if (btnText)   btnText.classList.add('hidden');
        if (btnLoader) btnLoader.classList.remove('hidden');
        if (submitBtn) submitBtn.disabled = true;
        // Form submits normally — Django view handles everything
    });

    function validateEmail() {
        if (!emailInput) return true;
        const val   = emailInput.value.trim();
        const error = document.getElementById('emailError');
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(val)) {
            if (error) error.classList.add('active');
            emailInput.style.borderColor = 'var(--color-error)';
            return false;
        }
        if (error) error.classList.remove('active');
        emailInput.style.borderColor = '';
        return true;
    }
});

