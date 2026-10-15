/**
 * FoodBridge - Main Application Logic & Event Handlers
 * Glues API, UI, Real-time state transitions, AI preview, and Modals together.
 */

// Sample Demo Image URLs
const DEMO_IMAGES = {
    buffet: "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=600",
    biryani: "https://images.unsplash.com/photo-1563379091339-03b21ab4a4f8?w=600",
    bakery: "https://images.unsplash.com/photo-1509440159596-0249088772ff?w=600",
    packaged: "https://images.unsplash.com/photo-1528735602780-2552fd46c7af?w=600"
};

let currentSelectedImage = DEMO_IMAGES.buffet;
let isVlmVerifying = false;

// --- DOM Initializer ---
document.addEventListener("DOMContentLoaded", async () => {
    // Set default deadline to now + 3 hours in input
    const deadlineInput = document.getElementById("food-deadline");
    if (deadlineInput) {
        const d = new Date();
        d.setHours(d.getHours() + 3);
        deadlineInput.value = d.toISOString().slice(0, 16);
    }

    const reqDeadlineInput = document.getElementById("req-deadline");
    if (reqDeadlineInput) {
        const d = new Date();
        d.setHours(d.getHours() + 4);
        reqDeadlineInput.value = d.toISOString().slice(0, 16);
    }

    // Set initial sample image
    useSampleImage('buffet');

    // Load initial data
    await refreshAllData();

    // Auto-refresh state every 15 seconds
    setInterval(refreshAllData, 15000);
});

// --- Tab Navigation ---
function switchTab(tabId) {
    document.querySelectorAll(".tab-btn").forEach(btn => {
        btn.classList.toggle("active", btn.dataset.tab === tabId);
    });

    document.querySelectorAll(".tab-content").forEach(content => {
        content.classList.toggle("active", content.id === tabId);
    });

    if (tabId === "map-tab") {
        initFoodBridgeMap();
        setTimeout(initFoodBridgeMap, 150);
        setTimeout(initFoodBridgeMap, 400);
    }
}

// --- Active Persona Switching ---
function switchPersona(personaKey) {
    FoodBridgeState.currentPersona = personaKey;
    const [role, idStr] = personaKey.split("_");
    const id = parseInt(idStr, 10);

    const personaMap = {
        donor_1: { id: 1, role: "donor", name: "The Grand Palace Hotel", address: "MG Road, Bengaluru", lat: 12.9716, lng: 77.5946 },
        donor_2: { id: 2, role: "donor", name: "Royal Feast Caterers", address: "Indiranagar, Bengaluru", lat: 12.9784, lng: 77.6408 },
        donor_4: { id: 4, role: "donor", name: "Artisan Bakery & Cafe", address: "Koramangala, Bengaluru", lat: 12.9352, lng: 77.6245 },
        ngo_5: { id: 5, role: "ngo", name: "Hope & Care Shelter", address: "Shanti Nagar, Bengaluru", lat: 12.9568, lng: 77.5983 },
        ngo_6: { id: 6, role: "ngo", name: "Annapurna Seva Trust", address: "Domlur, Bengaluru", lat: 12.9609, lng: 77.6387 },
        ngo_7: { id: 7, role: "ngo", name: "Care For All Children", address: "HSR Layout, Bengaluru", lat: 12.9116, lng: 77.6465 },
        vol_8: { id: 8, role: "volunteer", name: "Rahul Sharma", vehicle: "🚴 Bike / EV Rescuer" },
        vol_9: { id: 9, role: "volunteer", name: "Priya Verma", vehicle: "🛵 EV Scooter Rescuer" },
        vol_10: { id: 10, role: "volunteer", name: "Arun Kumar", vehicle: "🚐 Van / Cargo Rescuer" }
    };

    FoodBridgeState.currentUser = personaMap[personaKey] || personaMap.donor_1;

    // Switch tab automatically based on persona role
    if (role === "donor") {
        switchTab("donor-tab");
    } else if (role === "ngo") {
        switchTab("ngo-tab");
    } else if (role === "vol") {
        switchTab("volunteer-tab");
        const volNameEl = document.getElementById("vol-active-name");
        const volVehEl = document.getElementById("vol-vehicle-type");
        if (volNameEl) volNameEl.textContent = FoodBridgeState.currentUser.name;
        if (volVehEl) volVehEl.textContent = FoodBridgeState.currentUser.vehicle || "🚴 Bike Rescuer";
    }

    showToast(`Switched persona to ${FoodBridgeState.currentUser.name} (${role.toUpperCase()})`, "info");
    refreshAllData();
}

