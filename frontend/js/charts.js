/* ==========================================================================
   CHARTS MODULE - CHART.JS VISUALIZATIONS
   Generates clean, interactive charts for agricultural decision metrics
   ========================================================================== */

let waterChartInstance = null;
let priorityChartInstance = null;
let trendChartInstance = null;

// Chart.js default styling
if (typeof Chart !== "undefined") {
    Chart.defaults.font.family = "'Inter', sans-serif";
    Chart.defaults.color = "#64748b";
}

/**
 * 1. Water Requirement Bar Chart by Crop
 */
function createWaterChart(records) {
    const canvas = document.getElementById("waterChart");
    if (!canvas || typeof Chart === "undefined") return;

    if (waterChartInstance) {
        waterChartInstance.destroy();
    }

    // Filter relevant records
    const validRecords = (records || []).filter(r => {
        const type = String(r.prediction_type || "").toLowerCase();
        return type.includes("water") || type === "complete";
    }).slice(0, 8).reverse();

    if (validRecords.length === 0) {
        // Fallback default sample data if no records yet
        renderEmptyChartState(canvas, "No prediction data available yet.");
        return;
    }

    const labels = [];
    const waterMm = [];
    const waterLitres = [];

    validRecords.forEach((r, idx) => {
        const res = r.result?.water_requirement || r.result?.water_prediction || r.result || {};
        const inp = r.input || {};
        const crop = res.crop || inp.crop || `Crop #${idx + 1}`;
        const mm = Number(res.crop_water_requirement_mm || res.net_irrigation_requirement_mm || 0);
        const litres = Number(res.crop_water_requirement_litres || res.gross_irrigation_litres || 0);

        labels.push(crop);
        waterMm.push(roundTo(mm, 2));
        waterLitres.push(roundTo(litres, 0));
    });

    waterChartInstance = new Chart(canvas, {
        type: "bar",
        data: {
            labels: labels,
            datasets: [
                {
                    label: "Crop Water Need (mm/day)",
                    data: waterMm,
                    backgroundColor: "rgba(5, 150, 105, 0.85)",
                    borderColor: "#059669",
                    borderWidth: 1.5,
                    borderRadius: 6,
                    yAxisID: "y"
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: "top", labels: { boxWidth: 12, font: { weight: "600" } } },
                tooltip: {
                    callbacks: {
                        afterLabel: function(ctx) {
                            const lit = waterLitres[ctx.dataIndex];
                            return lit ? `Total: ${lit.toLocaleString()} Litres` : "";
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: { display: true, text: "mm / day", font: { weight: "600" } },
                    grid: { color: "#f1f5f9" }
                },
                x: {
                    grid: { display: false }
                }
            }
        }
    });
}

/**
 * 2. Irrigation Priority Distribution Doughnut Chart
 */
function createPriorityChart(records) {
    const canvas = document.getElementById("priorityChart");
    if (!canvas || typeof Chart === "undefined") return;

    if (priorityChartInstance) {
        priorityChartInstance.destroy();
    }

    let highCount = 0;
    let mediumCount = 0;
    let lowCount = 0;

    (records || []).forEach(r => {
        const res = r.result?.irrigation_recommendation || r.result || {};
        const prio = String(res.irrigation_priority || "").toUpperCase();
        if (prio.includes("HIGH") || prio.includes("CRITICAL")) {
            highCount++;
        } else if (prio.includes("MED")) {
            mediumCount++;
        } else if (prio.includes("LOW") || prio.includes("NONE")) {
            lowCount++;
        }
    });

    // Provide baseline representation if zero irrigation records yet
    const hasData = (highCount + mediumCount + lowCount) > 0;
    const dataCounts = hasData ? [highCount, mediumCount, lowCount] : [1, 2, 3];
    const bgColors = hasData ? ["#e11d48", "#d97706", "#059669"] : ["#f1f5f9", "#e2e8f0", "#cbd5e1"];

    priorityChartInstance = new Chart(canvas, {
        type: "doughnut",
        data: {
            labels: hasData ? ["High / Critical", "Medium", "Low / Adequate"] : ["No data yet", "", ""],
            datasets: [{
                data: dataCounts,
                backgroundColor: bgColors,
                borderWidth: 2,
                borderColor: "#ffffff"
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: "70%",
            plugins: {
                legend: {
                    position: "bottom",
                    labels: { boxWidth: 12, padding: 16, font: { weight: "600" } }
                }
            }
        }
    });
}

function renderEmptyChartState(canvas, message) {
    const ctx = canvas.getContext("2d");
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.font = "14px Inter, sans-serif";
    ctx.fillStyle = "#94a3b8";
    ctx.textAlign = "center";
    ctx.fillText(message, canvas.width / 2, canvas.height / 2);
}

function roundTo(num, decimals) {
    const factor = Math.pow(10, decimals);
    return Math.round(num * factor) / factor;
}

if (typeof window !== "undefined") {
    window.createWaterChart = createWaterChart;
    window.createPriorityChart = createPriorityChart;
}
