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
 * Fetch and populate 55 crops with optgroups
 */
async function initCrops() {
    try {
        const res = await getCrops();
        cropsDatabase = res.crops || [];

        const weatherSelect = document.getElementById("weatherCrop");
        const manualSelect = document.getElementById("manualCrop");

        // Group crops by group
        const grouped = {};
        cropsDatabase.forEach(c => {
            const grp = c.crop_group || "General Crops";
            if (!grouped[grp]) grouped[grp] = [];
            grouped[grp].push(c);
        });

        const buildOptionsHtml = (selectedDefault = "Wheat") => {
            let html = '<option value="">Select Crop...</option>';
            for (const grp of Object.keys(grouped).sort()) {
                html += `<optgroup label="${grp}">`;
                grouped[grp].forEach(c => {
                    const sel = c.crop === selectedDefault ? "selected" : "";
                    html += `<option value="${c.crop}" ${sel}>${c.crop}</option>`;
                });
                html += `</optgroup>`;
            }
            return html;
        };

        if (weatherSelect) weatherSelect.innerHTML = buildOptionsHtml("Wheat");
        if (manualSelect) manualSelect.innerHTML = buildOptionsHtml("Wheat");

        updateKcPreview("weather");
        updateKcPreview("manual");
    } catch (e) {
        console.error("Failed to load crops:", e);
    }
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
    btn.innerHTML = `<span class="spinner-border spinner-border-sm me-2"></span>Computing FAO-56 Weather &amp; Water...`;

    const crop = document.getElementById("weatherCrop").value;
    const growthStage = document.getElementById("weatherStage").value;
    const fieldArea = parseFloat(document.getElementById("weatherArea").value) || 1.0;
    const method = document.getElementById("weatherMethod").value;
    const lat = parseFloat(document.getElementById("locLat").value) || 17.385;
    const lon = parseFloat(document.getElementById("locLon").value) || 78.487;

    try {
        const payload = {
            crop: crop,
            growth_stage: growthStage,
            field_area_hectare: fieldArea,
            latitude: lat,
            longitude: lon,
            irrigation_method: method
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
    btn.innerHTML = `<span class="spinner-border spinner-border-sm me-2"></span>Calculating Model Output...`;

    const crop = document.getElementById("manualCrop").value;
    const growthStage = document.getElementById("manualStage").value;
    const fieldArea = parseFloat(document.getElementById("manualArea").value) || 1.0;
    const eto = parseFloat(document.getElementById("manualEto").value) || 4.5;
    const rain = parseFloat(document.getElementById("manualRain").value) || 0.0;
    const method = document.getElementById("manualMethod").value;

    try {
        const payload = {
            crop: crop,
            growth_stage: growthStage,
            field_area_hectare: fieldArea,
            eto_mm_day: eto,
            rainfall_mm: rain,
            irrigation_method: method
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
 * Display Computed Result
 */
function displayResult(pred, weather, eto, payload) {
    lastPredictionResult = { prediction: pred, weather: weather, eto: eto, input: payload };

    document.getElementById("resultPlaceholder")?.classList.add("d-none");
    const resultCard = document.getElementById("resultCard");
    resultCard?.classList.remove("d-none");

    const grossLitres = Number(pred.gross_irrigation_litres || pred.crop_water_requirement_litres || 0);
    const grossMm = Number(pred.gross_irrigation_requirement_mm || pred.crop_water_requirement_mm || 0);
    const netMm = Number(pred.net_irrigation_requirement_mm || pred.crop_water_requirement_mm || 0);
    const rainMm = Number(pred.effective_rainfall_mm || 0);
    const kc = Number(pred.kc || 1.0);
    const etoVal = Number(pred.eto_mm_day || eto?.eto_mm_day || 4.5);
    const method = pred.irrigation_method || payload.irrigation_method || "Drip";
    const area = Number(pred.field_area_hectare || payload.field_area_hectare || 1.0);

    safeSetText("resCropHeader", `${pred.crop || payload.crop} • ${pred.growth_stage || payload.growth_stage}`);
    safeSetText("resMethodBadge", `${method} (${Math.round((pred.irrigation_efficiency || 0.9) * 100)}% Eff)`);
    safeSetText("resGrossLitres", Math.round(grossLitres).toLocaleString());
    safeSetText("resDepthMm", `Gross application depth: ${grossMm.toFixed(2)} mm/day across ${area} ha`);

    safeSetText("resKc", kc.toFixed(2));
    safeSetText("resEto", `${etoVal.toFixed(2)} mm/d`);
    safeSetText("resNetMm", `${netMm.toFixed(2)} mm/d`);
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
