// Home Page JavaScript

document.addEventListener('DOMContentLoaded', function () {
    // Check if user is logged in
    const currentUser = JSON.parse(sessionStorage.getItem('currentUser'));

    if (!currentUser || !currentUser.isLoggedIn) {
        window.location.href = '/login/';
        return;
    }

    // Display user name
    const userNameElement = document.getElementById('userName');
    if (userNameElement && currentUser.fullName) {
        userNameElement.textContent = `Welcome, ${currentUser.fullName.split(' ')[0]}`;
    }

    // Start Diagnostics Button
    const startDiagnosticsBtn = document.getElementById('startDiagnosticsBtn');
    if (startDiagnosticsBtn) {
        startDiagnosticsBtn.addEventListener('click', () => {
            window.location.href = '/diagnostics/';
        });
    }

    // Logout Button
    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', () => {
            sessionStorage.removeItem('currentUser');
            window.location.href = '/login/';
        });
    }
});
