/* ==========================================================================
   WATER PREDICTION CONTROLLER
   Handles dynamic 55-crop loading, Kc preview, location search, and calculation.
   ========================================================================== */

let cropsDatabase = [];
let lastPredictionResult = null;

document.addEventListener("DOMContentLoaded", async () => {
    // 1. Load 55 crops from backend
    await initCrops();

    // 2. Wire up location search & GPS
    initLocationControls();

    // 3. Wire up Kc preview listeners
    initKcListeners();

    // 4. Wire up Weather mode form submit
    const weatherForm = document.getElementById("weatherWaterForm");
    if (weatherForm) {
        weatherForm.addEventListener("submit", handleWeatherWaterSubmit);
    }

    // 5. Wire up Manual mode form submit
    const manualForm = document.getElementById("manualWaterForm");
    if (manualForm) {
        manualForm.addEventListener("submit", handleManualWaterSubmit);
    }

    // 6. Send to irrigation advisor button
    const sendBtn = document.getElementById("sendToIrrigationBtn");
    if (sendBtn) {
        sendBtn.addEventListener("click", () => {
            if (lastPredictionResult) {
                // Save to sessionStorage to pre-fill irrigation page
                sessionStorage.setItem("lastPrediction", JSON.stringify(lastPredictionResult));
                window.location.href = "irrigation_recommendation.html";
            }
        });
    }
});

/**
 * Fetch and populate 55 crops with optgroups and live search filter
 */
async function initCrops() {
    try {
        const res = await getCrops();
        cropsDatabase = res.crops || [];

        const weatherSelect = document.getElementById("weatherCrop");
        const manualSelect = document.getElementById("manualCrop");

        renderCropOptions(weatherSelect, "Wheat");
        renderCropOptions(manualSelect, "Wheat");

        setupCropSearch("weatherCropSearch", "weatherCrop", "weather");
        setupCropSearch("manualCropSearch", "manualCrop", "manual");

        updateKcPreview("weather");
        updateKcPreview("manual");
    } catch (e) {
        console.error("Failed to load crops:", e);
    }
}

function renderCropOptions(selectEl, selectedDefault = "Wheat", filterText = "") {
    if (!selectEl) return;
    const currentVal = selectEl.value || selectedDefault;
    const term = filterText.trim().toLowerCase();

    // Group crops
    const grouped = {};
    cropsDatabase.forEach(c => {
        if (term) {
            const cropMatch = c.crop.toLowerCase().includes(term);
            const displayMatch = (c.display_name || "").toLowerCase().includes(term);
            const groupMatch = (c.crop_group || "").toLowerCase().includes(term);
            const aliasMatch = (c.aliases || []).some(a => a.toLowerCase().includes(term));
            if (!cropMatch && !displayMatch && !groupMatch && !aliasMatch) {
                return;
            }
        }
        const grp = c.crop_group || "General Crops";
        if (!grouped[grp]) grouped[grp] = [];
        grouped[grp].push(c);
    });

    let html = '<option value="">Select Crop...</option>';
    const groupKeys = Object.keys(grouped).sort();

    if (groupKeys.length === 0) {
        html += '<option value="" disabled>No matching crops found</option>';
    } else {
        for (const grp of groupKeys) {
            html += `<optgroup label="${grp}">`;
            grouped[grp].forEach(c => {
                const isSelected = c.crop.toLowerCase() === currentVal.toLowerCase() ? "selected" : "";
                const display = c.display_name || c.crop;
                html += `<option value="${c.crop}" ${isSelected}>${display}</option>`;
            });
            html += `</optgroup>`;
        }
    }

    selectEl.innerHTML = html;

    // If searching and exactly 1 result returned, select it automatically
    if (term && selectEl.options.length === 2 && selectEl.options[1].value) {
        selectEl.selectedIndex = 1;
    }
}

function setupCropSearch(searchId, selectId, mode) {
    const searchInput = document.getElementById(searchId);
    const selectEl = document.getElementById(selectId);
    if (!searchInput || !selectEl) return;

    searchInput.addEventListener("input", (e) => {
        renderCropOptions(selectEl, selectEl.value, e.target.value);
        updateKcPreview(mode);
    });

    searchInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
            e.preventDefault();
            if (selectEl.options.length > 1 && selectEl.options[1].value) {
                selectEl.selectedIndex = 1;
                updateKcPreview(mode);
            }
        }
    });
}