// --- Data Refresh Master ---
async function refreshAllData() {
    try {
        const [listings, reqs, tasks, stats, notifs] = await Promise.all([
            FoodBridgeAPI.getListings(),
            FoodBridgeAPI.getRequirements(),
            FoodBridgeAPI.getVolunteerTasks(),
            FoodBridgeAPI.getImpactStats(),
            FoodBridgeAPI.getNotifications()
        ]);

        renderDonorListings(listings);
        renderNgoRequirements(reqs);
        renderNgoRecommendations();
        renderVolunteerTasks(tasks);
        renderImpactStats(stats);
        renderNotifications(notifs);

        if (foodBridgeMap) {
            renderAllMapEntities();
        }
    } catch (e) {
        console.error("Data refresh error:", e);
    }
}

// --- Image Selection & Sample Presets ---
function useSampleImage(presetKey) {
    const url = DEMO_IMAGES[presetKey];
    if (!url) return;

    currentSelectedImage = url;
    const previewContainer = document.getElementById("image-preview-container");
    const placeholder = document.getElementById("upload-placeholder");
    const previewImg = document.getElementById("image-preview-img");

    if (previewImg && previewContainer && placeholder) {
        previewImg.src = url;
        previewContainer.classList.remove("hidden");
        placeholder.classList.add("hidden");
    }

    triggerLiveVlmCheck(url);
}

function handleImageSelection(event) {
    const file = event.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = function(e) {
        const previewContainer = document.getElementById("image-preview-container");
        const placeholder = document.getElementById("upload-placeholder");
        const previewImg = document.getElementById("image-preview-img");

        previewImg.src = e.target.result;
        currentSelectedImage = file;
        previewContainer.classList.remove("hidden");
        placeholder.classList.add("hidden");

        triggerLiveVlmCheck(file);
    };
    reader.readAsDataURL(file);
}

function removeSelectedImage() {
    currentSelectedImage = null;
    const previewContainer = document.getElementById("image-preview-container");
    const placeholder = document.getElementById("upload-placeholder");
    const fileInput = document.getElementById("food-image-file");

    if (fileInput) fileInput.value = "";
    if (previewContainer) previewContainer.classList.add("hidden");
    if (placeholder) placeholder.classList.remove("hidden");

    const vlmBody = document.getElementById("vlm-body-content");
    if (vlmBody) {
        vlmBody.innerHTML = `<p class="vlm-status-text"><i class="fa-solid fa-camera"></i> Please upload or select an image to verify.</p>`;
    }
}

// --- AI VLM Preview Trigger ---
async function triggerLiveVlmCheck(imgFileOrUrl) {
    const vlmBody = document.getElementById("vlm-body-content");
    if (!vlmBody) return;

    vlmBody.innerHTML = `
        <p class="vlm-status-text" style="color: #60a5fa;">
            <i class="fa-solid fa-circle-notch fa-spin"></i> Ollama VLM analyzing image for bulk surplus signatures...
        </p>
    `;

    const foodType = document.getElementById("food-type")?.value || "Cooked Meals";
    const notes = document.getElementById("food-notes")?.value || "";

    const formData = new FormData();
    formData.append("food_type", foodType);
    formData.append("notes", notes);

    if (imgFileOrUrl instanceof File) {
        formData.append("image", imgFileOrUrl);
    } else {
        formData.append("image_url", imgFileOrUrl);
    }

    const res = await FoodBridgeAPI.verifyImagePreview(formData);

    if (res && res.is_bulk) {
        vlmBody.innerHTML = `
            <div style="font-size: 0.82rem;">
                <span class="vlm-verified-badge"><i class="fa-solid fa-circle-check"></i> Bulk Surplus Verified (${Math.round(res.confidence * 100)}% Confidence)</span>
                <p style="color: #cbd5e1; margin-top: 3px;">${res.reason}</p>
                <div style="font-size: 0.72rem; color: #94a3b8; margin-top: 4px;">
                    <strong>Packaging:</strong> ${res.packaging_type || "Catering Vessels"} • <strong>Items:</strong> ${(res.detected_items || []).join(", ")}
                </div>
            </div>
        `;
    } else {
        vlmBody.innerHTML = `
            <div style="font-size: 0.82rem; color: #f87171;">
                <i class="fa-solid fa-triangle-exclamation"></i> Low confidence for bulk commercial surplus. Please check portion scale.
            </div>
        `;
    }
}

