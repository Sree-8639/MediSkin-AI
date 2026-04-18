/**
 * API Configuration and Client
 * ═════════════════════════════════════════════════════════════════════════════
 * 
 * Dynamically configures the API base URL based on:
 * - Environment (development vs production)
 * - Browser environment detection
 * - Environment variables
 * 
 * Usage:
 *   import { apiCall, API_URL } from './api-client.js';
 *   
 *   // Make a request
 *   const response = await apiCall('/predict/', {
 *     method: 'POST',
 *     body: JSON.stringify({ image: base64 })
 *   });
 */

// Determine API URL based on environment
export const API_URL = (() => {
  // Check if running in browser
  if (typeof window === 'undefined') {
    return process.env.NEXT_PUBLIC_API_URL || 'https://mediskin-backend.onrender.com';
  }

  // Development environment
  if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    return 'http://localhost:8000';
  }

  // Production environment
  const envApiUrl = window.__API_URL__ || process.env.REACT_APP_API_URL;
  return envApiUrl || 'https://mediskin-backend.onrender.com';
})();

/**
 * Generic API call wrapper
 * Automatically handles:
 * - Base URL prepending
 * - CORS headers
 * - Error handling
 * - JSON parsing
 * 
 * @param {string} endpoint - API endpoint (e.g., '/api/predict/')
 * @param {object} options - Fetch options (method, body, headers, etc.)
 * @returns {Promise<object>} Parsed JSON response
 */
export async function apiCall(endpoint, options = {}) {
  const url = `${API_URL}${endpoint}`;
  
  const defaultHeaders = {
    'Content-Type': 'application/json',
  };

  // Include CSRF token if available (from Django)
  const csrfToken = getCookie('csrftoken');
  if (csrfToken) {
    defaultHeaders['X-CSRFToken'] = csrfToken;
  }

  const config = {
    method: options.method || 'GET',
    headers: {
      ...defaultHeaders,
      ...options.headers,
    },
    credentials: 'include',  // Include cookies for authentication
    ...options,
  };

  try {
    console.log(`[API] ${config.method} ${url}`);
    const response = await fetch(url, config);

    if (!response.ok) {
      const error = new Error(`API Error: ${response.status} ${response.statusText}`);
      error.status = response.status;
      error.response = response;
      throw error;
    }

    const contentType = response.headers.get('content-type');
    if (contentType?.includes('application/json')) {
      return await response.json();
    }

    return await response.text();
  } catch (error) {
    console.error(`[API Error] ${config.method} ${url}:`, error);
    throw error;
  }
}

/**
 * Get CSRF token from cookies (Django requirement)
 * @param {string} name - Cookie name
 * @returns {string|null} Cookie value
 */
function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === name + '=') {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

/**
 * Specialized API call for file uploads (such as skin disease images)
 * Handles multipart/form-data and doesn't set Content-Type header
 * (browser will set it automatically with boundary)
 * 
 * @param {string} endpoint - API endpoint
 * @param {FormData} formData - FormData object with files
 * @returns {Promise<object>} Parsed JSON response
 */
export async function apiUpload(endpoint, formData) {
  const url = `${API_URL}${endpoint}`;
  
  const headers = {};
  
  // Include CSRF token if available
  const csrfToken = getCookie('csrftoken');
  if (csrfToken) {
    headers['X-CSRFToken'] = csrfToken;
  }

  try {
    console.log(`[API] POST ${url} (multipart/form-data)`);
    const response = await fetch(url, {
      method: 'POST',
      headers,
      body: formData,
      credentials: 'include',
    });

    if (!response.ok) {
      const error = new Error(`Upload Error: ${response.status} ${response.statusText}`);
      error.status = response.status;
      throw error;
    }

    return await response.json();
  } catch (error) {
    console.error(`[API Error] POST ${url}:`, error);
    throw error;
  }
}

// Export API_URL and utility functions for use in other modules
export default {
  API_URL,
  apiCall,
  apiUpload,
};
