/* ==========================================================================
   IRRIGATION ADVISORY CONTROLLER
   Handles 55-crop dropdowns, soil moisture slider, location, and recommendation.
   ========================================================================== */

let cropsList = [];

document.addEventListener("DOMContentLoaded", async () => {
    // 1. Initialize crops dropdown
    await initIrrigationCrops();

    // 2. Check for passed session parameters from Water Prediction page
    checkPreFill();

    // 3. Soil moisture slider listener
    const slider = document.getElementById("irrSoilMoistureSlider");
    if (slider) {
        slider.addEventListener("input", (e) => {
            const val = parseInt(e.target.value, 10);
            const label = getMoistureConditionLabel(val);
            const display = document.getElementById("moistureValDisplay");
            if (display) display.textContent = `${val}% (${label})`;
        });
    }

    // 4. Initialize location search & GPS
    initIrrigationLocation();

    // 5. Hook up Live mode submit
    const liveForm = document.getElementById("liveIrrigationForm");
    if (liveForm) {
        liveForm.addEventListener("submit", handleLiveSubmit);
    }

    // 6. Hook up Manual mode submit
    const manualForm = document.getElementById("manualIrrigationForm");
    if (manualForm) {
        manualForm.addEventListener("submit", handleManualSubmit);
    }
});

function getMoistureConditionLabel(val) {
    if (val < 20) return "Very Dry - Critical";
    if (val < 30) return "Dry - High Need";
    if (val < 40) return "Moderately Moist";
    if (val < 70) return "Adequate Moisture";
    return "Very Wet / Saturated";
}

async function initIrrigationCrops() {
    try {
        const res = await getCrops();
        cropsList = res.crops || [];
        const select = document.getElementById("irrCrop");
        if (!select) return;

        const grouped = {};
        cropsList.forEach(c => {
            const grp = c.crop_group || "General Crops";
            if (!grouped[grp]) grouped[grp] = [];
            grouped[grp].push(c);
        });

        let html = '<option value="">Select Crop...</option>';
        for (const grp of Object.keys(grouped).sort()) {
            html += `<optgroup label="${grp}">`;
            grouped[grp].forEach(c => {
                const sel = c.crop === "Wheat" ? "selected" : "";
                html += `<option value="${c.crop}" ${sel}>${c.crop}</option>`;
            });
            html += `</optgroup>`;
        }
        select.innerHTML = html;
    } catch (e) {
        console.error("Crops init error:", e);
    }
}

function checkPreFill() {
    try {
        const raw = sessionStorage.getItem("lastPrediction");
        if (raw) {
            const data = JSON.parse(raw);
            const crop = data.prediction?.crop || data.input?.crop;
            const stage = data.prediction?.growth_stage || data.input?.growth_stage;
            const area = data.prediction?.field_area_hectare || data.input?.field_area_hectare;

            if (crop) {
                const cropSelect = document.getElementById("irrCrop");
                if (cropSelect) cropSelect.value = crop;
            }
            if (stage) {
                const stageSelect = document.getElementById("irrGrowthStage");
                if (stageSelect) stageSelect.value = stage;
            }
            if (data.input?.soil_type) {
                const soilSelect = document.getElementById("irrSoilType");
                if (soilSelect) {
                    for (let i = 0; i < soilSelect.options.length; i++) {
                        if (soilSelect.options[i].value.toLowerCase() === data.input.soil_type.toLowerCase()) {
                            soilSelect.selectedIndex = i;
                            break;
                        }
                    }
                }
            }
            if (area) {
                const liveArea = document.getElementById("irrLiveArea");
                const manArea = document.getElementById("manArea");
                if (liveArea) liveArea.value = area;
                if (manArea) manArea.value = area;
            }

            // Prefill Location (Coordinates & Name) from Water Prediction
            if (data.input?.latitude && data.input?.longitude) {
                const lat = data.input.latitude;
                const lon = data.input.longitude;
                const locName = data.input.location_name || `${lat.toFixed(3)}° N, ${lon.toFixed(3)}° E`;
                const latEl = document.getElementById("irrLat");
                const lonEl = document.getElementById("irrLon");
                const nameEl = document.getElementById("irrLocName");
                const coordsEl = document.getElementById("irrLocCoords");
                if (latEl) latEl.value = lat;
                if (lonEl) lonEl.value = lon;
                if (nameEl) nameEl.textContent = locName;
                if (coordsEl) coordsEl.textContent = `${lat.toFixed(3)}° N, ${lon.toFixed(3)}° E`;
            }

            // Prefill Irrigation Method
            const method = data.prediction?.irrigation_method || data.input?.irrigation_method;
            if (method) {
                const liveMethod = document.getElementById("irrLiveMethod");
                const manMethod = document.getElementById("manMethod");
                const selectMatching = (sel) => {
                    if (!sel) return;
                    for (let i = 0; i < sel.options.length; i++) {
                        const val = sel.options[i].value.toLowerCase();
                        const m = method.toLowerCase();
                        if (val.includes(m) || m.includes(val) || (m.includes("surface") && val.includes("canal"))) {
                            sel.selectedIndex = i;
                            break;
                        }
                    }
                };
                selectMatching(liveMethod);
                selectMatching(manMethod);
            }
            // Clear once consumed
            sessionStorage.removeItem("lastPrediction");
        }
    } catch (e) {
        console.warn("Pre-fill error:", e);
    }
}