// --- Dynamic Urgency Score Preview ---
function updateLiveUrgencyPreview() {
    const foodType = document.getElementById("food-type")?.value || "Cooked Meals";
    const qty = parseFloat(document.getElementById("food-qty")?.value || 25);
    const deadlineVal = document.getElementById("food-deadline")?.value;
    const notes = document.getElementById("food-notes")?.value || "";

    // Update meal equiv helper
    const helper = document.getElementById("meal-equiv-helper");
    if (helper) {
        const factor = foodType === "Dairy Products" ? 4.0 : 3.0;
        const meals = Math.round(qty * factor);
        helper.textContent = `≈ ${meals} meal-equivalents`;
    }

    // Dynamic heuristic preview calculation
    let hoursRemaining = 2.5;
    if (deadlineVal) {
        const diffMs = new Date(deadlineVal) - new Date();
        hoursRemaining = Math.max(0.2, diffMs / (1000 * 3600));
    }

    let timeScore = hoursRemaining <= 1.0 ? 38 : (hoursRemaining <= 2.5 ? 32 : 20);
    let perishScore = foodType === "Cooked Meals" ? 25 : (foodType === "Bakery Items" ? 16 : 12);
    let weatherScore = 12; // Average ambient Bengaluru
    let qtyScore = qty >= 25 ? 9 : 6;
    let freshScore = notes.toLowerCase().includes("warm") || notes.toLowerCase().includes("sealed") ? 9 : 6;

    let total = Math.min(99, Math.max(20, Math.round(timeScore + perishScore + weatherScore + qtyScore + freshScore)));

    const scoreNum = document.getElementById("live-score-val");
    const progressFill = document.getElementById("score-progress");
    const scorePill = document.getElementById("score-pill");

    if (scoreNum) scoreNum.textContent = total;
    if (progressFill) progressFill.style.width = `${total}%`;

    if (scorePill) {
        if (total >= 85) {
            scorePill.style.color = "#ef4444";
            scorePill.style.borderColor = "#ef4444";
            scorePill.style.backgroundColor = "rgba(239, 68, 68, 0.15)";
        } else if (total >= 70) {
            scorePill.style.color = "#f59e0b";
            scorePill.style.borderColor = "#f59e0b";
            scorePill.style.backgroundColor = "rgba(245, 158, 11, 0.15)";
        } else {
            scorePill.style.color = "#10b981";
            scorePill.style.borderColor = "#10b981";
            scorePill.style.backgroundColor = "rgba(16, 185, 129, 0.15)";
        }
    }
}

