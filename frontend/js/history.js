/* ==========================================================================
   HISTORY CONTROLLER
   Search, filter, export, inspect, and delete prediction records.
   ========================================================================== */

let allHistoryRecords = [];
let currentFilterType = "all";
let currentSearchTerm = "";
let detailModalInstance = null;

document.addEventListener("DOMContentLoaded", async () => {
    // 1. Initialize modal instance
    const modalEl = document.getElementById("recordDetailModal");
    if (modalEl && typeof bootstrap !== "undefined") {
        detailModalInstance = new bootstrap.Modal(modalEl);
    }

    // 2. Fetch history records
    await loadHistory();

    // 3. Search input listener
    const searchInput = document.getElementById("historySearchInput");
    if (searchInput) {
        searchInput.addEventListener("input", (e) => {
            currentSearchTerm = e.target.value.trim().toLowerCase();
            renderHistoryTable();
        });
    }

    // 4. Filter pill listeners
    const pills = document.querySelectorAll(".filter-pill");
    pills.forEach(pill => {
        pill.addEventListener("click", () => {
            pills.forEach(p => p.classList.remove("active"));
            pill.classList.add("active");
            currentFilterType = pill.getAttribute("data-type") || "all";
            renderHistoryTable();
        });
    });

    // 5. Refresh button
    const refreshBtn = document.getElementById("refreshHistoryBtn");
    if (refreshBtn) {
        refreshBtn.addEventListener("click", async () => {
            refreshBtn.disabled = true;
            refreshBtn.innerHTML = `<span class="spinner-border spinner-border-sm me-1"></span>Refreshing...`;
            await loadHistory();
            refreshBtn.disabled = false;
            refreshBtn.innerHTML = `<span>🔄 Refresh</span>`;
        });
    }

    // 6. CSV Export button
    const csvBtn = document.getElementById("exportCsvBtn");
    if (csvBtn) {
        csvBtn.addEventListener("click", exportCsv);
    }

    // 7. JSON Export button
    const jsonBtn = document.getElementById("exportJsonBtn");
    if (jsonBtn) {
        jsonBtn.addEventListener("click", exportJson);
    }
});

/**
 * Fetch records from API
 */