function initIrrigationLocation() {
    const searchBtn = document.getElementById("irrLocSearchBtn");
    const searchInput = document.getElementById("irrLocSearchInput");
    const gpsBtn = document.getElementById("irrLocGpsBtn");

    if (searchBtn && searchInput) {
        searchBtn.addEventListener("click", async () => {
            const query = searchInput.value.trim();
            if (!query) return;
            const container = document.getElementById("irrLocResults");
            container.innerHTML = '<div class="text-muted small py-1">Searching...</div>';

            try {
                const res = await searchLocation(query);
                const locs = res.locations || [];
                if (locs.length === 0) {
                    container.innerHTML = '<div class="alert alert-warning py-1 small">No locations found.</div>';
                    return;
                }
                container.innerHTML = locs.map(loc => `
                    <button type="button" class="btn btn-outline-secondary btn-sm w-100 text-start mb-1" onclick="selectIrrLocation(${loc.latitude}, ${loc.longitude}, '${loc.name}, ${loc.state || loc.country}')">
                        <strong>${loc.name}</strong>, ${loc.state || ''} ${loc.country || ''}
                    </button>
                `).join("");
            } catch (err) {
                container.innerHTML = `<div class="alert alert-danger py-1 small">${err.message}</div>`;
            }
        });
    }

    if (gpsBtn) {
        gpsBtn.addEventListener("click", () => {
            if (!navigator.geolocation) {
                alert("GPS Geolocation is not supported by your browser.");
                return;
            }
            gpsBtn.disabled = true;
            navigator.geolocation.getCurrentPosition(
                (pos) => {
                    selectIrrLocation(pos.coords.latitude, pos.coords.longitude, "My Current Field (GPS)");
                    gpsBtn.disabled = false;
                },
                (err) => {
                    alert("GPS error: " + err.message);
                    gpsBtn.disabled = false;
                }
            );
        });
    }
}

function selectIrrLocation(lat, lon, name) {
    document.getElementById("irrLat").value = lat;
    document.getElementById("irrLon").value = lon;
    document.getElementById("irrLocName").textContent = name;
    document.getElementById("irrLocCoords").textContent = `${lat.toFixed(3)}° N, ${lon.toFixed(3)}° E`;
    const container = document.getElementById("irrLocResults");
    if (container) container.innerHTML = "";
}

/**
 * Handle Tab 1: Live Weather Submit
 */