// --- Handle Donor Post Form Submission ---
async function handleDonorSubmit(event) {
    event.preventDefault();

    const title = document.getElementById("food-title").value.trim();
    const foodType = document.getElementById("food-type").value;
    const quantityKg = parseFloat(document.getElementById("food-qty").value);
    const address = document.getElementById("food-address").value.trim();
    const deadlineRaw = document.getElementById("food-deadline").value;
    const notes = document.getElementById("food-notes").value.trim();
    const submitBtn = document.getElementById("btn-submit-donation");

    if (!title || !quantityKg || !address || !deadlineRaw) {
        showToast("Please fill all required fields.", "error");
        return;
    }

    submitBtn.disabled = true;
    submitBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Verifying with AI & Publishing...`;

    try {
        const formData = new FormData();
        formData.append("donor_id", FoodBridgeState.currentUser.id || 1);
        formData.append("donor_name", FoodBridgeState.currentUser.name || "The Grand Palace Hotel");
        formData.append("title", title);
        formData.append("food_type", foodType);
        formData.append("quantity_kg", quantityKg);
        formData.append("address", address);
        formData.append("lat", FoodBridgeState.currentUser.lat || 12.9716);
        formData.append("lng", FoodBridgeState.currentUser.lng || 77.5946);
        formData.append("pickup_deadline", deadlineRaw.replace("T", " ") + ":00");
        formData.append("notes", notes);

        if (currentSelectedImage instanceof File) {
            formData.append("image", currentSelectedImage);
        } else {
            formData.append("image_url", currentSelectedImage || DEMO_IMAGES.buffet);
        }

        const res = await FoodBridgeAPI.createListing(formData);

        showToast(`🎉 Surplus food published! Quality score: ${res.quality_score}/100 (~${res.meal_equivalent} meals)`, "success");

        // Reset form
        document.getElementById("donor-form").reset();
        useSampleImage('buffet');
        updateLiveUrgencyPreview();

        await refreshAllData();
    } catch (e) {
        showToast("Failed to publish surplus food.", "error");
        console.error(e);
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = `<i class="fa-solid fa-paper-plane"></i> Publish Surplus Food to Bridge`;
    }
}

// --- Render Donor Listings ---
function renderDonorListings(listings) {
    const container = document.getElementById("donor-listings-container");
    if (!container) return;

    if (!listings || listings.length === 0) {
        container.innerHTML = `<div class="loader-box">No surplus food listings found.</div>`;
        return;
    }

    const filtered = listings.filter(l => {
        if (FoodBridgeState.activeFilter === "available") return l.status === "available";
        if (FoodBridgeState.activeFilter === "matched") return l.status !== "available";
        return true;
    });

    container.innerHTML = filtered.map(l => {
        let badgeClass = "badge-normal";
        let badgeLabel = "🟢 Standard";
        if (l.quality_score >= 85) {
            badgeClass = "badge-urgent";
            badgeLabel = "🔴 Urgent";
        } else if (l.quality_score >= 70) {
            badgeClass = "badge-high";
            badgeLabel = "🟠 High Priority";
        }

        const statusBadges = {
            available: `<span class="badge badge-normal">Available for Matching</span>`,
            ngo_accepted: `<span class="badge badge-status">NGO Accepted</span>`,
            volunteer_assigned: `<span class="badge badge-status">Volunteer En Route</span>`,
            picked_up: `<span class="badge badge-high">Picked Up</span>`,
            delivered: `<span class="badge badge-normal">Delivered</span>`,
            confirmed: `<span class="badge badge-normal">✅ Verified Rescued</span>`
        };

        const vlmReason = l.ai_verification?.reason || "Bulk catering scale verified by Vision Engine.";

        return `
            <div class="listing-card">
                <div class="listing-card-body">
                    <img class="listing-thumb" src="${l.image_url || DEMO_IMAGES.buffet}" alt="${l.title}">
                    <div class="listing-info">
                        <div class="listing-top">
                            <h4 class="listing-title">${l.title}</h4>
                            <span class="badge ${badgeClass}">${badgeLabel} (${l.quality_score}/100)</span>
                        </div>
                        <div class="listing-meta">
                            <span><i class="fa-solid fa-weight-hanging text-gold"></i> <strong>${l.quantity_kg} kg</strong> (~${l.meal_equivalent} meals)</span>
                            <span><i class="fa-solid fa-location-dot"></i> ${l.address}</span>
                            <span><i class="fa-solid fa-clock"></i> Deadline: ${l.pickup_deadline}</span>
                        </div>
                        <div style="font-size: 0.76rem; color: #94a3b8; background: rgba(0,0,0,0.2); padding: 4px 8px; border-radius: 6px; margin-bottom: 6px;">
                            <i class="fa-solid fa-robot" style="color: #60a5fa;"></i> <strong>AI Audit:</strong> ${vlmReason}
                        </div>
                        <div style="display: flex; align-items: center; justify-content: space-between;">
                            ${statusBadges[l.status] || `<span class="badge">${l.status}</span>`}
                            <button class="btn btn-chip" onclick="openMatchModalForListing(${l.id})">
                                <i class="fa-solid fa-wand-magic-sparkles"></i> View Algorithm Matches
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }).join("");
}

function filterListings(filterType) {
    FoodBridgeState.activeFilter = filterType;
    document.querySelectorAll(".pill-btn").forEach(btn => {
        btn.classList.toggle("active", btn.textContent.toLowerCase() === filterType);
    });
    renderDonorListings(FoodBridgeState.listings);
}

// --- Render NGO Requirements & Recommendations ---
function renderNgoRequirements(reqs) {
    const container = document.getElementById("ngo-requirements-container");
    if (!container) return;

    if (!reqs || reqs.length === 0) {
        container.innerHTML = `<div class="loader-box">No active NGO requirements.</div>`;
        return;
    }

    container.innerHTML = reqs.map(r => `
        <div class="match-card">
            <div class="match-card-top">
                <div>
                    <h4 style="font-size: 1rem; font-weight: 700;">${r.ngo_name}</h4>
                    <span style="font-size: 0.78rem; color: #94a3b8;">📍 ${r.address} • Deadline: ${r.deadline}</span>
                </div>
                <span class="badge badge-status">${r.status.toUpperCase()}</span>
            </div>
            <div style="margin: 0.5rem 0; font-size: 0.85rem;">
                <strong>Requirement:</strong> ~${r.meals_required} meals (${r.food_type})
                <p style="font-size: 0.78rem; color: #cbd5e1; margin-top: 2px;">${r.notes || "Standard community shelter requirement"}</p>
            </div>
            <button class="btn btn-secondary btn-block" onclick="findMatchesForRequirement(${r.id})">
                <i class="fa-solid fa-magnifying-glass"></i> Find Matched Surplus Food
            </button>
        </div>
    `).join("");
}

