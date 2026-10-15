"""
FoodBridge - Flask REST Backend Server
Handles all API routes for Donors, NGOs, Volunteers, Matching, VLM Verification,
Logistics Tracking, and Impact Analytics.
"""

import os
import json
import sqlite3
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename

from database import get_db, init_db, seed_data_if_empty
from vlm import verify_food_image
from scoring import compute_quality_urgency_score, calculate_meal_equivalents, calculate_co2_avoided, get_live_weather
from matching import match_listing_with_requirement, find_best_matches_for_ngo, find_best_matches_for_listing
from transport import estimate_transport, haversine_distance

app = Flask(__name__, static_folder="../frontend", static_url_path="")
CORS(app)

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "..", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB max

# Initialize database on startup
init_db()
seed_data_if_empty()

# --- Helper Functions ---
def dict_from_row(row):
    if row is None:
        return None
    d = dict(row)
    # Parse JSON fields if present
    for json_field in ["ai_verification", "weather_info"]:
        if json_field in d and d[json_field]:
            try:
                d[json_field] = json.loads(d[json_field])
            except Exception:
                pass
    return d

def add_notification(user_id, target_role, title, message, notif_type="info"):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO notifications (user_id, target_role, title, message, type)
    VALUES (?, ?, ?, ?, ?)
    """, (user_id, target_role, title, message, notif_type))
    conn.commit()
    conn.close()

# --- Static Frontend Serving ---
@app.route("/")
def serve_index():
    return send_from_directory(app.static_folder, "index.html")

@app.route("/uploads/<filename>")
def serve_uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

# --- 1. Health & Meta Endpoints ---
@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "status": "healthy",
        "service": "FoodBridge AI Core",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    })

# --- 2. Users & Roles ---
@app.route("/api/users", methods=["GET"])
def get_users():
    role = request.args.get("role")
    conn = get_db()
    cursor = conn.cursor()
    if role:
        cursor.execute("SELECT * FROM users WHERE role = ?", (role,))
    else:
        cursor.execute("SELECT * FROM users")
    users = [dict_from_row(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(users)

# --- 3. Standalone AI VLM Preview Endpoint ---
@app.route("/api/vlm/verify-preview", methods=["POST"])
def verify_preview():
    food_type = request.form.get("food_type", "Cooked Meals")
    notes = request.form.get("notes", "")
    image_url = request.form.get("image_url", "")
    
    image_file = request.files.get("image")
    if image_file and image_file.filename:
        filename = secure_filename(f"preview_{datetime.now().strftime('%Y%m%d%H%M%S')}_{image_file.filename}")
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        image_file.save(filepath)
        vlm_res = verify_food_image(filepath, food_type, notes)
        vlm_res["saved_url"] = f"/uploads/{filename}"
    elif image_url:
        vlm_res = verify_food_image(image_url, food_type, notes)
        vlm_res["saved_url"] = image_url
    else:
        return jsonify({"error": "No image or image_url provided"}), 400

    return jsonify(vlm_res)

# --- 4. Food Listings (Supply) Endpoints ---
@app.route("/api/listings", methods=["GET"])
def get_listings():
    status = request.args.get("status")
    donor_id = request.args.get("donor_id")
    food_type = request.args.get("food_type")

    query = "SELECT * FROM listings WHERE 1=1"
    params = []

    if status and status != "all":
        query += " AND status = ?"
        params.append(status)
    if donor_id:
        query += " AND donor_id = ?"
        params.append(donor_id)
    if food_type:
        query += " AND food_type = ?"
        params.append(food_type)

    query += " ORDER BY id DESC"

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(query, params)
    listings = [dict_from_row(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(listings)

@app.route("/api/listings/<int:listing_id>", methods=["GET"])
def get_listing(listing_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM listings WHERE id = ?", (listing_id,))
    listing = dict_from_row(cursor.fetchone())
    conn.close()
    if not listing:
        return jsonify({"error": "Listing not found"}), 404
    return jsonify(listing)

@app.route("/api/listings", methods=["POST"])
def create_listing():
    # Supports multipart/form-data or json
    if request.is_json:
        data = request.get_json()
        image_url = data.get("image_url", "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=600")
        donor_id = data.get("donor_id", 1)
        donor_name = data.get("donor_name", "Grand Palace Hotel")
        title = data.get("title", "Surplus Food")
        food_type = data.get("food_type", "Cooked Meals")
        quantity_kg = float(data.get("quantity_kg", 20.0))
        address = data.get("address", "MG Road, Bengaluru")
        lat = float(data.get("lat", 12.9716))
        lng = float(data.get("lng", 77.5946))
        pickup_deadline = data.get("pickup_deadline")
        prepared_at = data.get("prepared_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        notes = data.get("notes", "")
    else:
        donor_id = int(request.form.get("donor_id", 1))
        donor_name = request.form.get("donor_name", "Grand Palace Hotel")
        title = request.form.get("title", "Surplus Food Donation")
        food_type = request.form.get("food_type", "Cooked Meals")
        quantity_kg = float(request.form.get("quantity_kg", 20.0))
        address = request.form.get("address", "MG Road, Bengaluru")
        lat = float(request.form.get("lat", 12.9716))
        lng = float(request.form.get("lng", 77.5946))
        pickup_deadline = request.form.get("pickup_deadline")
        prepared_at = request.form.get("prepared_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        notes = request.form.get("notes", "")
        
        image_file = request.files.get("image")
        if image_file and image_file.filename:
            filename = secure_filename(f"food_{datetime.now().strftime('%Y%m%d%H%M%S')}_{image_file.filename}")
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            image_file.save(filepath)
            image_url = f"/uploads/{filename}"
        else:
            image_url = request.form.get("image_url", "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=600")

    if not pickup_deadline:
        pickup_deadline = (datetime.now() + timedelta(hours=3)).strftime("%Y-%m-%d %H:%M:%S")

    # 1. AI VLM Verification
    vlm_result = verify_food_image(image_url, food_type, notes)

    # 2. Quality / Urgency Scoring
    score_result = compute_quality_urgency_score(pickup_deadline, food_type, quantity_kg, notes, lat, lng)
    quality_score = score_result["score"]
    weather_info = score_result["weather"]

    # 3. Meal Equivalents
    meal_equivalent = calculate_meal_equivalents(quantity_kg, food_type)

    # 4. Insert into database
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO listings (
        donor_id, donor_name, title, food_type, quantity_kg, meal_equivalent,
        address, lat, lng, pickup_deadline, prepared_at, notes, image_url,
        ai_verification, quality_score, weather_info, status
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        donor_id, donor_name, title, food_type, quantity_kg, meal_equivalent,
        address, lat, lng, pickup_deadline, prepared_at, notes, image_url,
        json.dumps(vlm_result), quality_score, json.dumps(weather_info), "available"
    ))
    listing_id = cursor.lastrowid
    conn.commit()
    conn.close()

    # 5. Broadcast notification to NGOs
    priority_emoji = "🚨" if score_result["priority"] == "urgent" else "🍱"
    add_notification(
        None, "ngo",
        f"{priority_emoji} New Surplus Food Available: {title}",
        f"{quantity_kg} kg (~{meal_equivalent} meals) posted by {donor_name} at {address}. Quality/Urgency Score: {quality_score}/100.",
        "urgent" if score_result["priority"] == "urgent" else "match"
    )

    return jsonify({
        "success": True,
        "message": "Surplus food listing created successfully.",
        "listing_id": listing_id,
        "meal_equivalent": meal_equivalent,
        "quality_score": quality_score,
        "priority": score_result["priority"],
        "ai_verification": vlm_result,
        "weather_info": weather_info
    }), 201

# --- 5. NGO Requirements (Demand) Endpoints ---
@app.route("/api/requirements", methods=["GET"])
def get_requirements():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM requirements ORDER BY id DESC")
    reqs = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(reqs)

@app.route("/api/requirements", methods=["POST"])
def create_requirement():
    data = request.get_json() or request.form
    ngo_id = int(data.get("ngo_id", 5))
    ngo_name = data.get("ngo_name", "Hope & Care Shelter")
    food_type = data.get("food_type", "Cooked Meals")
    meals_required = int(data.get("meals_required", 50))
    address = data.get("address", "Shanti Nagar, Bengaluru")
    lat = float(data.get("lat", 12.9568))
    lng = float(data.get("lng", 77.5983))
    deadline = data.get("deadline", (datetime.now() + timedelta(hours=4)).strftime("%Y-%m-%d %H:%M:%S"))
    notes = data.get("notes", "")

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO requirements (ngo_id, ngo_name, food_type, meals_required, address, lat, lng, deadline, notes, status)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (ngo_id, ngo_name, food_type, meals_required, address, lat, lng, deadline, notes, "active"))
    req_id = cursor.lastrowid
    conn.commit()
    conn.close()

    add_notification(
        None, "donor",
        f"🤝 New NGO Requirement: {meals_required} {food_type}",
        f"{ngo_name} is requesting {meals_required} meals at {address} before {deadline}.",
        "match"
    )

    return jsonify({
        "success": True,
        "requirement_id": req_id,
        "message": "NGO requirement created successfully."
    }), 201

# --- 6. Intelligent Matching Endpoints ---
@app.route("/api/matches/for-ngo/<int:ngo_id>", methods=["GET"])
def get_matches_for_ngo(ngo_id):
    conn = get_db()
    cursor = conn.cursor()
    
    # Fetch active NGO requirements
    cursor.execute("SELECT * FROM requirements WHERE ngo_id = ? AND status = 'active'", (ngo_id,))
    reqs = [dict(r) for r in cursor.fetchall()]

    # Fetch available listings
    cursor.execute("SELECT * FROM listings WHERE status = 'available'")
    listings = [dict_from_row(r) for r in cursor.fetchall()]
    conn.close()

    if not reqs:
        # If no specific requirement, match against NGO's user profile location
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (ngo_id,))
        user = dict_from_row(cursor.fetchone())
        conn.close()
        
        synthetic_req = {
            "id": 0, "ngo_id": ngo_id, "ngo_name": user["name"] if user else "NGO",
            "food_type": "Cooked Meals", "meals_required": 60,
            "address": user["address"] if user else "Bengaluru",
            "lat": user["lat"] if user else 12.9568,
            "lng": user["lng"] if user else 77.5983
        }
        matches = find_best_matches_for_ngo(synthetic_req, listings)
        return jsonify({"requirement": synthetic_req, "matches": matches})

    all_matches = []
    for req in reqs:
        matches = find_best_matches_for_ngo(req, listings)
        all_matches.append({
            "requirement": req,
            "matches": matches
        })

    return jsonify(all_matches)

@app.route("/api/matches/for-listing/<int:listing_id>", methods=["GET"])
def get_matches_for_listing(listing_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM listings WHERE id = ?", (listing_id,))
    listing = dict_from_row(cursor.fetchone())
    
    cursor.execute("SELECT * FROM requirements WHERE status = 'active'")
    reqs = [dict(r) for r in cursor.fetchall()]
    conn.close()

    if not listing:
        return jsonify({"error": "Listing not found"}), 404

    matches = find_best_matches_for_listing(listing, reqs)
    return jsonify({"listing": listing, "matches": matches})

# --- 7. NGO Match Acceptance ---
@app.route("/api/matches/accept", methods=["POST"])
def accept_match():
    data = request.get_json()
    listing_id = int(data.get("listing_id"))
    requirement_id = data.get("requirement_id")
    ngo_id = int(data.get("ngo_id", 5))

    conn = get_db()
    cursor = conn.cursor()

    # Get listing
    cursor.execute("SELECT * FROM listings WHERE id = ?", (listing_id,))
    listing = dict_from_row(cursor.fetchone())
    if not listing or listing["status"] != "available":
        conn.close()
        return jsonify({"error": "Listing is not available"}), 400

    # Get NGO
    cursor.execute("SELECT * FROM users WHERE id = ?", (ngo_id,))
    ngo = dict_from_row(cursor.fetchone())
    ngo_name = ngo["name"] if ngo else "Partner NGO"
    ngo_lat = ngo["lat"] if ngo else 12.9568
    ngo_lng = ngo["lng"] if ngo else 77.5983

    # Calculate distance & transport
    dist_km = haversine_distance(listing["lat"], listing["lng"], ngo_lat, ngo_lng)
    transport = estimate_transport(dist_km, listing["quantity_kg"])
    match_score = float(data.get("match_score", 90.0))

    # Update listing status
    cursor.execute("UPDATE listings SET status = 'ngo_accepted' WHERE id = ?", (listing_id,))
    
    # If requirement exists, update requirement
    if requirement_id:
        cursor.execute("UPDATE requirements SET status = 'matched' WHERE id = ?", (requirement_id,))

    # Insert match
    cursor.execute("""
    INSERT INTO matches (listing_id, requirement_id, ngo_id, match_score, distance_km, transport_cost, status)
    VALUES (?, ?, ?, ?, ?, ?, 'ngo_accepted')
    """, (listing_id, requirement_id, ngo_id, match_score, dist_km, transport["estimated_cost_inr"]))
    match_id = cursor.lastrowid
    conn.commit()
    conn.close()

    # Notify Volunteers
    add_notification(
        None, "volunteer",
        "🚨 Volunteer Pickup Needed!",
        f"{listing['quantity_kg']} kg food matched for {ngo_name}. Pickup from {listing['address']} to {ngo['address']}. Transport: ₹{transport['estimated_cost_inr']}.",
        "urgent"
    )

    return jsonify({
        "success": True,
        "match_id": match_id,
        "message": "Match accepted by NGO. Rescue task is now open for volunteer pickup.",
        "transport_info": transport
    })

# --- 8. Volunteer Coordination Hub ---
@app.route("/api/volunteers/tasks", methods=["GET"])
def get_volunteer_tasks():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT m.id as match_id, m.status as match_status, m.match_score, m.distance_km, m.transport_cost,
           l.id as listing_id, l.title as food_title, l.food_type, l.quantity_kg, l.meal_equivalent,
           l.address as donor_address, l.lat as donor_lat, l.lng as donor_lng, l.pickup_deadline,
           l.donor_name, l.notes as food_notes, l.image_url, l.quality_score,
           u.id as ngo_id, u.name as ngo_name, u.address as ngo_address, u.phone as ngo_phone,
           u.lat as ngo_lat, u.lng as ngo_lng,
           m.volunteer_id, v.name as volunteer_name
    FROM matches m
    JOIN listings l ON m.listing_id = l.id
    JOIN users u ON m.ngo_id = u.id
    LEFT JOIN users v ON m.volunteer_id = v.id
    WHERE m.status IN ('ngo_accepted', 'volunteer_assigned', 'picked_up')
    ORDER BY m.id DESC
    """)
    tasks = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(tasks)

