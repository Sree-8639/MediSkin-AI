// Diagnostics Page Functionality

document.addEventListener('DOMContentLoaded', function () {
    // Check authentication
    const currentUser = JSON.parse(sessionStorage.getItem('currentUser'));
    if (!currentUser || !currentUser.isLoggedIn) {
        window.location.href = '/login/';
        return;
    }

    // Elements
    const uploadArea = document.getElementById('uploadArea');
    const fileInput = document.getElementById('fileInput');
    const selectImageBtn = document.getElementById('selectImageBtn');
    const analyzeBtn = document.getElementById('analyzeBtn');
    const imagePreview = document.getElementById('imagePreview');
    const uploadPlaceholder = document.getElementById('uploadPlaceholder');
    const uploadError = document.getElementById('uploadError');
    const uploadErrorText = document.getElementById('uploadErrorText');
    const resultsPlaceholder = document.getElementById('resultsPlaceholder');
    const resultsContent = document.getElementById('resultsContent');
    const stateSelect = document.getElementById('stateSelect');
    const districtSelect = document.getElementById('districtSelect');
    const viewRecommendationsBtn = document.getElementById('viewRecommendationsBtn');
    const hospitalsGrid = document.getElementById('hospitalsGrid');
    const feedbackForm = document.getElementById('feedbackForm');
    const feedbackButtons = document.querySelectorAll('.feedback-btn');
    const feedbackAccuracy = document.getElementById('feedbackAccuracy');
    const logoutBtn = document.getElementById('logoutBtn');
    const previewReportBtn = document.getElementById('previewReportBtn');
    const downloadReportBtn = document.getElementById('downloadReportBtn');

    let selectedFile = null;
    let lastPrediction = null;
    let lastHospitals = [];

    const diseaseInfoMap = {
        "acne": [
            "Acne is a common skin condition caused by blocked pores and inflammation.",
            "Keeping skin clean and avoiding pore-clogging products can help reduce flare-ups."
        ],
        "eczema": [
            "Eczema causes dry, itchy, and inflamed skin due to a weakened skin barrier.",
            "Moisturizing regularly and avoiding triggers can help manage symptoms."
        ],
        "psoriasis": [
            "Psoriasis is an autoimmune condition that speeds up skin cell growth.",
            "Treatment focuses on reducing inflammation and scaling."
        ],
        "rosacea": [
            "Rosacea leads to facial redness, flushing, and visible blood vessels.",
            "Sun protection and gentle skincare help control flare-ups."
        ],
        "melanoma": [
            "Melanoma is a serious form of skin cancer that can spread quickly.",
            "Early detection and medical evaluation are essential."
        ]
    };

    // Logout
    if (logoutBtn) {
        logoutBtn.addEventListener('click', () => {
            sessionStorage.removeItem('currentUser');
            window.location.href = '/login/';
        });
    }

    // Report actions
    if (previewReportBtn) {
        previewReportBtn.addEventListener('click', () => {
            if (!lastPrediction) {
                alert('Please analyze an image before previewing the report.');
                return;
            }
            const reportHtml = buildReportHtml();
            const reportWindow = window.open('', '_blank');
            if (reportWindow) {
                reportWindow.document.write(reportHtml);
                reportWindow.document.close();
            }
        });
    }

    if (downloadReportBtn) {
        downloadReportBtn.addEventListener('click', () => {
            if (!lastPrediction) {
                alert('Please analyze an image before downloading the report.');
                return;
            }
            downloadReportAsPDF();
        });
    }

    function downloadReportAsPDF() {
        if (!lastPrediction) {
            alert('Please analyze an image before downloading the report.');
            return;
        }

        // Build the same report shown in preview
        const reportHtml = buildReportHtml();

        // Open the report in a new window (identical to preview)
        const reportWindow = window.open('', '_blank');
        if (!reportWindow) {
            alert('Pop-up blocked! Please allow pop-ups for this site and try again.');
            return;
        }

        // Add print-specific styles and auto-trigger print dialog
        // The @media print rules ensure the PDF output looks exactly
        // like what the user sees on screen.
        const printReportHtml = reportHtml.replace('</style>', `
            @media print {
                body { margin: 0; padding: 0; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
                .report { box-shadow: none; border-radius: 0; max-width: 100%; }
                .report-header { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
                .diff-table th { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
                .summary-card { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
                .disclaimer { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
            }
        </style>`);

        reportWindow.document.write(printReportHtml);
        reportWindow.document.close();

        // Wait for page and images to fully load, then trigger print
        reportWindow.onload = function () {
            setTimeout(function () {
                reportWindow.print();
            }, 500);
        };
        // Fallback if onload doesn't fire (some browsers)
        setTimeout(function () {
            try { reportWindow.print(); } catch (e) { }
        }, 2000);
    }


    // Image Upload Handlers
    if (selectImageBtn) selectImageBtn.addEventListener('click', () => fileInput.click());
    if (fileInput) fileInput.addEventListener('change', handleFileSelect);

    if (uploadArea) {
        uploadArea.addEventListener('click', (e) => {
            if (e.target === uploadArea || e.target === uploadPlaceholder) {
                fileInput.click();
            }
        });

        // Drag and drop
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });

        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('dragover');
        });

        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                handleFile(files[0]);
            }
        });
    }

    function handleFileSelect(e) {
        const file = e.target.files[0];
        if (file) {
            handleFile(file);
        }
    }

    function handleFile(file) {
        // Validate file type
        const validTypes = ['image/jpeg', 'image/png'];
        if (!validTypes.includes(file.type)) {
            showUploadError('Please upload a JPG or PNG image');
            return;
        }

        // Validate file size (5MB max)
        const maxSize = 5 * 1024 * 1024;
        if (file.size > maxSize) {
            showUploadError('File size must be less than 5MB');
            return;
        }

        selectedFile = file;
        hideUploadError();

        // Show preview
        const reader = new FileReader();
        reader.onload = (e) => {
            imagePreview.src = e.target.result;
            uploadPlaceholder.classList.add('hidden');
            imagePreview.classList.remove('hidden');
            selectImageBtn.classList.add('hidden');
            analyzeBtn.classList.remove('hidden');
        };
        reader.readAsDataURL(file);
    }

    function showUploadError(message) {
        uploadErrorText.textContent = message;
        uploadError.classList.remove('hidden');
    }

    function hideUploadError() {
        uploadError.classList.add('hidden');
    }

    // Analyze Image
    if (analyzeBtn) {
        analyzeBtn.addEventListener('click', async function () {
            if (!selectedFile) return;

            showLoading(this);
            hideUploadError();

            try {
                // Create FormData for file upload
                const formData = new FormData();
                formData.append('image', selectedFile);
                // Include username so backend can save prediction without session auth
                if (currentUser && currentUser.username) {
                    formData.append('username', currentUser.username);
                }

                // Call ML prediction API
                const apiBase = (window.MEDISKIN_API_BASE || '');
                const response = await fetch(apiBase + '/api/predict/', {
                    method: 'POST',
                    body: formData,
                    credentials: 'include'  // Include session cookies for authentication
                });

                const data = await response.json();

                if (data.success && data.prediction) {
                    // Display real ML prediction
                    displayResults({
                        name: data.prediction.disease,
                        confidence: data.prediction.confidence,
                        category: data.prediction.category || 'Dermatological Condition',
                        topPredictions: data.prediction.top_predictions
                    });
                } else {
                    showUploadError(data.error || 'Prediction failed. Please try again.');
                }

            } catch (error) {
                console.error('Analysis error:', error);
                showUploadError('Analysis failed. Please check your connection and try again.');
            } finally {
                hideLoading(this);
            }
        });
    }

    function displayResults(prediction) {
        lastPrediction = prediction;
        document.getElementById('diseaseName').textContent = prediction.name;
        document.getElementById('confidenceText').textContent = prediction.confidence + '%';

        const confidenceFill = document.getElementById('confidenceFill');
        confidenceFill.style.width = prediction.confidence + '%';

        // Render disease category badge
        const category = prediction.category || 'Dermatological Condition';
        const categoryColors = {
            'Malignant': '#ef4444',
            'Pre-Malignant': '#f97316',
            'Inflammatory': '#eab308',
            'Infectious': '#8b5cf6',
            'Acne/Comedonal': '#ec4899',
            'Benign': '#22c55e',
            'Pigmentary': '#06b6d4',
            'Dermatological Condition': '#64748b'
        };
        const color = categoryColors[category] || '#64748b';

        let categoryEl = document.getElementById('diseaseCategoryBadge');
        if (!categoryEl) {
            categoryEl = document.createElement('div');
            categoryEl.id = 'diseaseCategoryBadge';
            categoryEl.style.cssText = [
                'display:inline-flex',
                'align-items:center',
                'gap:6px',
                'margin-top:8px',
                'padding:4px 12px',
                'border-radius:999px',
                'font-size:0.8rem',
                'font-weight:600',
                'border:1.5px solid',
                'letter-spacing:0.3px'
            ].join(';');
            const nameEl = document.getElementById('diseaseName');
            if (nameEl && nameEl.parentNode) {
                nameEl.parentNode.insertBefore(categoryEl, nameEl.nextSibling);
            }
        }
        categoryEl.textContent = 'â— ' + category;
        categoryEl.style.color = color;
        categoryEl.style.borderColor = color;
        categoryEl.style.background = color + '18';

        // Render Top Differential Diagnoses table
        const topContainer = document.getElementById('topPredictionsContainer');
        const topBody = document.getElementById('topPredictionsBody');
        if (prediction.topPredictions && prediction.topPredictions.length > 0 && topContainer && topBody) {
            topBody.innerHTML = prediction.topPredictions.map(p => {
                const catColor = categoryColors[p.category] || '#64748b';
                return `<tr>
                    <td style="text-align:center;font-weight:bold;color:#1e40af">${p.rank}</td>
                    <td>${p.disease}</td>
                    <td><span style="background:${catColor}18;color:${catColor};padding:2px 8px;border-radius:999px;font-size:0.75rem;font-weight:600;border:1px solid ${catColor}">${p.category || 'Dermatological'}</span></td>
                    <td style="font-weight:700;color:#ffffff;font-size:0.9rem">${p.confidence.toFixed ? p.confidence.toFixed(1) : p.confidence}%</td>
                </tr>`;
            }).join('');
            topContainer.style.display = 'block';
        }

        resultsPlaceholder.classList.add('hidden');
        resultsContent.classList.remove('hidden');

        // Scroll to results
        resultsContent.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    function getSeverityLevel(confidence) {
        if (confidence >= 80) return 'High';
        if (confidence >= 50) return 'Medium';
        return 'Low';
    }

    function getDiseaseDescriptions(diseaseName) {
        const key = (diseaseName || '').toLowerCase();
        if (diseaseInfoMap[key]) {
            return diseaseInfoMap[key];
        }

        return [
            "This condition affects the skin and may require professional evaluation.",
            "Follow up with a dermatologist for accurate diagnosis and treatment."
        ];
    }

    function buildReportHtml() {
        const diseaseName = lastPrediction ? lastPrediction.name : '-';
        const confidence = lastPrediction ? lastPrediction.confidence : '-';
        const severity = lastPrediction ? getSeverityLevel(lastPrediction.confidence) : '-';
        const descriptions = getDiseaseDescriptions(diseaseName);
        const imageSrc = imagePreview && imagePreview.src ? imagePreview.src : '';
        const category = lastPrediction ? (lastPrediction.category || 'Dermatological Condition') : '-';

        const topPredRows = (lastPrediction && lastPrediction.topPredictions && lastPrediction.topPredictions.length)
            ? lastPrediction.topPredictions.map(p => `
                <tr style="border-bottom:1px solid #e2e8f0;">
                    <td style="padding:6px 12px;text-align:center;font-weight:bold;color:#1e40af;">${p.rank}</td>
                    <td style="padding:6px 12px;">${p.disease}</td>
                    <td style="padding:6px 12px;font-size:12px;">${p.category || 'Dermatological'}</td>
                    <td style="padding:6px 12px;font-weight:600;">${typeof p.confidence === 'number' ? p.confidence.toFixed(1) : p.confidence}%</td>
                </tr>`).join('')
            : '<tr><td colspan="4" style="padding:8px 12px;color:#64748b;">No data</td></tr>';

        const hospitalSection = lastHospitals.length
            ? lastHospitals.map(hospital => {
                const mapUrl = `https://www.google.com/maps/search/${encodeURIComponent(hospital.name + ' ' + hospital.location)}`;
                return `
                    <div class="hospital-item">
                        <h3>${hospital.name}</h3>
                        <p><strong>Specialty:</strong> ${hospital.specialty}</p>
                        <p><strong>Location:</strong> ${hospital.location}</p>
                        <p><strong>Contact:</strong> ${hospital.contact}</p>
                        <p><a href="${mapUrl}" target="_blank" rel="noopener">Location Link</a></p>
                    </div>
                `;
            }).join('')
            : '<p>No hospital recommendations selected.</p>';

        return `
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>MediSkin AI — Diagnostic Report</title>
    <style>
        body { font-family: Arial, sans-serif; background: #f8fafc; color: #0f172a; margin: 0; padding: 24px; }
        .report { max-width: 900px; margin: 0 auto; background: #ffffff; padding: 0; border-radius: 12px; box-shadow: 0 10px 30px rgba(15, 23, 42, 0.1); overflow:hidden; }
        .report-header { background: #1e40af; color: white; padding: 20px 28px; display:flex; justify-content:space-between; align-items:center; }
        .report-header h1 { margin:0; font-size:22px; }
        .report-header p { margin:0; font-size:12px; color:#bfdbfe; }
        .report-body { padding: 24px 28px; }
        .section { margin-top: 24px; }
        h2 { font-size:14px; color:#1e40af; border-left:4px solid #3b82f6; padding-left:10px; margin-bottom:10px; }
        .summary { display: grid; gap: 12px; grid-template-columns: repeat(3, 1fr); }
        .summary-card { padding: 14px; border-radius: 8px; }
        .card-disease { background:#f0f9ff; border-left:4px solid #0284c7; }
        .card-confidence { background:#f0fdf4; border-left:4px solid #16a34a; }
        .card-severity { background:#fefce8; border-left:4px solid #ca8a04; }
        .summary-card p.label { margin:0; font-size:10px; text-transform:uppercase; letter-spacing:.5px; color:#64748b; }
        .summary-card p.value { margin:6px 0 0; font-size:18px; font-weight:bold; color:#0f172a; }
        .diff-table { width:100%; border-collapse:collapse; margin-top:4px; }
        .diff-table th { background:#1e40af; color:white; padding:7px 12px; font-size:12px; text-align:left; }
        .diff-table tr:nth-child(even) { background:#eff6ff; }
        .report-image { width: 100%; max-height: 280px; object-fit: cover; border-radius: 10px; border: 1px solid #e2e8f0; }
        .hospital-item { border-top: 1px solid #e2e8f0; padding: 12px 0; }
        .hospital-item:first-child { border-top: none; }
        .disclaimer { background:#fef2f2; border:1px solid #fca5a5; border-radius:8px; padding:12px; margin-top:12px; }
        .disclaimer p { margin:0; color:#7f1d1d; font-size:13px; }
        footer { border-top:1px solid #e2e8f0; padding:12px 28px; text-align:center; color:#94a3b8; font-size:10px; }
        a { color: #2563eb; }
    </style>
</head>
<body>
    <div class="report">
        <div class="report-header">
            <h1>🩺 MediSkin AI — Diagnostic Report</h1>
            <p>Generated on ${new Date().toLocaleDateString('en-IN', { day: '2-digit', month: 'long', year: 'numeric' })}</p>
        </div>
        <div class="report-body">
            ${imageSrc ? `<div class="section"><img class="report-image" src="${imageSrc}" alt="Uploaded skin image" /></div>` : ''}

            <div class="section">
                <h2>Prediction Summary</h2>
                <div class="summary">
                    <div class="summary-card card-disease"><p class="label">Detected Condition</p><p class="value">${diseaseName}</p><p style="margin:4px 0 0;font-size:12px;color:#1e40af;">${category}</p></div>
                    <div class="summary-card card-confidence"><p class="label">Confidence Score</p><p class="value">${confidence}%</p></div>
                    <div class="summary-card card-severity"><p class="label">Severity Level</p><p class="value">${severity}</p></div>
                </div>
            </div>

            <div class="section">
                <h2>Top Differential Diagnoses</h2>
                <table class="diff-table">
                    <thead><tr><th>#</th><th>Condition</th><th>Category</th><th>Confidence</th></tr></thead>
                    <tbody>${topPredRows}</tbody>
                </table>
            </div>

            <div class="section">
                <h2>Medical Information</h2>
                <p>${descriptions[0]}</p>
                <p>${descriptions[1]}</p>
                <div class="disclaimer"><p>âš  <strong>Important:</strong> Always consult with a qualified dermatologist for professional medical advice and treatment. This report is for informational purposes only.</p></div>
            </div>

            <div class="section">
                <h2>Recommended Hospitals</h2>
                ${hospitalSection}
            </div>
        </div>
        <footer>MediSkin AI Â© 2026 | Confidential Medical Report. For informational purposes only.</footer>
    </div>
</body>
</html>
        `;
    }


    // ── Indian States & Districts ──────────────────────────────────────────────
    const locationData = {
        "Andhra Pradesh": ["Anantapur","Chittoor","East Godavari","Guntur","Krishna","Kurnool","Prakasam","Srikakulam","Visakhapatnam","Vizianagaram","West Godavari","YSR Kadapa"],
        "Karnataka": ["Bangalore Urban","Bangalore Rural","Mysore","Hubli-Dharwad","Mangalore","Belgaum","Gulbarga","Shimoga","Udupi","Tumkur"],
        "Maharashtra": ["Mumbai City","Mumbai Suburban","Pune","Nagpur","Thane","Nashik","Aurangabad","Solapur","Amravati","Kolhapur"],
        "Tamil Nadu": ["Chennai","Coimbatore","Madurai","Trichy","Salem","Tiruppur","Erode","Vellore","Thoothukudi","Kanchipuram"],
        "Telangana": ["Hyderabad","Warangal","Nizamabad","Karimnagar","Khammam","Mahabubnagar","Nalgonda","Rangareddy","Medak","Adilabad"],
        "Delhi": ["New Delhi","North Delhi","South Delhi","West Delhi","East Delhi"],
        "West Bengal": ["Kolkata","Howrah","Hooghly","North 24 Parganas","South 24 Parganas","Darjeeling","Malda","Murshidabad"],
        "Gujarat": ["Ahmedabad","Surat","Vadodara","Rajkot","Bhavnagar","Jamnagar","Junagadh","Gandhinagar"],
        "Kerala": ["Thiruvananthapuram","Kochi","Kozhikode","Thrissur","Kollam","Alappuzha","Kottayam","Palakkad"],
        "Rajasthan": ["Jaipur","Jodhpur","Udaipur","Kota","Ajmer","Bikaner","Alwar","Bharatpur"],
        "Uttar Pradesh": ["Lucknow","Kanpur","Agra","Varanasi","Prayagraj","Meerut","Ghaziabad","Noida"],
        "Madhya Pradesh": ["Bhopal","Indore","Gwalior","Jabalpur","Ujjain","Sagar","Rewa","Satna"],
        "Bihar": ["Patna","Gaya","Bhagalpur","Muzaffarpur","Purnia","Darbhanga","Arrah","Begusarai"],
        "Punjab": ["Ludhiana","Amritsar","Jalandhar","Patiala","Bathinda","Mohali","Fatehgarh Sahib"],
        "Haryana": ["Gurugram","Faridabad","Ambala","Hisar","Rohtak","Panipat","Karnal","Sonipat"]
    };

    // Populate States dropdown
    if (stateSelect) {
        Object.keys(locationData).sort().forEach(function(state) {
            var option = document.createElement('option');
            option.value = state;
            option.textContent = state;
            stateSelect.appendChild(option);
        });

        stateSelect.addEventListener('change', function () {
            var selectedState = this.value;
            districtSelect.innerHTML = '<option value="">Select District</option>';
            if (selectedState && locationData[selectedState]) {
                locationData[selectedState].sort().forEach(function(district) {
                    var option = document.createElement('option');
                    option.value = district;
                    option.textContent = district;
                    districtSelect.appendChild(option);
                });
                districtSelect.disabled = false;
            } else {
                districtSelect.disabled = true;
            }
        });
    }

    // ── View Recommendations: pure Google Maps iframe embed (no API key needed) ──
    var mapsEmbedContainer = document.getElementById('mapsEmbedContainer');
    var mapsEmbedFrame     = document.getElementById('mapsEmbedFrame');
    var mapsEmbedLocation  = document.getElementById('mapsEmbedLocation');

    if (viewRecommendationsBtn) {
        viewRecommendationsBtn.addEventListener('click', function () {
            var state    = stateSelect    ? stateSelect.value.trim()    : '';
            var district = districtSelect ? districtSelect.value.trim() : '';
            var townEl   = document.getElementById('townInput');
            var town     = townEl ? townEl.value.trim() : '';

            if (!state && !district && !town) {
                hospitalsGrid.innerHTML = '<p class="hospitals-placeholder">Please select a State and District first.</p>';
                return;
            }

            var city      = district || town || '';
            var cityLabel = city ? city + ', ' + state : state;

            // Highly specific query — terms like "clinic", "hospital", "dermatologist"
            // push Google Maps toward establishment results instead of pharmacies/stores.
            // Using the /maps/search/ path (not ?q=) returns place-category results.
            var location  = (city ? city + '+' : '') + state.replace(/ /g, '+') + '+India';
            var embedSrc  = 'https://maps.google.com/maps?q=' +
                encodeURIComponent('skin dermatology clinic hospital specialist ' + (city || state) + ' India') +
                '&output=embed&hl=en&z=13';

            if (mapsEmbedFrame)     mapsEmbedFrame.src = embedSrc;
            if (mapsEmbedLocation)  mapsEmbedLocation.textContent = cityLabel;
            if (mapsEmbedContainer) mapsEmbedContainer.classList.remove('hidden');

            // ── Clinic cards below the map ─────────────────────────────────────
            displayHospitals(getSearchHospitals(city, state));
        });
    }

    // ── Curated Dermatology Hospital Database ──────────────────────────────────
    // Each entry: { name, specialty, location, contact, mapsQuery, image }
    // mapsQuery is passed to Google Maps search — specific enough to show ONE result.
    var _hospitalDB = {
        // Telangana
        'Hyderabad': [
            { name: 'CARE Hospitals – Skin & Dermatology', specialty: 'Dermatology & Cosmetology', location: 'Road No.1, Banjara Hills, Hyderabad', contact: '+91 40 3041 8888', mapsQuery: 'CARE Hospitals Dermatology Banjara Hills Hyderabad' },
            { name: 'Apollo Skin Care Centre', specialty: 'Advanced Dermatology & Laser', location: 'Film Nagar, Jubilee Hills, Hyderabad', contact: '+91 40 2360 7777', mapsQuery: 'Apollo Skin Care Centre Jubilee Hills Hyderabad' },
            { name: 'Renova Skin Hair & Cosmetic Clinic', specialty: 'Skin, Hair & Cosmetic Surgery', location: 'Jubilee Hills, Hyderabad', contact: '+91 40 2355 5755', mapsQuery: 'Renova Skin Hair Cosmetic Clinic Jubilee Hills Hyderabad' }
        ],
        'Rangareddy': [
            { name: 'Apollo Hospital Dermatology – Hyderguda', specialty: 'Dermatology & Venereology', location: 'Hyderguda, Hyderabad', contact: '+91 40 2360 7777', mapsQuery: 'Apollo Hospital Dermatology Hyderguda Hyderabad' },
            { name: 'Kamineni Skin Care', specialty: 'Dermatology, Allergy & Laser', location: 'LB Nagar, Hyderabad', contact: '+91 40 3987 9999', mapsQuery: 'Kamineni Skin Care LB Nagar Hyderabad' },
            { name: 'Kaya Skin Clinic – Banjara Hills', specialty: 'Skin & Hair Treatment', location: 'Banjara Hills, Hyderabad', contact: '1800 209 5292', mapsQuery: 'Kaya Skin Clinic Banjara Hills Hyderabad' }
        ],
        // Karnataka
        'Bangalore Urban': [
            { name: 'Manipal Hospital – Dermatology Dept.', specialty: 'Dermatology & Venereology', location: 'HAL Old Airport Road, Kodihalli, Bengaluru', contact: '+91 80 2502 4444', mapsQuery: 'Manipal Hospital Dermatology Old Airport Road Bangalore' },
            { name: 'Apollo Hospitals – Skin & Laser Centre', specialty: 'Laser Dermatology & Cosmetology', location: 'Bannerghatta Road, Bengaluru', contact: '+91 80 2630 4050', mapsQuery: 'Apollo Hospitals Skin Laser Centre Bannerghatta Bangalore' },
            { name: 'Sparsh Hospital – Dermatology', specialty: 'Department of Dermatology', location: 'Infantry Road, Vasanth Nagar, Bengaluru', contact: '+91 80 6122 6122', mapsQuery: 'Sparsh Hospital Dermatology Infantry Road Bangalore' }
        ],
        'Mysore': [
            { name: 'JSS Hospital – Dermatology Dept.', specialty: 'Dermatology & STD Clinic', location: 'Agrahara, Mysore', contact: '+91 821 2548 400', mapsQuery: 'JSS Hospital Dermatology Mysore' },
            { name: 'Columbia Asia Hospital – Skin Clinic', specialty: 'Dermatology & Cosmetology', location: 'Mysore', contact: '+91 821 3989 999', mapsQuery: 'Columbia Asia Hospital Skin Clinic Mysore' },
            { name: 'Kaya Skin Clinic – Mysore', specialty: 'Skin & Hair Treatment', location: 'Saraswathipuram, Mysore', contact: '1800 209 5292', mapsQuery: 'Kaya Skin Clinic Mysore' }
        ],
        // Tamil Nadu
        'Chennai': [
            { name: 'Apollo Hospitals – Dermatology Dept.', specialty: 'Dermatology, Laser & Cosmetology', location: 'Greams Road, Chennai', contact: '+91 44 2829 3333', mapsQuery: 'Apollo Hospitals Dermatology Greams Road Chennai' },
            { name: 'MIOT International – Dermatology', specialty: 'Skin & Dermatology', location: 'Manapakkam, Chennai', contact: '+91 44 4200 2288', mapsQuery: 'MIOT International Dermatology Manapakkam Chennai' },
            { name: 'Fortis Malar Hospital – Skin Clinic', specialty: 'Dermatology & Venereology', location: 'Adyar, Chennai', contact: '+91 44 4289 2222', mapsQuery: 'Fortis Malar Hospital Dermatology Adyar Chennai' }
        ],
        'Coimbatore': [
            { name: 'PSG Hospitals – Dermatology Dept.', specialty: 'Dermatology & STD', location: 'Peelamedu, Coimbatore', contact: '+91 422 434 4000', mapsQuery: 'PSG Hospitals Dermatology Peelamedu Coimbatore' },
            { name: 'G. Kuppuswamy Naidu Memorial Hospital – Skin', specialty: 'Skin & Dermatology', location: 'Pappanaickenpalayam, Coimbatore', contact: '+91 422 430 0000', mapsQuery: 'Kuppuswamy Naidu Hospital Dermatology Coimbatore' },
            { name: 'Kaya Skin Clinic – Coimbatore', specialty: 'Skin & Hair Treatment', location: 'RS Puram, Coimbatore', contact: '1800 209 5292', mapsQuery: 'Kaya Skin Clinic RS Puram Coimbatore' }
        ],
        // Maharashtra
        'Mumbai City': [
            { name: 'Hinduja Hospital – Dermatology Dept.', specialty: 'Dermatology, Venereology & Leprosy', location: 'Mahim, Mumbai', contact: '+91 22 2445 2222', mapsQuery: 'Hinduja Hospital Dermatology Mahim Mumbai' },
            { name: 'Lilavati Hospital – Skin Clinic', specialty: 'Dermatology & Cosmetology', location: 'Bandra West, Mumbai', contact: '+91 22 2675 1000', mapsQuery: 'Lilavati Hospital Dermatology Bandra Mumbai' },
            { name: 'Bombay Hospital – Dermatology', specialty: 'Skin & Dermatology', location: 'Marine Lines, Mumbai', contact: '+91 22 2206 7676', mapsQuery: 'Bombay Hospital Dermatology Marine Lines Mumbai' }
        ],
        'Mumbai Suburban': [
            { name: 'Kokilaben Dhirubhai Ambani Hospital – Skin', specialty: 'Dermatology & Cosmetology', location: 'Andheri West, Mumbai', contact: '+91 22 3066 3066', mapsQuery: 'Kokilaben Hospital Dermatology Andheri Mumbai' },
            { name: 'SRV Hospital – Dermatology', specialty: 'Skin & Laser Treatment', location: 'Goregaon, Mumbai', contact: '+91 22 3055 0000', mapsQuery: 'SRV Hospital Dermatology Goregaon Mumbai' },
            { name: 'Kaya Skin Clinic – Andheri', specialty: 'Skin, Hair & Laser', location: 'Andheri East, Mumbai', contact: '1800 209 5292', mapsQuery: 'Kaya Skin Clinic Andheri Mumbai' }
        ],
        'Pune': [
            { name: 'Ruby Hall Clinic – Dermatology', specialty: 'Dermatology & Venereology', location: 'Sassoon Road, Pune', contact: '+91 20 6645 5000', mapsQuery: 'Ruby Hall Clinic Dermatology Sassoon Road Pune' },
            { name: 'Jehangir Hospital – Skin Clinic', specialty: 'Skin & Dermatology Dept.', location: 'Sassoon Road, Pune', contact: '+91 20 4153 3333', mapsQuery: 'Jehangir Hospital Dermatology Pune' },
            { name: 'Deenanath Mangeshkar Hospital – Skin', specialty: 'Dermatology & Cosmetic Dermatology', location: 'Erandwane, Pune', contact: '+91 20 4901 5000', mapsQuery: 'Deenanath Mangeshkar Hospital Dermatology Pune' }
        ],
        // Delhi
        'Delhi': [
            { name: 'AIIMS – Department of Dermatology', specialty: 'Dermatology & Venereology', location: 'Ansari Nagar, New Delhi', contact: '+91 11 2658 8500', mapsQuery: 'AIIMS Department of Dermatology Ansari Nagar Delhi' },
            { name: 'Apollo Hospital – Skin & Dermatology', specialty: 'Advanced Dermatology & Laser', location: 'Sarita Vihar, New Delhi', contact: '+91 11 7179 1090', mapsQuery: 'Apollo Hospital Dermatology Sarita Vihar Delhi' },
            { name: 'Max Smart Super Speciality – Skin Clinic', specialty: 'Dermatology & Cosmetology', location: 'Saket, New Delhi', contact: '+91 11 2651 5050', mapsQuery: 'Max Smart Super Speciality Hospital Dermatology Saket Delhi' }
        ],
        'New Delhi': [
            { name: 'AIIMS – Department of Dermatology', specialty: 'Dermatology & Venereology', location: 'Ansari Nagar, New Delhi', contact: '+91 11 2658 8500', mapsQuery: 'AIIMS Department of Dermatology Ansari Nagar New Delhi' },
            { name: 'Sir Ganga Ram Hospital – Skin Dept.', specialty: 'Dermatology, Venereology & Leprosy', location: 'Rajinder Nagar, New Delhi', contact: '+91 11 2575 0000', mapsQuery: 'Sir Ganga Ram Hospital Dermatology New Delhi' },
            { name: 'Fortis Flt. Lt. Rajan Dhall Hospital – Skin', specialty: 'Dermatology & Cosmetology', location: 'Vasant Kunj, New Delhi', contact: '+91 11 4277 6222', mapsQuery: 'Fortis Rajan Dhall Hospital Dermatology Vasant Kunj Delhi' }
        ],
        // West Bengal
        'Kolkata': [
            { name: 'AMRI Hospital – Dermatology', specialty: 'Dermatology & Allergology', location: 'Dhakuria, Kolkata', contact: '+91 33 6680 0000', mapsQuery: 'AMRI Hospital Dermatology Dhakuria Kolkata' },
            { name: 'Apollo Gleneagles Hospital – Skin', specialty: 'Dermatology & Cosmetology', location: 'Canal Circular Road, Kolkata', contact: '+91 33 2320 3040', mapsQuery: 'Apollo Gleneagles Hospital Dermatology Kolkata' },
            { name: 'Peerless Hospital – Skin & Dermatology', specialty: 'Dermatology, Venereology & Leprosy', location: 'Panchasayar, Kolkata', contact: '+91 33 4011 1222', mapsQuery: 'Peerless Hospital Dermatology Kolkata' }
        ],
        // Gujarat
        'Ahmedabad': [
            { name: 'Apollo Hospital – Dermatology Dept.', specialty: 'Dermatology & Cosmetology', location: 'Bhat, Ahmedabad', contact: '+91 79 6670 1800', mapsQuery: 'Apollo Hospital Dermatology Bhat Ahmedabad' },
            { name: 'Sterling Hospital – Skin Clinic', specialty: 'Skin, Hair & Nail Disorders', location: 'Memnagar, Ahmedabad', contact: '+91 79 4000 3000', mapsQuery: 'Sterling Hospital Dermatology Memnagar Ahmedabad' },
            { name: 'Zydus Hospital – Dermatology', specialty: 'Advanced Dermatology & Laser', location: 'Thaltej, Ahmedabad', contact: '+91 79 6619 0000', mapsQuery: 'Zydus Hospital Dermatology Thaltej Ahmedabad' }
        ],
        // Kerala
        'Kochi': [
            { name: 'Amrita Institute – Dermatology Dept.', specialty: 'Dermatology & Venereology', location: 'Edapally, Kochi', contact: '+91 484 2801 234', mapsQuery: 'Amrita Institute Dermatology Edapally Kochi' },
            { name: 'Aster Medcity – Skin & Dermatology', specialty: 'Dermatology, Cosmetology & Laser', location: 'Cheranalloor, Kochi', contact: '+91 484 6699 999', mapsQuery: 'Aster Medcity Dermatology Cheranalloor Kochi' },
            { name: 'Lakeshore Hospital – Dermatology', specialty: 'Skin & Dermatology', location: 'Maradu, Kochi', contact: '+91 484 2701 032', mapsQuery: 'Lakeshore Hospital Dermatology Maradu Kochi' }
        ],
        // Rajasthan
        'Jaipur': [
            { name: 'Fortis Escort Hospital – Skin Dept.', specialty: 'Dermatology & Cosmetology', location: 'Jawahar Lal Nehru Marg, Jaipur', contact: '+91 141 2547 000', mapsQuery: 'Fortis Escorts Hospital Dermatology Jaipur' },
            { name: 'Eternal Hospital – Dermatology', specialty: 'Skin, Hair & Nail Clinic', location: 'JLN Road, Jaipur', contact: '+91 141 4141 414', mapsQuery: 'Eternal Hospital Dermatology JLN Road Jaipur' },
            { name: 'Mahatma Gandhi Hospital – Skin Dept.', specialty: 'Dermatology & Venereology', location: 'Sitabari, Jaipur', contact: '+91 141 2706 246', mapsQuery: 'Mahatma Gandhi Hospital Dermatology Jaipur' }
        ],
        // Uttar Pradesh
        'Lucknow': [
            { name: 'SGPGI – Dermatology Dept.', specialty: 'Dermatology, Venereology & Leprosy', location: 'Raebareli Road, Lucknow', contact: '+91 522 266 8700', mapsQuery: 'SGPGI Dermatology Raebareli Road Lucknow' },
            { name: 'Medanta – The Medicity Skin Clinic', specialty: 'Dermatology & Cosmetology', location: 'Sushant Golf City, Lucknow', contact: '+91 522 4505 050', mapsQuery: 'Medanta Skin Clinic Sushant Golf City Lucknow' },
            { name: 'Apollo Hospital – Dermatology Dept.', specialty: 'Advanced Dermatology & Laser', location: 'Kanpur Road, Lucknow', contact: '+91 522 4677 666', mapsQuery: 'Apollo Hospital Dermatology Kanpur Road Lucknow' }
        ],
        // Punjab
        'Ludhiana': [
            { name: 'DMC Hospital – Dermatology Dept.', specialty: 'Dermatology & Venereology', location: 'Tagore Nagar, Ludhiana', contact: '+91 161 530 2000', mapsQuery: 'DMC Hospital Dermatology Tagore Nagar Ludhiana' },
            { name: 'Apollo Hospital – Skin Clinic', specialty: 'Dermatology & Cosmetology', location: 'Grand Walk Mall, Ludhiana', contact: '+91 161 508 0055', mapsQuery: 'Apollo Hospital Dermatology Ludhiana' },
            { name: 'Fortis Hospital – Dermatology', specialty: 'Skin Diseases & Laser Treatment', location: 'Chandigarh Road, Ludhiana', contact: '+91 161 501 2222', mapsQuery: 'Fortis Hospital Dermatology Chandigarh Road Ludhiana' }
        ],
        // Haryana
        'Gurugram': [
            { name: 'Medanta – The Medicity Dermatology', specialty: 'Dermatology, Cosmetology & Laser', location: 'Sector 38, Gurugram', contact: '+91 124 414 1414', mapsQuery: 'Medanta Medicity Dermatology Sector 38 Gurugram' },
            { name: 'Fortis Memorial Research Institute – Skin', specialty: 'Dermatology & Aesthetic Medicine', location: 'Sector 44, Gurugram', contact: '+91 124 492 1021', mapsQuery: 'Fortis Memorial Research Institute Dermatology Gurugram' },
            { name: 'Artemis Hospital – Dermatology', specialty: 'Skin, Hair & Nail Disorders', location: 'Sector 51, Gurugram', contact: '+91 124 676 7676', mapsQuery: 'Artemis Hospital Dermatology Sector 51 Gurugram' }
        ]
    };

    /**
     * Returns 3 named hospital cards for the selected city.
     * Each card's directionsUrl uses the exact hospital name+city so Google Maps
     * opens THAT specific hospital — not a generic category search.
     */
    function getSearchHospitals(city, state) {
        // Try exact city match, then state-level fallback, then generic
        var key     = city || state;
        var entries = _hospitalDB[key] || _hospitalDB[state] || null;
        var loc     = (city ? city + ', ' : '') + state + ', India';

        if (entries) {
            return entries.map(function(h) {
                return {
                    name:         h.name,
                    specialty:    h.specialty,
                    location:     h.location,
                    contact:      h.contact,
                    // Search by exact hospital name → Google Maps opens that specific place
                    directionsUrl: 'https://www.google.com/maps/search/' +
                                   encodeURIComponent(h.mapsQuery),
                    image: 'https://images.unsplash.com/photo-1587350859743-b15272315fa1?auto=format&fit=crop&w=800&q=80'
                };
            });
        }

        // Fallback: no curated data for this city — use name-specific search queries
        return [
            {
                name:         'Skin & Dermatology Clinic – ' + (city || state),
                specialty:    'General Dermatology & Skin Diseases',
                location:     loc,
                contact:      'Click to find exact clinic on Google Maps',
                directionsUrl: 'https://www.google.com/maps/search/' +
                               encodeURIComponent('skin dermatology clinic ' + (city || state) + ' India'),
                image: 'https://images.unsplash.com/photo-1587350859743-b15272315fa1?auto=format&fit=crop&w=800&q=80'
            },
            {
                name:         'Hospital Dermatology Dept. – ' + (city || state),
                specialty:    'Hospital-based Dermatology Unit',
                location:     loc,
                contact:      'Click to find exact hospital on Google Maps',
                directionsUrl: 'https://www.google.com/maps/search/' +
                               encodeURIComponent('hospital dermatology department ' + (city || state) + ' India'),
                image: 'https://images.unsplash.com/photo-1516549655169-df83a0774514?auto=format&fit=crop&w=800&q=80'
            },
            {
                name:         'Laser & Cosmetology Skin Centre – ' + (city || state),
                specialty:    'Cosmetology, Laser & Hair Treatment',
                location:     loc,
                contact:      'Click to find exact centre on Google Maps',
                directionsUrl: 'https://www.google.com/maps/search/' +
                               encodeURIComponent('cosmetology laser skin centre ' + (city || state) + ' India'),
                image: 'https://images.unsplash.com/photo-1519494026892-80bbd2d6fd0d?auto=format&fit=crop&w=800&q=80'
            }
        ];
    }


    /** Static fallback shown when API key is missing or network fails */
    function getFallbackHospitals(city, state) {
        var loc = (city ? city + ', ' : '') + (state || '') + ', India';
        return [
            {
                name: (city || state) + ' Dermatology Centre',
                specialty: 'Skin Disease & Laser Treatment',
                location: loc,
                contact: 'Contact local directory',
                directionsUrl: 'https://www.google.com/maps/search/dermatologist+' + encodeURIComponent((city || state) + ' India'),
                image: 'https://images.unsplash.com/photo-1587350859743-b15272315fa1?auto=format&fit=crop&w=800&q=80'
            },
            {
                name: 'Apollo Skin Care — ' + (city || state),
                specialty: 'Advanced Dermatology & Cosmetology',
                location: loc,
                contact: 'Contact local directory',
                directionsUrl: 'https://www.google.com/maps/search/Apollo+skin+dermatology+' + encodeURIComponent((city || state) + ' India'),
                image: 'https://images.unsplash.com/photo-1519494026892-80bbd2d6fd0d?auto=format&fit=crop&w=800&q=80'
            },
            {
                name: 'City Skin & Hair Clinic — ' + (city || state),
                specialty: 'Trichology & Dermatology',
                location: loc,
                contact: 'Contact local directory',
                directionsUrl: 'https://www.google.com/maps/search/skin+clinic+dermatologist+' + encodeURIComponent((city || state) + ' India'),
                image: 'https://images.unsplash.com/photo-1516549655169-df83a0774514?auto=format&fit=crop&w=800&q=80'
            }
        ];
    }

    /** Render hospital cards — clicking opens exact Google Maps directions */
    function displayHospitals(hospitals) {
        var hospitalsToShow = hospitals.slice(0, 3);

        var hospitalsHTML = hospitalsToShow.map(function(hospital) {
            var mapsUrl = hospital.directionsUrl ||
                ('https://www.google.com/maps/dir/?api=1&destination=' + encodeURIComponent(hospital.name + ' ' + hospital.location));

            return '<div class="hospital-item" onclick="window.open(\'' + mapsUrl + '\',\'_blank\')" title="Click for directions">' +
                '<div class="hospital-image-container">' +
                '<img src="' + hospital.image + '" alt="' + hospital.name + '" class="hospital-img" loading="eager"' +
                ' onerror="this.src=\'data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%22800%22 height=%22600%22%3E%3Crect fill=%22%23667eea%22 width=%22800%22 height=%22600%22/%3E%3Ctext x=%2250%25%22 y=%2250%25%22 font-size=%2248%22 fill=%22white%22 text-anchor=%22middle%22 dy=%22.3em%22%3E&#127973;%3C/text%3E%3C/svg%3E\'"' +
                ' style="object-fit:cover;width:100%;height:100%;">' +
                '<div class="hospital-image-overlay"><span class="directions-tag">&#128205; Get Directions</span></div>' +
                '</div>' +
                '<div class="hospital-content-box">' +
                '<h4 class="hospital-name">' + hospital.name + '</h4>' +
                '<p class="hospital-specialty">&#127973; ' + hospital.specialty + '</p>' +
                '<div class="hospital-info-group">' +
                '<p class="hospital-location"><svg fill="none" stroke="currentColor" viewBox="0 0 24 24">' +
                '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"></path>' +
                '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"></path></svg>' +
                hospital.location + '</p>' +
                '<p class="hospital-contact"><svg fill="none" stroke="currentColor" viewBox="0 0 24 24">' +
                '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z"></path></svg>' +
                hospital.contact + '</p>' +
                '</div></div></div>';
        }).join('');

        var infoContainer =
            '<div class="hospital-info-container"><div class="info-content">' +
            '<svg class="info-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">' +
            '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>' +
            '<div class="info-text"><h4>Important Information</h4>' +
            '<p>Click any card to open <strong>Google Maps directions</strong> to that clinic.</p>' +
            '<p class="info-note"><strong>Note:</strong> Always consult a qualified dermatologist for professional medical advice.</p>' +
            '</div></div></div>';

        hospitalsGrid.innerHTML = hospitalsHTML + infoContainer;

        lastHospitals = hospitalsToShow.map(function(h) {
            return { name: h.name, specialty: h.specialty, location: h.location, contact: h.contact };
        });
    }


    // Feedback Form
    // Feedback Form
    feedbackButtons.forEach(btn => {
        btn.addEventListener('click', function () {
            feedbackButtons.forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            feedbackAccuracy.value = this.dataset.value;
            document.getElementById('accuracyError').classList.remove('active');
        });
    });

    feedbackForm.addEventListener('submit', async function (e) {
        e.preventDefault();

        if (!feedbackAccuracy.value) {
            document.getElementById('accuracyError').classList.add('active');
            return;
        }

        const feedbackData = {
            accuracy: feedbackAccuracy.value,
            comments: document.getElementById('feedbackComments').value.trim()
        };

        try {
            // Simulate API call
            await new Promise(resolve => setTimeout(resolve, 1000));

            // Show success message
            document.getElementById('feedbackSuccess').classList.remove('hidden');

            // Reset form after 2 seconds
            setTimeout(() => {
                feedbackForm.reset();
                feedbackButtons.forEach(b => b.classList.remove('active'));
                document.getElementById('feedbackSuccess').classList.add('hidden');
            }, 3000);

        } catch (error) {
            console.error('Feedback error:', error);
        }
    });

    // Helper functions
    function showLoading(button) {
        button.querySelector('.btn-text').classList.add('hidden');
        button.querySelector('.btn-loader').classList.remove('hidden');
        button.disabled = true;
    }

    function hideLoading(button) {
        button.querySelector('.btn-text').classList.remove('hidden');
        button.querySelector('.btn-loader').classList.add('hidden');
        button.disabled = false;
    }
});