async function renderNgoRecommendations() {
    const container = document.getElementById("ngo-recommendations-container");
    if (!container) return;

    const ngoId = FoodBridgeState.currentUser.id || 5;
    const matchesData = await FoodBridgeAPI.getMatchesForNgo(ngoId);

    let candidateMatches = [];
    if (Array.isArray(matchesData)) {
        if (matchesData.length > 0 && matchesData[0].matches) {
            candidateMatches = matchesData[0].matches;
        } else if (matchesData.matches) {
            candidateMatches = matchesData.matches;
        }
    } else if (matchesData && matchesData.matches) {
        candidateMatches = matchesData.matches;
    }

    // Update match count badge
    const countBadge = document.getElementById("active-matches-count");
    if (countBadge) countBadge.textContent = candidateMatches.length;

    if (!candidateMatches || candidateMatches.length === 0) {
        container.innerHTML = `<div class="loader-box">No surplus matches currently within radius.</div>`;
        return;
    }

    container.innerHTML = candidateMatches.map(m => {
        const l = m.listing;
        return `
            <div class="match-card">
                <div class="match-card-top">
                    <div>
                        <h4 style="font-size: 1rem; font-weight: 700; color: #f8fafc;">${l.title}</h4>
                        <span style="font-size: 0.78rem; color: #94a3b8;">By ${l.donor_name} • ${l.address}</span>
                    </div>
                    <div class="match-score-badge">
                        ${m.match_score}% <small>MATCH</small>
                    </div>
                </div>

                <div class="match-grid-details">
                    <div class="match-grid-item">
                        <span>Distance</span>
                        <strong>${m.distance_km} km</strong>
                    </div>
                    <div class="match-grid-item">
                        <span>Available Volume</span>
                        <strong>${l.quantity_kg} kg (${l.meal_equivalent} meals)</strong>
                    </div>
                    <div class="match-grid-item">
                        <span>Est. Transport</span>
                        <strong>₹${m.transport_info.estimated_cost_inr}</strong>
                    </div>
                </div>

                <div style="display: flex; gap: 0.5rem; margin-top: 0.75rem;">
                    <button class="btn btn-primary flex-1" onclick="acceptMatchedListing(${l.id}, ${m.requirement?.id || 'null'}, ${m.match_score})">
                        <i class="fa-solid fa-check"></i> Accept Match & Request Pickup
                    </button>
                    <button class="btn btn-secondary" onclick="showMatchBreakdownModal(${JSON.stringify(m).replace(/"/g, '&quot;')})">
                        <i class="fa-solid fa-chart-pie"></i> Details
                    </button>
                </div>
            </div>
        `;
    }).join("");
}

async function acceptMatchedListing(listingId, requirementId, matchScore) {
    try {
        const ngoId = FoodBridgeState.currentUser.id || 5;
        const res = await FoodBridgeAPI.acceptMatch(listingId, requirementId, ngoId, matchScore);
        showToast("Match accepted! Task dispatched to nearby volunteers.", "success");
        await refreshAllData();
        switchTab("volunteer-tab");
    } catch (e) {
        showToast("Error accepting match.", "error");
    }
}