@app.route("/api/volunteers/claim-task", methods=["POST"])
def claim_volunteer_task():
    data = request.get_json()
    match_id = int(data.get("match_id"))
    volunteer_id = int(data.get("volunteer_id", 8))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM matches WHERE id = ?", (match_id,))
    match = dict_from_row(cursor.fetchone())

    if not match:
        conn.close()
        return jsonify({"error": "Task not found"}), 404

    cursor.execute("""
    UPDATE matches SET volunteer_id = ?, status = 'volunteer_assigned', updated_at = CURRENT_TIMESTAMP
    WHERE id = ?
    """, (volunteer_id, match_id))

    cursor.execute("UPDATE listings SET status = 'volunteer_assigned' WHERE id = ?", (match["listing_id"],))

    # Fetch volunteer name
    cursor.execute("SELECT name FROM users WHERE id = ?", (volunteer_id,))
    vol_row = cursor.fetchone()
    vol_name = vol_row["name"] if vol_row else "Volunteer"

    conn.commit()
    conn.close()

    add_notification(
        match["ngo_id"], "ngo",
        "🚴 Volunteer Assigned!",
        f"{vol_name} has accepted pickup for food donation #{match['listing_id']}.",
        "status_update"
    )

    return jsonify({
        "success": True,
        "message": f"Task successfully assigned to {vol_name}."
    })