/**
 * Update Kc indicator preview when crop or stage changes
 */
function initKcListeners() {
    const weatherCrop = document.getElementById("weatherCrop");
    const weatherStage = document.getElementById("weatherStage");
    if (weatherCrop && weatherStage) {
        weatherCrop.addEventListener("change", () => updateKcPreview("weather"));
        weatherStage.addEventListener("change", () => updateKcPreview("weather"));
    }

    const manualCrop = document.getElementById("manualCrop");
    const manualStage = document.getElementById("manualStage");
    if (manualCrop && manualStage) {
        manualCrop.addEventListener("change", () => updateKcPreview("manual"));
        manualStage.addEventListener("change", () => updateKcPreview("manual"));
    }
}

function updateKcPreview(mode) {
    const cropName = document.getElementById(`${mode}Crop`)?.value;
    const stage = document.getElementById(`${mode}Stage`)?.value;
    if (!cropName || !stage) return;

    const cropObj = cropsDatabase.find(c => c.crop.toLowerCase() === cropName.toLowerCase());
    if (!cropObj) return;

    let kc = 1.0;
    const s = stage.toLowerCase();
    if (s.includes("sow") || s.includes("init")) kc = cropObj.kc_initial;
    else if (s.includes("veg") || s.includes("dev")) kc = cropObj.kc_development;
    else if (s.includes("flow") || s.includes("mid")) kc = cropObj.kc_mid;
    else if (s.includes("harv") || s.includes("late")) kc = cropObj.kc_late;

    if (mode === "weather") {
        const valElem = document.getElementById("weatherKcVal");
        const grpElem = document.getElementById("weatherCropGroup");
        if (valElem) valElem.textContent = Number(kc).toFixed(2);
        if (grpElem) grpElem.textContent = `Group: ${cropObj.crop_group}`;
    }
}

/**
 * Location controls: Search + GPS
 */
