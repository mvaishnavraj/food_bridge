/**
 * FoodBridge - Interactive Logistics Map (Leaflet.js)
 * Visualizes Donors, NGOs, Volunteers, and Active Redistribution Routes.
 */

let foodBridgeMap = null;
let markersLayer = null;
let routesLayer = null;

function createCustomPin(color, iconClass, label = "") {
    return L.divIcon({
        className: 'custom-map-marker',
        html: `
            <div style="
                background: ${color};
                width: 34px;
                height: 34px;
                border-radius: 50% 50% 50% 0;
                transform: rotate(-45deg);
                display: flex;
                align-items: center;
                justify-content: center;
                box-shadow: 0 4px 12px rgba(0,0,0,0.5);
                border: 2px solid #ffffff;
            ">
                <i class="${iconClass}" style="
                    transform: rotate(45deg);
                    color: #ffffff;
                    font-size: 13px;
                "></i>
            </div>
        `,
        iconSize: [34, 34],
        iconAnchor: [17, 34],
        popupAnchor: [0, -32]
    });
}

function initFoodBridgeMap() {
    const mapElement = document.getElementById("leaflet-map");
    if (!mapElement) return;

    // Default center: Bengaluru (MG Road / Indiranagar)
    const defaultCenter = [12.9650, 77.6150];

    if (!foodBridgeMap) {
        foodBridgeMap = L.map('leaflet-map', {
            center: defaultCenter,
            zoom: 13,
            zoomControl: true,
            preferCanvas: true
        });

        // 1. High-Speed OpenStreetMap Tiles (100% reliable, free, globally accessible)
        const osmLayer = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors | FoodBridge Logistics',
            maxZoom: 19,
            subdomains: ['a', 'b', 'c']
        });

        // 2. CartoDB Voyager Tiles (Clean aesthetic)
        const cartoLayer = L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://carto.com/">CARTO</a> | FoodBridge Network',
            subdomains: 'abcd',
            maxZoom: 19
        });

        // Default to OpenStreetMap for guaranteed visibility
        osmLayer.addTo(foodBridgeMap);

        // Add Layer Toggle Control
        L.control.layers({
            "🗺️ OpenStreetMap (Standard)": osmLayer,
            "🎨 Carto Voyager (Clean)": cartoLayer
        }).addTo(foodBridgeMap);

        markersLayer = L.layerGroup().addTo(foodBridgeMap);
        routesLayer = L.layerGroup().addTo(foodBridgeMap);
    }

    // Force Leaflet to recalculate container geometry upon tab display
    setTimeout(() => { if (foodBridgeMap) foodBridgeMap.invalidateSize(true); }, 50);
    setTimeout(() => { if (foodBridgeMap) foodBridgeMap.invalidateSize(true); }, 250);
    setTimeout(() => { if (foodBridgeMap) foodBridgeMap.invalidateSize(true); }, 600);

    renderAllMapEntities();
}