// --- Volunteer Task Dispatch Rendering ---
function renderVolunteerTasks(tasks) {
    const container = document.getElementById("volunteer-tasks-container");
    if (!container) return;

    if (!tasks || tasks.length === 0) {
        container.innerHTML = `
            <div class="card glass-card" style="grid-column: 1 / -1; text-align: center; padding: 2.5rem;">
                <i class="fa-solid fa-bicycle" style="font-size: 2.5rem; color: #10b981; margin-bottom: 0.5rem;"></i>
                <h3>No Open Food Rescues Pending Pickup</h3>
                <p style="color: #94a3b8; font-size: 0.85rem;">All matched surplus food has been picked up or delivered.</p>
            </div>
        `;
        return;
    }

    container.innerHTML = tasks.map(t => {
        const isAssigned = !!t.volunteer_id;
        const isMyTask = t.volunteer_id === FoodBridgeState.currentUser.id;

        let actionButtonHtml = "";
        if (!isAssigned) {
            actionButtonHtml = `
                <button class="btn btn-primary btn-block" onclick="claimTask(${t.match_id})">
                    <i class="fa-solid fa-hand-fist"></i> Accept & Claim Pickup Task
                </button>
            `;
        } else if (t.match_status === "volunteer_assigned") {
            actionButtonHtml = `
                <button class="btn btn-primary btn-block" style="background: #f59e0b;" onclick="updateTaskStep(${t.match_id}, 'picked_up')">
                    <i class="fa-solid fa-box"></i> Confirm Food Picked Up from Donor
                </button>
            `;
        } else if (t.match_status === "picked_up") {
            actionButtonHtml = `
                <button class="btn btn-primary btn-block" style="background: #14b8a6;" onclick="updateTaskStep(${t.match_id}, 'delivered')">
                    <i class="fa-solid fa-truck-ramp-box"></i> Mark Reached NGO Shelter
                </button>
            `;
        } else if (t.match_status === "delivered") {
            actionButtonHtml = `
                <button class="btn btn-primary btn-block" style="background: #10b981;" onclick="updateTaskStep(${t.match_id}, 'confirmed')">
                    <i class="fa-solid fa-circle-check"></i> Final Delivery Verification & Audit
                </button>
            `;
        }

        return `
            <div class="task-card">
                <div>
                    <div class="task-header">
                        <div>
                            <span class="badge badge-urgent">🚨 Active Rescue Task</span>
                            <h4 style="font-size: 1.05rem; font-weight: 700; margin-top: 4px;">${t.food_title}</h4>
                        </div>
                        <span class="task-cost-pill">Est. ₹${t.transport_cost}</span>
                    </div>

                    <div style="font-size: 0.82rem; color: #cbd5e1; margin-bottom: 0.5rem;">
                        <strong>Cargo:</strong> ${t.quantity_kg} kg (${t.food_type}) ≈ ${t.meal_equivalent} meals
                    </div>

                    <!-- Pickup -> Dropoff Route -->
                    <div class="route-steps">
                        <div class="route-node">
                            <span class="node-dot pickup"></span>
                            <div>
                                <strong style="color: #f59e0b;">Pickup:</strong> ${t.donor_name} (${t.donor_address})
                            </div>
                        </div>
                        <div class="route-node">
                            <span class="node-dot drop"></span>
                            <div>
                                <strong style="color: #10b981;">Dropoff:</strong> ${t.ngo_name} (${t.ngo_address})
                            </div>
                        </div>
                    </div>

                    <div style="font-size: 0.78rem; color: #94a3b8; display: flex; justify-content: space-between; margin-bottom: 0.75rem;">
                        <span><i class="fa-solid fa-route"></i> Distance: <strong>${t.distance_km} km</strong></span>
                        <span><i class="fa-solid fa-clock"></i> Deadline: <strong>${t.pickup_deadline}</strong></span>
                    </div>
                </div>

                <div class="task-workflow-actions">
                    ${actionButtonHtml}
                </div>
            </div>
        `;
    }).join("");
}

async function claimTask(matchId) {
    try {
        const volId = FoodBridgeState.currentUser.id || 8;
        await FoodBridgeAPI.claimVolunteerTask(matchId, volId);
        showToast("You have claimed this food rescue mission! Proceed to donor location.", "success");
        await refreshAllData();
    } catch (e) {
        showToast("Error claiming task.", "error");
    }
}

async function updateTaskStep(matchId, nextStatus) {
    try {
        await FoodBridgeAPI.updateTaskStatus(matchId, nextStatus);
        if (nextStatus === "confirmed") {
            showToast("🎉 Delivery confirmed and recorded to public impact ledger!", "success");
        } else {
            showToast(`Task updated to ${nextStatus.replace('_', ' ').toUpperCase()}`, "info");
        }
        await refreshAllData();
    } catch (e) {
        showToast("Error updating task status.", "error");
    }
}