async function loadHistory() {
    try {
        const res = await getAllHistory(100);
        allHistoryRecords = res.history || [];
        renderHistoryTable();
    } catch (e) {
        console.error("Failed to load history:", e);
        const tbody = document.getElementById("historyTableBody");
        if (tbody) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="8" class="text-center py-4 text-danger">
                        Failed to retrieve records: ${e.message}
                    </td>
                </tr>
            `;
        }
    }
}

/**
 * Filter and render table
 */
function renderHistoryTable() {
    const tbody = document.getElementById("historyTableBody");
    const countLabel = document.getElementById("recordCountLabel");
    if (!tbody) return;

    // Filter by type
    let filtered = allHistoryRecords.filter(rec => {
        if (currentFilterType === "all") return true;
        const type = String(rec.prediction_type || "").toLowerCase();
        if (currentFilterType === "water") return type.includes("water");
        if (currentFilterType === "irrigation") return type.includes("irrigation");
        if (currentFilterType === "complete") return type.includes("complete");
        return true;
    });

    // Filter by search query
    if (currentSearchTerm) {
        filtered = filtered.filter(rec => {
            const inp = JSON.stringify(rec.input || "").toLowerCase();
            const res = JSON.stringify(rec.result || "").toLowerCase();
            const type = String(rec.prediction_type || "").toLowerCase();
            return inp.includes(currentSearchTerm) || res.includes(currentSearchTerm) || type.includes(currentSearchTerm);
        });
    }

    if (countLabel) {
        countLabel.textContent = `Showing ${filtered.length} of ${allHistoryRecords.length} records`;
    }

    if (filtered.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="8" class="text-center py-5 text-muted">
                    <div class="fs-4 mb-2">📋</div>
                    <strong>No records match your criteria.</strong><br>
                    <span class="small">Try adjusting search terms or generate a new prediction.</span>
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = filtered.map(rec => {
        const inp = rec.input || {};
        const res = rec.result?.water_requirement || rec.result?.water_prediction || rec.result || {};
        const irr = rec.result?.irrigation_recommendation || rec.result || {};

        const crop = res.crop || inp.crop || "Custom Field";
        const stage = res.growth_stage || inp.growth_stage || "--";
        const area = inp.field_area_hectare ? `${inp.field_area_hectare} ha` : "--";

        const litres = Number(res.crop_water_requirement_litres || res.gross_irrigation_litres || 0);
        const litresFormatted = litres > 0 ? Math.round(litres).toLocaleString() : "--";

        // Date
        let dateStr = "--";
        if (rec.created_at) {
            try {
                const d = new Date(rec.created_at);
                dateStr = d.toLocaleDateString("en-US", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
            } catch (e) {}
        }

        // Type badge
        const typeStr = String(rec.prediction_type || "water").replace("_", " ");
        let typeBadge = `<span class="badge bg-light text-dark border">${typeStr}</span>`;
        if (typeStr.includes("complete")) {
            typeBadge = `<span class="badge bg-success-subtle text-success border border-success-subtle">Complete</span>`;
        } else if (typeStr.includes("irrigation")) {
            typeBadge = `<span class="badge bg-info-subtle text-info border border-info-subtle">Irrigation</span>`;
        }

        // Priority
        const prio = String(irr.irrigation_priority || "").toUpperCase();
        let prioBadge = `<span class="badge-priority priority-low">LOW</span>`;
        if (prio.includes("HIGH") || prio.includes("CRITICAL")) {
            prioBadge = `<span class="badge-priority priority-high">HIGH</span>`;
        } else if (prio.includes("MED")) {
            prioBadge = `<span class="badge-priority priority-medium">MED</span>`;
        } else if (!prio) {
            prioBadge = `<span class="text-muted small">N/A</span>`;
        }

        return `
            <tr>
                <td class="text-nowrap small text-muted">${dateStr}</td>
                <td>${typeBadge}</td>
                <td class="fw-bold text-dark">${crop}</td>
                <td><span class="badge bg-light text-secondary">${stage}</span></td>
                <td>${area}</td>
                <td class="fw-bold text-success">${litresFormatted}</td>
                <td>${prioBadge}</td>
                <td class="text-end text-nowrap">
                    <button class="btn btn-sm btn-outline-custom py-1 px-2 me-1" onclick="viewRecord('${rec.id}')">
                        Inspect
                    </button>
                    <button class="btn btn-sm btn-outline-danger py-1 px-2" onclick="deleteHistoryItem('${rec.id}')">
                        ✕
                    </button>
                </td>
            </tr>
        `;
    }).join("");
}

/**
 * View detailed record in modal
 */
function viewRecord(id) {
    const rec = allHistoryRecords.find(r => r.id === id);
    if (!rec) return;

    const modalTitle = document.getElementById("modalTitle");
    const modalContent = document.getElementById("modalContent");
    if (!modalContent) return;

    const crop = rec.result?.crop || rec.input?.crop || "Field Assessment";
    const type = rec.prediction_type || "Model Run";
    if (modalTitle) modalTitle.textContent = `${crop} • ${type.toUpperCase()}`;

    modalContent.innerHTML = `
        <div class="mb-3">
            <h6 class="fw-bold text-success">Input Parameters</h6>
            <pre class="bg-light p-3 rounded small text-dark border">${JSON.stringify(rec.input, null, 2)}</pre>
        </div>
        <div class="mb-3">
            <h6 class="fw-bold text-primary">Calculation &amp; Model Output</h6>
            <pre class="bg-light p-3 rounded small text-dark border">${JSON.stringify(rec.result, null, 2)}</pre>
        </div>
        <div class="d-flex justify-content-between text-muted small">
            <span>Record ID: <code>${rec.id}</code></span>
            <span>Recorded: ${rec.created_at || "Recent"}</span>
        </div>
    `;

    if (detailModalInstance) {
        detailModalInstance.show();
    }
}

/**
 * Delete a history record
 */
async function deleteHistoryItem(id) {
    if (!confirm("Are you sure you want to delete this historical record?")) return;

    try {
        await deleteHistoryRecord(id);
        allHistoryRecords = allHistoryRecords.filter(r => r.id !== id);
        renderHistoryTable();
    } catch (e) {
        alert("Failed to delete record: " + e.message);
    }
}

/**
 * Export records to CSV
 */
function exportCsv() {
    if (allHistoryRecords.length === 0) {
        alert("No records to export.");
        return;
    }

    const headers = ["ID", "Date", "Type", "Crop", "Growth_Stage", "Field_Area_ha", "Water_Gross_Litres", "Water_Net_mm", "Priority"];
    const rows = allHistoryRecords.map(r => {
        const inp = r.input || {};
        const res = r.result?.water_requirement || r.result?.water_prediction || r.result || {};
        const irr = r.result?.irrigation_recommendation || r.result || {};

        return [
            r.id,
            r.created_at || "",
            r.prediction_type || "",
            res.crop || inp.crop || "",
            res.growth_stage || inp.growth_stage || "",
            inp.field_area_hectare || "",
            res.gross_irrigation_litres || res.crop_water_requirement_litres || "",
            res.net_irrigation_requirement_mm || res.crop_water_requirement_mm || "",
            irr.irrigation_priority || ""
        ].map(val => `"${String(val).replace(/"/g, '""')}"`).join(",");
    });

    const csvContent = [headers.join(","), ...rows].join("\n");
    downloadBlob(csvContent, "crop_water_history.csv", "text/csv;charset=utf-8;");
}

/**
 * Export records to JSON
 */
function exportJson() {
    if (allHistoryRecords.length === 0) {
        alert("No records to export.");
        return;
    }
    const jsonStr = JSON.stringify(allHistoryRecords, null, 2);
    downloadBlob(jsonStr, "crop_water_history.json", "application/json");
}

function downloadBlob(content, filename, type) {
    const blob = new Blob([content], { type: type });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

if (typeof window !== "undefined") {
    window.viewRecord = viewRecord;
    window.deleteHistoryItem = deleteHistoryItem;
}