function renderAllMapEntities() {
    if (!foodBridgeMap || !markersLayer) return;

    markersLayer.clearLayers();
    routesLayer.clearLayers();

    const listings = FoodBridgeState.listings || [];
    const requirements = FoodBridgeState.requirements || [];
    const tasks = FoodBridgeState.volunteerTasks || [];

    // 1. Render Surplus Food Listings (Donors)
    listings.forEach(listing => {
        if (!listing.lat || !listing.lng) return;

        let pinColor = "#10b981"; // Normal (green)
        let urgencyBadge = '<span class="badge badge-normal">🟢 Normal</span>';

        if (listing.quality_score >= 85) {
            pinColor = "#ef4444"; // Urgent (red)
            urgencyBadge = '<span class="badge badge-urgent">🔴 Urgent</span>';
        } else if (listing.quality_score >= 70) {
            pinColor = "#f59e0b"; // High (orange)
            urgencyBadge = '<span class="badge badge-high">🟠 High Priority</span>';
        }

        const marker = L.marker([listing.lat, listing.lng], {
            icon: createCustomPin(pinColor, "fa-solid fa-utensils")
        });

        const popupHtml = `
            <div style="font-family: 'Inter', sans-serif; min-width: 220px; color: #1e293b;">
                <div style="font-weight: 700; font-size: 14px; margin-bottom: 4px;">${listing.title}</div>
                <div style="font-size: 12px; color: #64748b; margin-bottom: 6px;">
                    <i class="fa-solid fa-location-dot"></i> ${listing.address}
                </div>
                <div style="display: flex; gap: 6px; margin-bottom: 8px;">
                    ${urgencyBadge}
                    <span style="font-size: 11px; background: #e2e8f0; padding: 2px 6px; border-radius: 4px; font-weight: 600;">
                        ${listing.quantity_kg} kg (~${listing.meal_equivalent} meals)
                    </span>
                </div>
                <div style="font-size: 11px; color: #475569; margin-bottom: 8px;">
                    ⏰ Pickup by: <strong>${listing.pickup_deadline}</strong>
                </div>
                <button onclick="switchTab('ngo-tab')" style="
                    background: #10b981; color: white; border: none; padding: 5px 10px;
                    border-radius: 6px; font-size: 11px; font-weight: 600; cursor: pointer; width: 100%;
                ">
                    View in NGO Matching Hub
                </button>
            </div>
        `;

        marker.bindPopup(popupHtml);
        markersLayer.addLayer(marker);
    });

    // 2. Render NGO Requirements (Demand)
    const ngoLocations = [
        { name: "Hope & Care Shelter", lat: 12.9568, lng: 77.5983, address: "Shanti Nagar", meals: 70 },
        { name: "Annapurna Seva Trust", lat: 12.9609, lng: 77.6387, address: "Domlur Village", meals: 100 },
        { name: "Care For All Children Home", lat: 12.9116, lng: 77.6465, address: "HSR Layout Sector 2", meals: 50 }
    ];

    ngoLocations.forEach(ngo => {
        const marker = L.marker([ngo.lat, ngo.lng], {
            icon: createCustomPin("#3b82f6", "fa-solid fa-handshake-angle")
        });

        const popupHtml = `
            <div style="font-family: 'Inter', sans-serif; min-width: 200px; color: #1e293b;">
                <div style="font-weight: 700; font-size: 14px; color: #2563eb; margin-bottom: 2px;">${ngo.name}</div>
                <div style="font-size: 12px; color: #64748b; margin-bottom: 6px;">📍 ${ngo.address}</div>
                <div style="font-size: 12px; font-weight: 600; background: #dbeafe; color: #1e40af; padding: 3px 8px; border-radius: 4px; display: inline-block;">
                    Demand: ~${ngo.meals} meals needed
                </div>
            </div>
        `;

        marker.bindPopup(popupHtml);
        markersLayer.addLayer(marker);
    });

    // 3. Render Active Volunteer Rescuers
    const volunteers = [
        { name: "Rahul Sharma (Bike)", lat: 12.9719, lng: 77.6412 },
        { name: "Priya Verma (EV Scooter)", lat: 12.9350, lng: 77.6190 },
        { name: "Arun Kumar (Delivery Van)", lat: 12.9634, lng: 77.6012 }
    ];

    volunteers.forEach(v => {
        const marker = L.marker([v.lat, v.lng], {
            icon: createCustomPin("#8b5cf6", "fa-solid fa-bicycle")
        });

        marker.bindPopup(`
            <div style="font-family: 'Inter', sans-serif; color: #1e293b;">
                <strong>🚴 ${v.name}</strong><br>
                <small style="color: #64748b;">Ready for Food Rescue Dispatch</small>
            </div>
        `);
        markersLayer.addLayer(marker);
    });

    // 4. Render Active Delivery Routing Lines
    tasks.forEach(task => {
        if (task.donor_lat && task.donor_lng && task.ngo_lat && task.ngo_lng) {
            const latlngs = [
                [task.donor_lat, task.donor_lng],
                [task.ngo_lat, task.ngo_lng]
            ];

            const polyline = L.polyline(latlngs, {
                color: '#10b981',
                weight: 4,
                dashArray: '8, 8',
                opacity: 0.85
            });

            polyline.bindPopup(`
                <div style="font-family: 'Inter', sans-serif; color: #1e293b;">
                    <strong>Active Rescue Route</strong><br>
                    ${task.food_title}<br>
                    Distance: ${task.distance_km} km | Est. Transport: ₹${task.transport_cost}
                </div>
            `);

            routesLayer.addLayer(polyline);
        }
    });
}