@app.route("/api/volunteers/update-status", methods=["POST"])
def update_task_status():
    data = request.get_json()
    match_id = int(data.get("match_id"))
    new_status = data.get("status") # 'picked_up', 'delivered', 'confirmed'

    valid_statuses = ['picked_up', 'delivered', 'confirmed']
    if new_status not in valid_statuses:
        return jsonify({"error": f"Invalid status. Must be one of {valid_statuses}"}), 400

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT m.*, l.donor_id, l.quantity_kg, l.meal_equivalent, l.title as food_title,
           u.name as ngo_name
    FROM matches m
    JOIN listings l ON m.listing_id = l.id
    JOIN users u ON m.ngo_id = u.id
    WHERE m.id = ?
    """, (match_id,))
    task = dict_from_row(cursor.fetchone())

    if not task:
        conn.close()
        return jsonify({"error": "Task not found"}), 404

    cursor.execute("""
    UPDATE matches SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?
    """, (new_status, match_id))
    cursor.execute("UPDATE listings SET status = ? WHERE id = ?", (new_status, task["listing_id"]))

    # If confirmed, record into impact_log
    if new_status == "confirmed":
        co2_saved = calculate_co2_avoided(task["quantity_kg"])
        cursor.execute("""
        INSERT INTO impact_log (
            listing_id, donor_id, ngo_id, volunteer_id, kg_rescued, meal_equivalents,
            co2_avoided_kg, distance_km, delivered_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (
            task["listing_id"], task["donor_id"], task["ngo_id"], task["volunteer_id"],
            task["quantity_kg"], task["meal_equivalent"], co2_saved, task["distance_km"]
        ))

        # Also mark requirement as fulfilled
        if task.get("requirement_id"):
            cursor.execute("UPDATE requirements SET status = 'fulfilled' WHERE id = ?", (task["requirement_id"],))

        # Broadcast celebration notifications
        add_notification(
            task["donor_id"], "donor",
            "🎉 Surplus Food Successfully Delivered & Confirmed!",
            f"Your donation of {task['quantity_kg']} kg (~{task['meal_equivalent']} meals) has been safely delivered to {task['ngo_name']}! Thank you for reducing food waste.",
            "success"
        )
        add_notification(
            task["ngo_id"], "ngo",
            "✅ Delivery Confirmed!",
            f"Food donation #{task['listing_id']} has been received and verified.",
            "success"
        )

    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "new_status": new_status,
        "message": f"Task state advanced to '{new_status}'."
    })