// --- Render Impact Stats, Charts & Leaderboards ---
function renderImpactStats(stats) {
    if (!stats || !stats.totals) return;

    const t = stats.totals;
    const kgEl = document.getElementById("stat-total-kg");
    const mealsEl = document.getElementById("stat-total-meals");
    const co2El = document.getElementById("stat-total-co2");
    const delivEl = document.getElementById("stat-total-deliveries");

    if (kgEl) kgEl.innerHTML = `${Math.round(t.total_kg_rescued)} <small>kg</small>`;
    if (mealsEl) mealsEl.innerHTML = `${t.total_meals_served} <small>meals</small>`;
    if (co2El) co2El.innerHTML = `${Math.round(t.total_co2_avoided_kg)} <small>kg CO₂e</small>`;
    if (delivEl) delivEl.textContent = t.total_deliveries;

    // Header ticker
    const tickKg = document.getElementById("ticker-kg");
    const tickMeals = document.getElementById("ticker-meals");
    const tickCo2 = document.getElementById("ticker-co2");
    if (tickKg) tickKg.textContent = `${Math.round(t.total_kg_rescued)} kg`;
    if (tickMeals) tickMeals.textContent = `${t.total_meals_served}`;
    if (tickCo2) tickCo2.textContent = `${Math.round(t.total_co2_avoided_kg)} kg`;

    // Charts
    initImpactCharts(stats);

    // Donor Leaderboard
    const donorLbContainer = document.getElementById("donor-leaderboard-container");
    if (donorLbContainer && stats.donor_leaderboard) {
        donorLbContainer.innerHTML = `
            <table class="leaderboard-table">
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Donor Kitchen</th>
                        <th>Food Rescued</th>
                        <th>Meals Provided</th>
                    </tr>
                </thead>
                <tbody>
                    ${stats.donor_leaderboard.map((d, idx) => `
                        <tr>
                            <td class="leaderboard-rank">#${idx + 1}</td>
                            <td><strong>${d.donor_name}</strong><br><small style="color: #64748b;">${d.organization || ""}</small></td>
                            <td><strong>${d.kg_donated} kg</strong></td>
                            <td style="color: #10b981; font-weight: 600;">${d.meals_provided} meals</td>
                        </tr>
                    `).join("")}
                </tbody>
            </table>
        `;
    }

    // Volunteer Leaderboard
    const volLbContainer = document.getElementById("volunteer-leaderboard-container");
    if (volLbContainer && stats.volunteer_leaderboard) {
        volLbContainer.innerHTML = `
            <table class="leaderboard-table">
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Volunteer Rescuer</th>
                        <th>Deliveries</th>
                        <th>Rescued (kg)</th>
                    </tr>
                </thead>
                <tbody>
                    ${stats.volunteer_leaderboard.map((v, idx) => `
                        <tr>
                            <td class="leaderboard-rank">#${idx + 1}</td>
                            <td><strong>${v.volunteer_name}</strong></td>
                            <td><span class="badge badge-normal">${v.deliveries_completed} Completed</span></td>
                            <td style="color: #10b981; font-weight: 600;">${v.kg_transported} kg</td>
                        </tr>
                    `).join("")}
                </tbody>
            </table>
        `;
    }

    // Audit Log Table
    const auditTbody = document.getElementById("audit-log-tbody");
    if (auditTbody && stats.recent_deliveries) {
        auditTbody.innerHTML = stats.recent_deliveries.map(item => `
            <tr>
                <td><strong>#FB-${item.id}</strong></td>
                <td>${item.food_title}<br><small style="color: #64748b;">${item.food_type}</small></td>
                <td>${item.donor_name}</td>
                <td>${item.ngo_name}</td>
                <td>🚴 ${item.volunteer_name || "Community Volunteer"}</td>
                <td><strong>${item.kg_rescued} kg</strong> (${item.meal_equivalents} meals)</td>
                <td style="color: #14b8a6;">${item.co2_avoided_kg} kg</td>
                <td style="font-size: 0.75rem; color: #94a3b8;">${item.delivered_at}</td>
                <td><span class="badge badge-normal">VERIFIED RESCUE</span></td>
            </tr>
        `).join("");
    }
}

// --- Notifications UI ---
function renderNotifications(notifs) {
    const listContainer = document.getElementById("notif-list-container");
    const countBadge = document.getElementById("unread-notif-count");

    if (countBadge) countBadge.textContent = notifs.filter(n => !n.is_read).length || 0;

    if (!listContainer) return;

    if (!notifs || notifs.length === 0) {
        listContainer.innerHTML = `<p style="text-align: center; color: #64748b; font-size: 0.82rem;">No recent notifications.</p>`;
        return;
    }

    listContainer.innerHTML = notifs.map(n => `
        <div class="notif-item ${!n.is_read ? 'unread' : ''}">
            <div class="notif-item-title">${n.title}</div>
            <p style="color: #cbd5e1;">${n.message}</p>
            <div class="notif-item-time">${n.created_at}</div>
        </div>
    `).join("");
}

function toggleNotificationPanel() {
    const drawer = document.getElementById("notif-drawer");
    const overlay = document.getElementById("notif-overlay");
    if (drawer && overlay) {
        drawer.classList.toggle("active");
        overlay.classList.toggle("active");
    }
}

async function markAllNotificationsRead() {
    await FoodBridgeAPI.markNotificationsRead();
    await refreshAllData();
    showToast("All notifications marked as read.", "info");
}

