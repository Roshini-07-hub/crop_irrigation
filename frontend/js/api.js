/* ==========================================================================
   SMART IRRIGATION AI - API CLIENT MODULE
   Provides unified communication with the Flask backend.
   Supports automatic host detection (works with file:// and http://).
   ========================================================================== */

const API_BASE_URL = (() => {
    if (typeof window !== "undefined" && window.location && window.location.origin) {
        if (window.location.origin.startsWith("http")) {
            return `${window.location.origin}/api`;
        }
    }
    return "http://127.0.0.1:5000/api";
})();

const ROOT_BASE_URL = (() => {
    if (typeof window !== "undefined" && window.location && window.location.origin) {
        if (window.location.origin.startsWith("http")) {
            return window.location.origin;
        }
    }
    return "http://127.0.0.1:5000";
})();

/**
 * Generic Fetch Wrapper with JSON decoding and friendly error reporting
 */
async function apiRequest(endpoint, options = {}) {
    const url = endpoint.startsWith("http") ? endpoint : `${API_BASE_URL}${endpoint}`;
    
    try {
        const response = await fetch(url, {
            ...options,
            headers: {
                "Content-Type": "application/json",
                "Accept": "application/json",
                ...(options.headers || {})
            }
        });

        let data;
        try {
            data = await response.json();
        } catch (parseError) {
            throw new Error(`Server returned non-JSON response (${response.status} ${response.statusText}). Ensure backend server is running.`);
        }

        if (!response.ok) {
            const errorMsg = data.error || data.details || `API request failed with status ${response.status}`;
            throw new Error(errorMsg);
        }

        return data;
    } catch (err) {
        if (err.message && err.message.includes("Failed to fetch")) {
            throw new Error("Cannot connect to backend server. Make sure 'python backend/app.py' is running on http://127.0.0.1:5000.");
        }
        throw err;
    }
}

// ==========================================================================
// SYSTEM & HEALTH API
// ==========================================================================

async function getHealthStatus() {
    try {
        const res = await fetch(`${ROOT_BASE_URL}/health`, {
            headers: { "Accept": "application/json" }
        });
        return await res.json();
    } catch (e) {
        return { success: false, status: "offline", error: e.message };
    }
}

async function getSystemStatus() {
    return await apiRequest("/status");
}

// ==========================================================================
// CROPS API
// ==========================================================================

let _cropsCache = null;

async function getCrops() {
    if (_cropsCache) {
        return _cropsCache;
    }
    const data = await apiRequest("/crops/");
    _cropsCache = data;
    return data;
}

// ==========================================================================
// PREDICTION APIS
// ==========================================================================

/**
 * Predict water requirement with manual inputs (ETo, rainfall, area, method)
 */
async function predictWater(inputData) {
    return await apiRequest("/predict/water", {
        method: "POST",
        body: JSON.stringify(inputData)
    });
}

/**
 * Predict water requirement automatically from location and live weather
 */
async function predictWaterFromWeather(inputData) {
    return await apiRequest("/predict/water/weather", {
        method: "POST",
        body: JSON.stringify(inputData)
    });
}

/**
 * Complete prediction: Water Requirement + Irrigation Decision
 */
async function predictComplete(inputData) {
    return await apiRequest("/predict/complete", {
        method: "POST",
        body: JSON.stringify(inputData)
    });
}

/**
 * Live Weather + Irrigation Recommendation
 */
async function getWeatherIrrigationRecommendation(inputData) {
    return await apiRequest("/predict/weather/irrigation", {
        method: "POST",
        body: JSON.stringify(inputData)
    });
}

// ==========================================================================
// WEATHER & LOCATION APIS
// ==========================================================================

async function getWeather(latitude, longitude) {
    const params = new URLSearchParams({
        latitude: String(latitude),
        longitude: String(longitude)
    });
    return await apiRequest(`/weather/?${params.toString()}`);
}

async function searchLocation(query) {
    const params = new URLSearchParams({ q: query.trim() });
    return await apiRequest(`/location/search?${params.toString()}`);
}

// ==========================================================================
// HISTORY APIS
// ==========================================================================

async function getAllHistory(limit = 50, type = null) {
    const params = new URLSearchParams({ limit: String(limit) });
    if (type) {
        params.append("type", type);
    }
    return await apiRequest(`/history/?${params.toString()}`);
}

async function getWaterHistory(limit = 50) {
    return await apiRequest(`/history/water?limit=${limit}`);
}

async function getCompleteHistory(limit = 50) {
    return await apiRequest(`/history/complete?limit=${limit}`);
}

async function getWeatherHistory(limit = 50) {
    return await apiRequest(`/history/weather?limit=${limit}`);
}

async function deleteHistoryRecord(recordId) {
    return await apiRequest(`/history/${encodeURIComponent(recordId)}`, {
        method: "DELETE"
    });
}

// Export functions to global scope for script tags
if (typeof window !== "undefined") {
    window.API_BASE_URL = API_BASE_URL;
    window.ROOT_BASE_URL = ROOT_BASE_URL;
    window.apiRequest = apiRequest;
    window.getHealthStatus = getHealthStatus;
    window.getSystemStatus = getSystemStatus;
    window.getCrops = getCrops;
    window.predictWater = predictWater;
    window.predictWaterFromWeather = predictWaterFromWeather;
    window.predictComplete = predictComplete;
    window.getWeatherIrrigationRecommendation = getWeatherIrrigationRecommendation;
    window.getWeather = getWeather;
    window.searchLocation = searchLocation;
    window.getAllHistory = getAllHistory;
    window.getWaterHistory = getWaterHistory;
    window.getCompleteHistory = getCompleteHistory;
    window.getWeatherHistory = getWeatherHistory;
    window.deleteHistoryRecord = deleteHistoryRecord;
}