async function handleLiveSubmit(e) {
    e.preventDefault();
    const btn = document.getElementById("irrLiveSubmitBtn");
    const origHtml = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = `<span class="spinner-border spinner-border-sm me-2"></span>Evaluating Field &amp; Weather...`;

    const crop = document.getElementById("irrCrop").value;
    const stage = document.getElementById("irrGrowthStage").value;
    const soilType = document.getElementById("irrSoilType").value;
    const soilMoisture = parseFloat(document.getElementById("irrSoilMoistureSlider").value) || 25.0;
    const lat = parseFloat(document.getElementById("irrLat").value) || 17.385;
    const lon = parseFloat(document.getElementById("irrLon").value) || 78.487;
    const area = parseFloat(document.getElementById("irrLiveArea").value) || 1.0;
    const method = document.getElementById("irrLiveMethod").value;

    try {
        const payload = {
            crop: crop,
            growth_stage: stage,
            soil_type: soilType,
            soil_moisture: soilMoisture,
            latitude: lat,
            longitude: lon,
            field_area_hectare: area,
            irrigation_type: method,
            irrigation_need: soilMoisture < 30 ? "high" : (soilMoisture < 50 ? "medium" : "low")
        };

        const res = await getWeatherIrrigationRecommendation(payload);
        displayIrrigationResult(res, crop, stage);
    } catch (err) {
        alert("Recommendation error: " + err.message);
    } finally {
        btn.disabled = false;
        btn.innerHTML = origHtml;
    }
}

/**
 * Handle Tab 2: Manual Environment Submit
 */
async function handleManualSubmit(e) {
    e.preventDefault();
    const btn = document.getElementById("irrManualSubmitBtn");
    const origHtml = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = `<span class="spinner-border spinner-border-sm me-2"></span>Processing Decision Matrix...`;

    const crop = document.getElementById("irrCrop").value;
    const stage = document.getElementById("irrGrowthStage").value;
    const soilType = document.getElementById("irrSoilType").value;
    const soilMoisture = parseFloat(document.getElementById("irrSoilMoistureSlider").value) || 25.0;
    const temp = parseFloat(document.getElementById("manTemp").value) || 30.0;
    const humidity = parseFloat(document.getElementById("manHumidity").value) || 50.0;
    const rain = parseFloat(document.getElementById("manRain").value) || 0.0;
    const wind = parseFloat(document.getElementById("manWind").value) || 10.0;
    const sun = parseFloat(document.getElementById("manSun").value) || 7.0;
    const eto = parseFloat(document.getElementById("manEto").value) || 4.5;
    const area = parseFloat(document.getElementById("manArea").value) || 1.0;
    const method = document.getElementById("manMethod").value;

    try {
        const payload = {
            crop: crop,
            growth_stage: stage,
            soil_type: soilType,
            soil_moisture: soilMoisture,
            temperature_c: temp,
            humidity: humidity,
            rainfall_mm: rain,
            wind_speed_kmh: wind,
            sunlight_hours: sun,
            eto_mm_day: eto,
            field_area_hectare: area,
            irrigation_type: method,
            irrigation_need: soilMoisture < 30 ? "high" : (soilMoisture < 50 ? "medium" : "low")
        };

        const res = await predictComplete(payload);
        displayIrrigationResult(res, crop, stage);
    } catch (err) {
        alert("Recommendation error: " + err.message);
    } finally {
        btn.disabled = false;
        btn.innerHTML = origHtml;
    }
}

/**
 * Display Decision Results
 */