// --- Toast Messenger ---
function showToast(msg, type = "info") {
    const container = document.getElementById("toast-container");
    if (!container) return;

    const toast = document.createElement("div");
    toast.className = "toast";

    const icon = type === "success" ? "fa-circle-check" : (type === "error" ? "fa-circle-exclamation" : "fa-circle-info");
    const color = type === "success" ? "#10b981" : (type === "error" ? "#ef4444" : "#3b82f6");

    toast.innerHTML = `
        <i class="fa-solid ${icon}" style="color: ${color}; font-size: 1.1rem;"></i>
        <div style="font-size: 0.85rem; color: #f8fafc;">${msg}</div>
    `;

    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = "0";
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// --- Modals ---
function openCreateRequirementModal() {
    const modal = document.getElementById("req-modal");
    if (modal) modal.classList.remove("hidden");
}
function closeCreateRequirementModal() {
    const modal = document.getElementById("req-modal");
    if (modal) modal.classList.add("hidden");
}

async function handleNgoReqSubmit(event) {
    event.preventDefault();
    const foodType = document.getElementById("req-food-type").value;
    const meals = parseInt(document.getElementById("req-meals").value, 10);
    const address = document.getElementById("req-address").value;
    const deadline = document.getElementById("req-deadline").value;
    const notes = document.getElementById("req-notes").value;

    const data = {
        ngo_id: FoodBridgeState.currentUser.id || 5,
        ngo_name: FoodBridgeState.currentUser.name || "Hope & Care Shelter",
        food_type: foodType,
        meals_required: meals,
        address: address,
        lat: FoodBridgeState.currentUser.lat || 12.9568,
        lng: FoodBridgeState.currentUser.lng || 77.5983,
        deadline: deadline.replace("T", " ") + ":00",
        notes: notes
    };

    await FoodBridgeAPI.createRequirement(data);
    showToast("Requirement posted to FoodBridge!", "success");
    closeCreateRequirementModal();
    await refreshAllData();
}

function showMatchBreakdownModal(matchObj) {
    const modal = document.getElementById("match-modal");
    const body = document.getElementById("match-modal-body");
    if (!modal || !body) return;

    const b = matchObj.breakdown || {};
    const t = matchObj.transport_info || {};

    body.innerHTML = `
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 1rem;">
            <div>
                <h4>${matchObj.listing.title}</h4>
                <p style="color: #94a3b8; font-size: 0.82rem;">${matchObj.listing.donor_name} ➔ ${matchObj.requirement?.ngo_name || 'Your NGO'}</p>
            </div>
            <div class="match-score-badge" style="font-size: 1.4rem;">
                ${matchObj.match_score}%
            </div>
        </div>

        <h5 style="color: #10b981; margin: 1rem 0 0.5rem 0;">Algorithm Weights & Scoring Breakdown:</h5>
        <div class="match-grid-details" style="grid-template-columns: 1fr 1fr; gap: 0.75rem;">
            <div>📍 Distance Proximity (35% wt): <strong>${b.distance_score || 90}/100</strong> (${matchObj.distance_km} km)</div>
            <div>🍲 Food Compatibility (25% wt): <strong>${b.type_score || 100}/100</strong></div>
            <div>⚖️ Quantity Coverage (20% wt): <strong>${b.quantity_score || 85}/100</strong></div>
            <div>⏰ Urgency / Perishability (20% wt): <strong>${b.urgency_score || 88}/100</strong></div>
        </div>

        <h5 style="color: #3b82f6; margin: 1rem 0 0.5rem 0;">Logistics & Transport Estimation:</h5>
        <div style="background: rgba(0,0,0,0.3); padding: 0.85rem; border-radius: 8px; font-size: 0.85rem;">
            <div>Estimated Fare: <strong>₹${t.estimated_cost_inr || 75}</strong></div>
            <div>Vehicle Recommendation: <strong>${t.vehicle_icon || '🚴'} ${t.vehicle_type || 'Bike'}</strong></div>
            <div>Transit Duration: <strong>~${t.estimated_duration_mins || 20} mins</strong> in city traffic</div>
        </div>
    `;

    modal.classList.remove("hidden");
}

function closeMatchModal() {
    const modal = document.getElementById("match-modal");
    if (modal) modal.classList.add("hidden");
}

function openCieModal() {
    const modal = document.getElementById("cie-modal");
    if (modal) modal.classList.remove("hidden");
}
function closeCieModal() {
    const modal = document.getElementById("cie-modal");
    if (modal) modal.classList.add("hidden");
}

function exportImpactReport() {
    showToast("Generating official FoodBridge CIE Impact Summary PDF/CSV...", "info");
    const blob = new Blob([JSON.stringify(FoodBridgeState.impactStats, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "FoodBridge_Impact_Report.json";
    a.click();
}
