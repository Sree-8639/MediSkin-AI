// Profile Page JavaScript

document.addEventListener('DOMContentLoaded', function () {
    // Check if user is logged in
    const currentUser = JSON.parse(sessionStorage.getItem('currentUser'));

    if (!currentUser || !currentUser.isLoggedIn) {
        window.location.href = '/login/';
        return;
    }

    // Indian Location Data
    const indianStates = {
        "Andhra Pradesh": {
            districts: {
                "Visakhapatnam": ["Visakhapatnam", "Anakapalli", "Bheemunipatnam"],
                "Vijayawada": ["Vijayawada", "Gannavaram", "Jaggayyapeta"],
                "Guntur": ["Guntur", "Tenali", "Mangalagiri"]
            }
        },
        "Telangana": {
            districts: {
                "Hyderabad": ["Hyderabad", "Secunderabad", "Kukatpally"],
                "Warangal": ["Warangal", "Hanamkonda", "Jangaon"],
                "Nizamabad": ["Nizamabad", "Armoor", "Bodhan"]
            }
        },
        "Karnataka": {
            districts: {
                "Bangalore Urban": ["Bangalore", "Yelahanka", "Whitefield"],
                "Mysore": ["Mysore", "Nanjangud", "K.R. Nagar"],
                "Mangalore": ["Mangalore", "Udupi", "Manipal"]
            }
        },
        "Tamil Nadu": {
            districts: {
                "Chennai": ["Chennai", "Tambaram", "Avadi"],
                "Coimbatore": ["Coimbatore", "Pollachi", "Mettupalayam"],
                "Madurai": ["Madurai", "Melur", "Usilampatti"]
            }
        },
        "Maharashtra": {
            districts: {
                "Mumbai": ["Mumbai", "Navi Mumbai", "Thane"],
                "Pune": ["Pune", "Pimpri-Chinchwad", "Baramati"],
                "Nagpur": ["Nagpur", "Kamptee", "Ramtek"]
            }
        },
        "Kerala": {
            districts: {
                "Thiruvananthapuram": ["Thiruvananthapuram", "Neyyattinkara", "Attingal"],
                "Kochi": ["Kochi", "Ernakulam", "Thrippunithura"],
                "Kozhikode": ["Kozhikode", "Vadakara", "Koyilandy"]
            }
        },
        "West Bengal": {
            districts: {
                "Kolkata": ["Kolkata", "Howrah", "Salt Lake"],
                "Darjeeling": ["Darjeeling", "Siliguri", "Kalimpong"],
                "Durgapur": ["Durgapur", "Asansol", "Raniganj"]
            }
        },
        "Gujarat": {
            districts: {
                "Ahmedabad": ["Ahmedabad", "Gandhinagar", "Sanand"],
                "Surat": ["Surat", "Navsari", "Valsad"],
                "Vadodara": ["Vadodara", "Anand", "Bharuch"]
            }
        },
        "Rajasthan": {
            districts: {
                "Jaipur": ["Jaipur", "Amber", "Sanganer"],
                "Jodhpur": ["Jodhpur", "Pali", "Sojat"],
                "Udaipur": ["Udaipur", "Chittorgarh", "Rajsamand"]
            }
        },
        "Punjab": {
            districts: {
                "Ludhiana": ["Ludhiana", "Khanna", "Samrala"],
                "Amritsar": ["Amritsar", "Tarn Taran", "Ajnala"],
                "Jalandhar": ["Jalandhar", "Phagwara", "Nakodar"]
            }
        }
    };

    // Elements
    const profileInitials = document.getElementById('profileInitials');
    const firstNameInput = document.getElementById('firstName');
    const lastNameInput = document.getElementById('lastName');
    const usernameInput = document.getElementById('username');
    const emailInput = document.getElementById('email');
    const phoneInput = document.getElementById('phone');
    const passwordInput = document.getElementById('password');
    const countrySelect = document.getElementById('country');
    const stateSelect = document.getElementById('state');
    const districtSelect = document.getElementById('district');
    const citySelect = document.getElementById('city');

    // Profile Picture elements (declared here so loadProfileFromBackend can use them)
    const profilePictureInput = document.getElementById('profilePictureInput');
    const profilePicture = document.getElementById('profilePicture');

    // Load user data (from sessionStorage + supplement from backend)
    function loadUserData() {
        firstNameInput.value = currentUser.firstName || '';
        lastNameInput.value = currentUser.lastName || '';
        usernameInput.value = currentUser.username || '';
        emailInput.value = currentUser.email || '';
        phoneInput.value = currentUser.phone || '';

        // Set profile initials
        const initials = getInitials(currentUser.firstName, currentUser.lastName);
        profileInitials.textContent = initials;

        // Immediately show profile picture from sessionStorage (cached at login)
        if (currentUser.profilePictureUrl) {
            const overlay = profilePicture.querySelector('.profile-picture-overlay');
            const initialsEl = profilePicture.querySelector('.profile-initials');
            const existing = profilePicture.querySelector('img.pp-img');
            if (existing) existing.remove();
            if (initialsEl) initialsEl.style.display = 'none';
            const img = document.createElement('img');
            img.src = currentUser.profilePictureUrl;
            img.className = 'pp-img';
            img.style.cssText = 'width:100%;height:100%;object-fit:cover;border-radius:50%;position:absolute;inset:0;';
            profilePicture.insertBefore(img, overlay);
        }

        // Immediately populate location from sessionStorage (cached at login)
        if (currentUser.country) {
            countrySelect.value = currentUser.country;
            if (currentUser.country === 'India' && currentUser.state) {
                populateStates();
                stateSelect.value = currentUser.state;
                if (currentUser.district) {
                    populateDistricts(currentUser.state);
                    districtSelect.value = currentUser.district;
                    if (currentUser.city) {
                        populateCities(currentUser.state, currentUser.district);
                        citySelect.value = currentUser.city;
                    }
                }
            }
        }

        // Also refresh from backend (syncs any changes made on another device/session)
        loadProfileFromBackend();
    }

    async function loadProfileFromBackend() {
        if (!currentUser.username) return;
        try {
            const apiBase = (window.MEDISKIN_API_BASE || '');
        const resp = await fetch(apiBase + `/api/profile/data/?username=${encodeURIComponent(currentUser.username)}`, {
                credentials: 'include'
            });
            const data = await resp.json();
            if (data.success && data.profile) {
                const p = data.profile;
                // Store in session (including profile picture URL for instant display)
                currentUser.country = p.country || currentUser.country || '';
                currentUser.state = p.state || currentUser.state || '';
                currentUser.district = p.district || currentUser.district || '';
                currentUser.city = p.city || currentUser.city || '';
                if (p.profile_picture_url) {
                    currentUser.profilePictureUrl = p.profile_picture_url;
                }
                sessionStorage.setItem('currentUser', JSON.stringify(currentUser));

                // Populate location fields
                countrySelect.value = currentUser.country;
                if (currentUser.country === 'India') {
                    populateStates();
                    stateSelect.value = currentUser.state;
                    if (currentUser.state) {
                        populateDistricts(currentUser.state);
                        districtSelect.value = currentUser.district;
                        if (currentUser.district) {
                            populateCities(currentUser.state, currentUser.district);
                            citySelect.value = currentUser.city;
                        }
                    }
                }

                // Load profile picture
                if (p.profile_picture_url) {
                    const overlay = profilePicture.querySelector('.profile-picture-overlay');
                    const initials = profilePicture.querySelector('.profile-initials');
                    const existing = profilePicture.querySelector('img.pp-img');
                    if (existing) existing.remove();
                    if (initials) initials.style.display = 'none';
                    const img = document.createElement('img');
                    img.src = p.profile_picture_url;
                    img.className = 'pp-img';
                    img.style.cssText = 'width:100%;height:100%;object-fit:cover;border-radius:50%;position:absolute;inset:0;';
                    profilePicture.insertBefore(img, overlay);
                }
            }
        } catch (err) {
            console.warn('Could not load profile from backend:', err);
        }
    }

    function getInitials(firstName, lastName) {
        if (!firstName && !lastName) return 'U';
        const first = (firstName || '')[0] || '';
        const last = (lastName || '')[0] || '';
        return (first + last).toUpperCase() || 'U';
    }

    // Populate States based on Country
    function populateStates() {
        stateSelect.innerHTML = '<option value="">Select State</option>';
        districtSelect.innerHTML = '<option value="">Select District</option>';
        citySelect.innerHTML = '<option value="">Select City</option>';

        if (countrySelect.value === 'India') {
            Object.keys(indianStates).forEach(state => {
                const option = document.createElement('option');
                option.value = state;
                option.textContent = state;
                stateSelect.appendChild(option);
            });
        }
    }

    // Populate Districts based on State
    function populateDistricts(state) {
        districtSelect.innerHTML = '<option value="">Select District</option>';
        citySelect.innerHTML = '<option value="">Select City</option>';

        if (indianStates[state]) {
            Object.keys(indianStates[state].districts).forEach(district => {
                const option = document.createElement('option');
                option.value = district;
                option.textContent = district;
                districtSelect.appendChild(option);
            });
        }
    }

    // Populate Cities based on State and District
    function populateCities(state, district) {
        citySelect.innerHTML = '<option value="">Select City</option>';

        if (indianStates[state] && indianStates[state].districts[district]) {
            indianStates[state].districts[district].forEach(city => {
                const option = document.createElement('option');
                option.value = city;
                option.textContent = city;
                citySelect.appendChild(option);
            });
        }
    }

    // Country Change Event
    countrySelect.addEventListener('change', function () {
        if (this.value === 'India') {
            populateStates();
        } else {
            stateSelect.innerHTML = '<option value="">Select State</option>';
            districtSelect.innerHTML = '<option value="">Select District</option>';
            citySelect.innerHTML = '<option value="">Select City</option>';
        }
    });

    // State Change Event
    stateSelect.addEventListener('change', function () {
        if (this.value) {
            populateDistricts(this.value);
        } else {
            districtSelect.innerHTML = '<option value="">Select District</option>';
            citySelect.innerHTML = '<option value="">Select City</option>';
        }
    });

    // District Change Event
    districtSelect.addEventListener('change', function () {
        const selectedState = stateSelect.value;
        if (this.value && selectedState) {
            populateCities(selectedState, this.value);
        } else {
            citySelect.innerHTML = '<option value="">Select City</option>';
        }
    });

    loadUserData();

    // Profile Picture Upload – click the circle to pick a file
    profilePicture.addEventListener('click', () => {
        profilePictureInput.click();
    });

    profilePictureInput.addEventListener('change', async function (e) {
        const file = e.target.files[0];
        if (!file) return;

        // Show a local preview immediately
        const reader = new FileReader();
        reader.onload = function (event) {
            const overlay = profilePicture.querySelector('.profile-picture-overlay');
            const initials = profilePicture.querySelector('.profile-initials');
            const existing = profilePicture.querySelector('img.pp-img');
            if (existing) existing.remove();
            if (initials) initials.style.display = 'none';
            const img = document.createElement('img');
            img.src = event.target.result;
            img.className = 'pp-img';
            img.style.cssText = 'width:100%;height:100%;object-fit:cover;border-radius:50%;position:absolute;inset:0;';
            profilePicture.insertBefore(img, overlay);
        };
        reader.readAsDataURL(file);

        // Upload to backend
        try {
            const formData = new FormData();
            formData.append('username', currentUser.username);
            formData.append('profile_picture', file);
            const apiBase = (window.MEDISKIN_API_BASE || '');
            const resp = await fetch(apiBase + '/api/profile/picture/', {
                method: 'POST',
                body: formData,
                credentials: 'include'
            });
            const data = await resp.json();
            if (data.success) {
                // Cache the URL in sessionStorage so it persists within this session
                if (data.picture_url) {
                    currentUser.profilePictureUrl = data.picture_url;
                    sessionStorage.setItem('currentUser', JSON.stringify(currentUser));
                }
                showSuccessMessage('Profile picture updated!');
            } else {
                console.error('Picture upload failed:', data.error);
                showSuccessMessage('Picture saved locally (upload failed)');
            }
        } catch (err) {
            console.error('Picture upload error:', err);
        }
    });

    // Edit Personal Information
    const editPersonalBtn = document.getElementById('editPersonalBtn');
    const personalInfoForm = document.getElementById('personalInfoForm');
    const personalActions = document.getElementById('personalActions');
    const cancelPersonalBtn = document.getElementById('cancelPersonalBtn');

    editPersonalBtn.addEventListener('click', () => {
        firstNameInput.disabled = false;
        lastNameInput.disabled = false;
        emailInput.disabled = false;
        phoneInput.disabled = false;
        personalActions.classList.remove('hidden');
        editPersonalBtn.classList.add('hidden');
    });

    cancelPersonalBtn.addEventListener('click', () => {
        loadUserData();
        firstNameInput.disabled = true;
        lastNameInput.disabled = true;
        emailInput.disabled = true;
        phoneInput.disabled = true;
        personalActions.classList.add('hidden');
        editPersonalBtn.classList.remove('hidden');
    });

    personalInfoForm.addEventListener('submit', function (e) {
        e.preventDefault();

        currentUser.firstName = firstNameInput.value.trim();
        currentUser.lastName = lastNameInput.value.trim();
        currentUser.email = emailInput.value.trim();
        currentUser.phone = phoneInput.value.trim();

        sessionStorage.setItem('currentUser', JSON.stringify(currentUser));

        firstNameInput.disabled = true;
        lastNameInput.disabled = true;
        emailInput.disabled = true;
        phoneInput.disabled = true;
        personalActions.classList.add('hidden');
        editPersonalBtn.classList.remove('hidden');

        // Update initials
        profileInitials.textContent = getInitials(currentUser.firstName, currentUser.lastName);

        showSuccessMessage('Personal information updated!');
    });

    // Edit Location
    const editLocationBtn = document.getElementById('editLocationBtn');
    const locationForm = document.getElementById('locationForm');
    const locationActions = document.getElementById('locationActions');
    const cancelLocationBtn = document.getElementById('cancelLocationBtn');

    editLocationBtn.addEventListener('click', () => {
        countrySelect.disabled = false;
        stateSelect.disabled = false;
        districtSelect.disabled = false;
        citySelect.disabled = false;
        locationActions.classList.remove('hidden');
        editLocationBtn.classList.add('hidden');
    });

    cancelLocationBtn.addEventListener('click', () => {
        loadUserData();
        countrySelect.disabled = true;
        stateSelect.disabled = true;
        districtSelect.disabled = true;
        citySelect.disabled = true;
        locationActions.classList.add('hidden');
        editLocationBtn.classList.remove('hidden');
    });

    locationForm.addEventListener('submit', async function (e) {
        e.preventDefault();

        currentUser.country = countrySelect.value;
        currentUser.state = stateSelect.value;
        currentUser.district = districtSelect.value;
        currentUser.city = citySelect.value;
        currentUser.profileComplete = true;

        sessionStorage.setItem('currentUser', JSON.stringify(currentUser));

        countrySelect.disabled = true;
        stateSelect.disabled = true;
        districtSelect.disabled = true;
        citySelect.disabled = true;
        locationActions.classList.add('hidden');
        editLocationBtn.classList.remove('hidden');

        // Persist location to backend
        try {
            const apiBase = (window.MEDISKIN_API_BASE || '');
            const resp = await fetch(apiBase + '/api/profile/location/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({
                    username: currentUser.username,
                    country: currentUser.country,
                    state: currentUser.state,
                    district: currentUser.district,
                    city: currentUser.city
                })
            });
            const data = await resp.json();
            if (data.success) {
                showSuccessMessage('Location details saved!');
            } else {
                showSuccessMessage('Location saved locally (sync failed)');
            }
        } catch (err) {
            console.error('Location save error:', err);
            showSuccessMessage('Location details updated!');
        }
    });

    // Change Password
    const passwordForm = document.getElementById('passwordForm');
    const passwordSuccess = document.getElementById('passwordSuccess');

    passwordForm.addEventListener('submit', async function (e) {
        e.preventDefault();

        const currentPassword = document.getElementById('currentPassword').value;
        const newPassword = document.getElementById('newPassword').value;
        const confirmNewPassword = document.getElementById('confirmNewPassword').value;

        if (newPassword !== confirmNewPassword) {
            alert('New passwords do not match!');
            return;
        }

        if (newPassword.length < 8) {
            alert('Password must be at least 8 characters!');
            return;
        }

        try {
            // Call backend API to change password
            const apiBase = (window.MEDISKIN_API_BASE || '');
            const response = await fetch(apiBase + '/api/auth/change-password/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    username: currentUser.username,
                    currentPassword: currentPassword,
                    newPassword: newPassword
                })
            });

            const data = await response.json();

            if (data.success) {
                passwordSuccess.classList.remove('hidden');
                passwordForm.reset();

                setTimeout(() => {
                    passwordSuccess.classList.add('hidden');
                }, 3000);
            } else {
                alert(data.error || 'Password change failed. Please try again.');
            }
        } catch (error) {
            console.error('Password change error:', error);
            alert('An error occurred. Please try again.');
        }
    });

    // Logout
    const logoutBtn = document.getElementById('logoutBtn');
    logoutBtn.addEventListener('click', () => {
        sessionStorage.removeItem('currentUser');
        window.location.href = '/login/';
    });

    // Success Message Helper
    function showSuccessMessage(message) {
        const successAlert = document.getElementById('profileSuccess');
        const successText = document.getElementById('successText');

        successText.textContent = message;
        successAlert.classList.remove('hidden');

        setTimeout(() => {
            successAlert.classList.add('hidden');
        }, 3000);
    }

    // Load Prediction History
    async function loadPredictionHistory() {
        const historyContainer = document.getElementById('historyContainer');

        try {
            const apiBase = (window.MEDISKIN_API_BASE || '');
            const response = await fetch(apiBase + `/api/history/?username=${encodeURIComponent(currentUser.username)}`, {
                credentials: 'include'
            });
            const data = await response.json();

            if (data.success && data.history && data.history.length > 0) {
                const historyHTML = `
                    <div class="history-grid">
                        ${data.history.map(item => `
                            <div class="history-item">
                                <div class="history-disease">${item.disease}</div>
                                <div class="history-confidence">Confidence: ${item.confidence}%</div>
                                <div class="history-meta">
                                    <span class="history-date">📅 ${item.date}</span>
                                    <span class="history-time">🕐 ${item.time}</span>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                `;
                historyContainer.innerHTML = historyHTML;
            } else {
                historyContainer.innerHTML = `
                    <div class="history-empty">
                        <svg class="history-empty-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                        </svg>
                        <p>No prediction history yet. Start by analyzing skin images in the Diagnostics page!</p>
                    </div>
                `;
            }
        } catch (error) {
            console.error('Error loading prediction history:', error);
            historyContainer.innerHTML = `
                <div class="history-empty">
                    <p>Failed to load prediction history. Please try again later.</p>
                </div>
            `;
        }
    }

    // Load history on page load
    loadPredictionHistory();

    // Reload history when page becomes visible (user returns from diagnostics)
    document.addEventListener('visibilitychange', function () {
        if (!document.hidden) {
            console.log('Page visible - reloading prediction history');
            loadPredictionHistory();
        }
    });

    // Also reload when window gains focus
    window.addEventListener('focus', function () {
        console.log('Window focused - reloading prediction history');
        loadPredictionHistory();
    });
});