function initLocationControls() {
    const searchBtn = document.getElementById("locSearchBtn");
    const searchInput = document.getElementById("locSearchInput");
    const gpsBtn = document.getElementById("locGpsBtn");

    if (searchBtn && searchInput) {
        searchBtn.addEventListener("click", async () => {
            const query = searchInput.value.trim();
            if (!query) return;
            const container = document.getElementById("locSearchResults");
            container.innerHTML = '<div class="text-muted small py-1">Searching locations...</div>';

            try {
                const res = await searchLocation(query);
                const locs = res.locations || [];
                if (locs.length === 0) {
                    container.innerHTML = '<div class="alert alert-warning py-1 small mb-1">No matching locations found.</div>';
                    return;
                }

                container.innerHTML = locs.map(loc => `
                    <button type="button" class="btn btn-outline-secondary btn-sm w-100 text-start mb-1" onclick="selectLocation(${loc.latitude}, ${loc.longitude}, '${loc.name}, ${loc.state || loc.country}')">
                        <strong>${loc.name}</strong>, ${loc.state || ''} ${loc.country || ''} 
                        <span class="text-muted">(${loc.latitude.toFixed(3)}°, ${loc.longitude.toFixed(3)}°)</span>
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
            gpsBtn.innerHTML = `<span>⏳</span>`;
            navigator.geolocation.getCurrentPosition(
                (pos) => {
                    const lat = pos.coords.latitude;
                    const lon = pos.coords.longitude;
                    selectLocation(lat, lon, "My Current Field (GPS)");
                    gpsBtn.disabled = false;
                    gpsBtn.innerHTML = `<span>📍 GPS</span>`;
                },
                (err) => {
                    alert("GPS error: " + err.message);
                    gpsBtn.disabled = false;
                    gpsBtn.innerHTML = `<span>📍 GPS</span>`;
                }
            );
        });
    }
}

function selectLocation(lat, lon, name) {
    document.getElementById("locLat").value = lat;
    document.getElementById("locLon").value = lon;
    document.getElementById("locSelectedName").textContent = name;
    document.getElementById("locSelectedCoords").textContent = `${lat.toFixed(3)}° N, ${lon.toFixed(3)}° E`;
    const container = document.getElementById("locSearchResults");
    if (container) container.innerHTML = "";
}

/**
 * Handle Tab 1 Form Submit (Weather + Location Mode)
 */
async function handleWeatherWaterSubmit(e) {
    e.preventDefault();
    const btn = document.getElementById("weatherWaterSubmitBtn");
    const origHtml = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = `<span class="spinner-border spinner-border-sm me-2"></span>Computing Real-Time Farmer Plan...`;

    const crop = document.getElementById("weatherCrop").value;
    const growthStage = document.getElementById("weatherStage").value;
    const fieldArea = parseFloat(document.getElementById("weatherArea").value) || 1.0;
    const method = document.getElementById("weatherMethod").value;
    const soil = document.getElementById("weatherSoil")?.value || "Loamy";
    const pumpHp = parseFloat(document.getElementById("weatherPumpHp")?.value) || 5.0;
    const lat = parseFloat(document.getElementById("locLat").value) || 17.385;
    const lon = parseFloat(document.getElementById("locLon").value) || 78.487;

    try {
        const payload = {
            crop: crop,
            growth_stage: growthStage,
            field_area_hectare: fieldArea,
            latitude: lat,
            longitude: lon,
            irrigation_method: method,
            soil_type: soil,
            pump_hp: pumpHp,
            location_name: document.getElementById("locSelectedName")?.textContent || "Field Location"
        };

        const res = await predictWaterFromWeather(payload);
        displayResult(res.prediction, res.weather, res.eto, payload);
    } catch (err) {
        alert("Calculation error: " + err.message);
    } finally {
        btn.disabled = false;
        btn.innerHTML = origHtml;
    }
}

/**
 * Handle Tab 2 Form Submit (Manual Mode)
 */
async function handleManualWaterSubmit(e) {
    e.preventDefault();
    const btn = document.getElementById("manualWaterSubmitBtn");
    const origHtml = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = `<span class="spinner-border spinner-border-sm me-2"></span>Calculating Real-Time Farmer Plan...`;

    const crop = document.getElementById("manualCrop").value;
    const growthStage = document.getElementById("manualStage").value;
    const fieldArea = parseFloat(document.getElementById("manualArea").value) || 1.0;
    const eto = parseFloat(document.getElementById("manualEto").value) || 4.5;
    const rain = parseFloat(document.getElementById("manualRain").value) || 0.0;
    const method = document.getElementById("manualMethod").value;
    const soil = document.getElementById("manualSoil")?.value || "Loamy";
    const pumpHp = parseFloat(document.getElementById("manualPumpHp")?.value) || 5.0;

    try {
        const payload = {
            crop: crop,
            growth_stage: growthStage,
            field_area_hectare: fieldArea,
            eto_mm_day: eto,
            rainfall_mm: rain,
            irrigation_method: method,
            soil_type: soil,
            pump_hp: pumpHp,
            location_name: document.getElementById("locSelectedName")?.textContent || "Field Location"
        };

        const res = await predictWater(payload);
        displayResult(res.prediction || res, null, { eto_mm_day: eto }, payload);
    } catch (err) {
        alert("Calculation error: " + err.message);
    } finally {
        btn.disabled = false;
        btn.innerHTML = origHtml;
    }
}

/**
 * Display Computed Result with Real-Time Farmer Operational Schedule
 */
function displayResult(pred, weather, eto, payload) {
    lastPredictionResult = { prediction: pred, weather: weather, eto: eto, input: payload };

    document.getElementById("resultPlaceholder")?.classList.add("d-none");
    const resultCard = document.getElementById("resultCard");
    resultCard?.classList.remove("d-none");

    const farmer = pred.farmer_usage || {};
    const grossLitres = Number(pred.gross_irrigation_litres || pred.crop_water_requirement_litres || 0);
    const grossMm = Number(pred.gross_irrigation_requirement_mm || pred.crop_water_requirement_mm || 0);
    const rainMm = Number(pred.effective_rainfall_mm || 0);
    const kc = Number(pred.kc || 1.0);
    const etoVal = Number(pred.eto_mm_day || eto?.eto_mm_day || 4.5);
    const method = pred.irrigation_method || payload.irrigation_method || "Sprinkler";
    const area = Number(pred.field_area_hectare || payload.field_area_hectare || 1.0);
    const soilType = farmer.soil_type || payload.soil_type || "Loamy";
    const pumpHp = farmer.pump_hp || payload.pump_hp || 5.0;

    // Real Farmer Operational Values
    const eventVolume = farmer.event_volume_litres || pred.event_volume_litres || (grossLitres * 10);
    const eventGrossDepth = farmer.event_gross_depth_mm || pred.event_gross_depth_mm || 45.0;
    const intervalDisplay = farmer.irrigation_interval_display || pred.irrigation_interval_display || "Every 10 - 14 Days";
    const pumpHours = farmer.pump_hours_per_event || pred.pump_hours_per_event || 10.0;
    const pumpShiftDisplay = farmer.pump_shift_display || pred.pump_shift_display || `~${pumpHours} Hours`;
    const shiftGuidance = farmer.shift_guidance || pred.shift_guidance || "";
    const seasonalSummary = farmer.seasonal_irrigations_summary || pred.seasonal_irrigations_summary || "0 - 2 Irrigations";
    const regime = farmer.irrigation_regime || "Field Crop";
    const criticality = farmer.stage_criticality || "Active Stage";
    const baseGuideline = farmer.farmer_practical_guideline || pred.farmer_practical_guideline || "Check soil moisture before irrigating.";
    const guideline = shiftGuidance ? `${baseGuideline} ⚡ ${shiftGuidance}` : baseGuideline;
    const warning = farmer.danger_warning || pred.danger_warning || "";
    const clarification = farmer.daily_consumption_clarification || pred.daily_consumption_clarification || "";

    // Set Text Values
    safeSetText("resCropHeader", `${pred.crop || payload.crop} • ${pred.growth_stage || payload.growth_stage}`);
    safeSetText("resRegimeBadge", regime);
    safeSetText("resMethodBadge", `${method} (${Math.round((pred.irrigation_efficiency || 0.75) * 100)}% Eff)`);
    safeSetText("resSoilPumpBadge", `${soilType} Soil • ${pumpHp} HP Pump`);
    safeSetText("resCriticalityBadge", criticality.includes("CRITICAL") ? "Critical Stage" : "Normal Stage");

    // Primary Metric: Real Irrigation Event Volume
    safeSetText("resEventVolume", Math.round(eventVolume).toLocaleString());
    safeSetText("resEventDepth", `Gross application depth: ${eventGrossDepth.toFixed(1)} mm across ${area} ha`);

    // Operational Triad
    safeSetText("resInterval", intervalDisplay);
    safeSetText("resPumpHours", pumpShiftDisplay);
    safeSetText("resSeasonalCount", seasonalSummary);

    // Advisory & Warnings
    safeSetText("resWarningText", warning);
    safeSetText("resGuidelineText", guideline);
    safeSetText("resDailyClarification", clarification);

    // Atmospheric Reference Stats
    safeSetText("resGrossLitres", `${Math.round(grossLitres).toLocaleString()} L/d`);
    safeSetText("resDepthMm", `${grossMm.toFixed(2)} mm/day gross`);
    safeSetText("resKc", kc.toFixed(2));
    safeSetText("resEto", `${etoVal.toFixed(2)} mm/d`);
    safeSetText("resRainMm", `${rainMm.toFixed(2)} mm/d`);

    const minFao = pred.reference_water_min_mm ? `${pred.reference_water_min_mm} mm` : "--";
    const maxFao = pred.reference_water_max_mm ? `${pred.reference_water_max_mm} mm` : "--";
    safeSetText("resFaoRange", `${minFao} - ${maxFao}`);

    // Smooth scroll to result on mobile
    if (window.innerWidth < 992) {
        resultCard.scrollIntoView({ behavior: "smooth" });
    }
}

function safeSetText(id, val) {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
}

if (typeof window !== "undefined") {
    window.selectLocation = selectLocation;
}