# --- 9. Impact Dashboard & Analytics ---
@app.route("/api/impact/stats", methods=["GET"])
def get_impact_stats():
    conn = get_db()
    cursor = conn.cursor()

    # Aggregate Metrics
    cursor.execute("""
    SELECT 
        COALESCE(SUM(kg_rescued), 0) as total_kg_rescued,
        COALESCE(SUM(meal_equivalents), 0) as total_meals_served,
        COALESCE(SUM(co2_avoided_kg), 0) as total_co2_avoided_kg,
        COUNT(*) as total_deliveries
    FROM impact_log
    """)
    totals = dict(cursor.fetchone())

    # Count of Donors and Volunteers
    cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'donor'")
    totals["total_donors"] = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'volunteer'")
    totals["total_volunteers"] = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'ngo'")
    totals["total_ngos"] = cursor.fetchone()[0]

    # Food Category Breakdown
    cursor.execute("""
    SELECT l.food_type, COALESCE(SUM(i.kg_rescued), 0) as total_kg, COUNT(i.id) as count
    FROM impact_log i
    JOIN listings l ON i.listing_id = l.id
    GROUP BY l.food_type
    """)
    category_breakdown = [dict(r) for r in cursor.fetchall()]

    # Status Funnel Count
    cursor.execute("""
    SELECT status, COUNT(*) as count FROM listings GROUP BY status
    """)
    status_counts = {r["status"]: r["count"] for r in cursor.fetchall()}

    # Donor Leaderboard
    cursor.execute("""
    SELECT u.name as donor_name, u.organization, COALESCE(SUM(i.kg_rescued), 0) as kg_donated,
           COALESCE(SUM(i.meal_equivalents), 0) as meals_provided, COUNT(i.id) as donation_count
    FROM users u
    JOIN impact_log i ON u.id = i.donor_id
    WHERE u.role = 'donor'
    GROUP BY u.id
    ORDER BY kg_donated DESC
    LIMIT 5
    """)
    donor_leaderboard = [dict(r) for r in cursor.fetchall()]

    # Volunteer Leaderboard
    cursor.execute("""
    SELECT u.name as volunteer_name, COUNT(i.id) as deliveries_completed,
           COALESCE(SUM(i.kg_rescued), 0) as kg_transported,
           COALESCE(SUM(i.distance_km), 0) as total_km
    FROM users u
    JOIN impact_log i ON u.id = i.volunteer_id
    WHERE u.role = 'volunteer'
    GROUP BY u.id
    ORDER BY deliveries_completed DESC
    LIMIT 5
    """)
    volunteer_leaderboard = [dict(r) for r in cursor.fetchall()]

    # Recent Deliveries Feed
    cursor.execute("""
    SELECT i.*, l.title as food_title, l.food_type, d.name as donor_name, n.name as ngo_name, v.name as volunteer_name
    FROM impact_log i
    JOIN listings l ON i.listing_id = l.id
    JOIN users d ON i.donor_id = d.id
    JOIN users n ON i.ngo_id = n.id
    LEFT JOIN users v ON i.volunteer_id = v.id
    ORDER BY i.id DESC
    LIMIT 8
    """)
    recent_deliveries = [dict(r) for r in cursor.fetchall()]

    conn.close()

    return jsonify({
        "totals": totals,
        "category_breakdown": category_breakdown,
        "status_counts": status_counts,
        "donor_leaderboard": donor_leaderboard,
        "volunteer_leaderboard": volunteer_leaderboard,
        "recent_deliveries": recent_deliveries
    })

# --- 10. Notifications Feed ---
@app.route("/api/notifications", methods=["GET"])
def get_notifications():
    role = request.args.get("role")
    conn = get_db()
    cursor = conn.cursor()
    if role:
        cursor.execute("SELECT * FROM notifications WHERE target_role IS NULL OR target_role = ? ORDER BY id DESC LIMIT 20", (role,))
    else:
        cursor.execute("SELECT * FROM notifications ORDER BY id DESC LIMIT 20")
    notifs = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return jsonify(notifs)

@app.route("/api/notifications/mark-read", methods=["POST"])
def mark_notifications_read():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE notifications SET is_read = 1")
    conn.commit()
    conn.close()
    return jsonify({"success": True})

if __name__ == "__main__":
    import sys
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
        except Exception:
            pass
    print("==================================================")
    print(" [FoodBridge] Surplus Food Redistribution Server")
    print(" Serving at: http://127.0.0.1:5000")
    print("==================================================")
    app.run(host="0.0.0.0", port=5000, debug=True)