function displayIrrigationResult(rawRes, crop, stage) {
    document.getElementById("irrPlaceholder")?.classList.add("d-none");
    const card = document.getElementById("irrResultCard");
    card?.classList.remove("d-none");

    // Unpack nested response structures safely
    const res = rawRes?.irrigation_recommendation || 
                rawRes?.result?.irrigation_recommendation || 
                rawRes?.result || 
                rawRes || {};

    safeSetText("resIrrCropHeader", `${crop} • ${stage}`);

    const priority = String(res.irrigation_priority || "MEDIUM").toUpperCase();
    const prioBadge = document.getElementById("resPriorityBadge");
    const urgencyBox = document.getElementById("resUrgencyBox");
    const urgencyTitle = document.getElementById("resUrgencyTitle");
    const scoreText = document.getElementById("resScoreText");

    // Styling according to priority
    if (priority.includes("HIGH") || priority.includes("CRITICAL")) {
        if (prioBadge) {
            prioBadge.className = "badge-priority priority-high";
            prioBadge.textContent = "CRITICAL / HIGH";
        }
        if (urgencyBox) {
            urgencyBox.style.background = "var(--accent-rose-light)";
            urgencyBox.style.borderColor = "rgba(225, 29, 72, 0.25)";
        }
        if (urgencyTitle) {
            urgencyTitle.textContent = "Urgent Irrigation Needed";
            urgencyTitle.className = "fw-bold text-danger";
        }
        if (scoreText) {
            scoreText.textContent = res.priority_score !== undefined ? `High Priority (${res.priority_score} pts)` : "High Priority";
            scoreText.className = "badge bg-white text-danger border";
        }
    } else if (priority.includes("MED")) {
        if (prioBadge) {
            prioBadge.className = "badge-priority priority-medium";
            prioBadge.textContent = "MEDIUM PRIORITY";
        }
        if (urgencyBox) {
            urgencyBox.style.background = "var(--accent-amber-light)";
            urgencyBox.style.borderColor = "rgba(217, 119, 6, 0.25)";
        }
        if (urgencyTitle) {
            urgencyTitle.textContent = "Irrigate Within 24-48 Hours";
            urgencyTitle.className = "fw-bold text-warning";
        }
        if (scoreText) {
            scoreText.textContent = res.priority_score !== undefined ? `Moderate Priority (${res.priority_score} pts)` : "Moderate Priority";
            scoreText.className = "badge bg-white text-warning border";
        }
    } else {
        if (prioBadge) {
            prioBadge.className = "badge-priority priority-low";
            prioBadge.textContent = "LOW / ADEQUATE";
        }
        if (urgencyBox) {
            urgencyBox.style.background = "var(--primary-light)";
            urgencyBox.style.borderColor = "var(--primary-border)";
        }
        if (urgencyTitle) {
            urgencyTitle.textContent = "Soil Moisture Currently Adequate";
            urgencyTitle.className = "fw-bold text-success";
        }
        if (scoreText) {
            scoreText.textContent = res.priority_score !== undefined ? `Low Priority (${res.priority_score} pts)` : "Low Priority";
            scoreText.className = "badge bg-white text-success border";
        }
    }

    const primaryReason = res.reason || 
                          res.time_reason || 
                          (res.priority_reasons && res.priority_reasons[0]) || 
                          (res.explanation ? res.explanation.split('; ')[0] : null) || 
                          "Soil moisture evaluated against crop growth threshold.";
    safeSetText("resPrimaryReason", primaryReason);

    // Recommended Volume & Pump Runtime
    const volDisplay = res.event_volume_display || 
                       (res.recommended_water_litres !== undefined ? `${Number(res.recommended_water_litres).toLocaleString()} Litres` : "Calculating volume...");
    const pumpDisplay = res.pump_shift_display || 
                        (res.recommended_water_litres === 0 ? "No pumping required" : "Pump runtime evaluating...");

    safeSetText("resIrrVolume", volDisplay);
    safeSetText("resIrrPumpRuntime", `Pump Runtime: ${pumpDisplay}`);

    safeSetText("resTiming", res.recommended_time || "Early Morning (06:00 - 08:30 AM)");
    safeSetText("resTechnique", res.recommended_technique || "Drip / Micro-Irrigation");

    // Factors list
    const factorsList = document.getElementById("resFactorsList");
    if (factorsList) {
        let factors = res.factors || res.priority_reasons;
        if (!factors || !factors.length) {
            if (res.explanation) {
                factors = res.explanation.split("; ").filter(Boolean);
            }
        }
        if (Array.isArray(factors) && factors.length > 0) {
            factorsList.innerHTML = factors.map(f => `<li>${f}</li>`).join("");
        } else {
            factorsList.innerHTML = `
                <li>Root-zone moisture evaluated against FAO threshold</li>
                <li>Evaporative loss minimized via recommended window</li>
            `;
        }
    }

    if (window.innerWidth < 992) {
        card.scrollIntoView({ behavior: "smooth" });
    }
}

function safeSetText(id, val) {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
}

if (typeof window !== "undefined") {
    window.selectIrrLocation = selectIrrLocation;
}
