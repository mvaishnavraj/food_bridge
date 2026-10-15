"""
FoodBridge - SQLite Database Layer
Handles database initialization, table creation, seed data, and query helpers.
"""

import sqlite3
import os
import json
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), "foodbridge.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # 1. Users Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL DEFAULT 'password123',
        role TEXT NOT NULL CHECK(role IN ('donor', 'ngo', 'volunteer', 'admin')),
        name TEXT NOT NULL,
        organization TEXT,
        phone TEXT,
        address TEXT,
        lat REAL,
        lng REAL,
        verified INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 2. Food Listings Table (Supply)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS listings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        donor_id INTEGER,
        donor_name TEXT NOT NULL,
        title TEXT NOT NULL,
        food_type TEXT NOT NULL,
        quantity_kg REAL NOT NULL,
        meal_equivalent INTEGER NOT NULL,
        address TEXT NOT NULL,
        lat REAL NOT NULL,
        lng REAL NOT NULL,
        pickup_deadline TEXT NOT NULL,
        prepared_at TEXT,
        notes TEXT,
        image_url TEXT,
        ai_verification TEXT, -- JSON: is_bulk, confidence, reason, detected_items
        quality_score INTEGER DEFAULT 80,
        weather_info TEXT,    -- JSON: temp, humidity, condition
        status TEXT DEFAULT 'available' CHECK(status IN ('available', 'matched', 'ngo_accepted', 'volunteer_assigned', 'picked_up', 'delivered', 'confirmed', 'rejected')),
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (donor_id) REFERENCES users (id)
    )
    """)

    # 3. NGO Requirements Table (Demand)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS requirements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ngo_id INTEGER,
        ngo_name TEXT NOT NULL,
        food_type TEXT NOT NULL,
        meals_required INTEGER NOT NULL,
        address TEXT NOT NULL,
        lat REAL NOT NULL,
        lng REAL NOT NULL,
        deadline TEXT NOT NULL,
        notes TEXT,
        status TEXT DEFAULT 'active' CHECK(status IN ('active', 'matched', 'fulfilled', 'cancelled')),
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (ngo_id) REFERENCES users (id)
    )
    """)

    # 4. Matches Table (Coordination)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS matches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        listing_id INTEGER NOT NULL,
        requirement_id INTEGER,
        ngo_id INTEGER NOT NULL,
        volunteer_id INTEGER,
        match_score REAL NOT NULL,
        distance_km REAL NOT NULL,
        transport_cost REAL NOT NULL,
        status TEXT DEFAULT 'pending_ngo' CHECK(status IN ('pending_ngo', 'ngo_accepted', 'volunteer_assigned', 'picked_up', 'delivered', 'confirmed', 'rejected')),
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (listing_id) REFERENCES listings (id),
        FOREIGN KEY (requirement_id) REFERENCES requirements (id),
        FOREIGN KEY (ngo_id) REFERENCES users (id),
        FOREIGN KEY (volunteer_id) REFERENCES users (id)
    )
    """)

    # 5. Impact Log Table (Analytics)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS impact_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        listing_id INTEGER,
        donor_id INTEGER,
        ngo_id INTEGER,
        volunteer_id INTEGER,
        kg_rescued REAL NOT NULL,
        meal_equivalents INTEGER NOT NULL,
        co2_avoided_kg REAL NOT NULL,
        distance_km REAL NOT NULL,
        delivered_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (listing_id) REFERENCES listings (id)
    )
    """)

    # 6. Notifications Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        target_role TEXT,
        title TEXT NOT NULL,
        message TEXT NOT NULL,
        type TEXT DEFAULT 'info' CHECK(type IN ('urgent', 'match', 'status_update', 'success', 'info')),
        is_read INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()

def seed_data_if_empty():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] > 0:
        conn.close()
        return

    print("[INFO] Seeding initial demo data for FoodBridge...")

    now = datetime.now()

    # 1. Users
    users_data = [
        # Donors
        ("hotel_the_leela", "password123", "donor", "The Grand Palace Hotel", "Grand Palace Hospitality", "+91 98450 11223", "MG Road, Bengaluru", 12.9716, 77.5946, 1),
        ("royal_catering", "password123", "donor", "Royal Feast Caterers", "Royal Feast Events", "+91 98451 22334", "Indiranagar 100ft Rd, Bengaluru", 12.9784, 77.6408, 1),
        ("tech_park_cafeteria", "password123", "donor", "Global Tech Park Cafeteria", "Sodexo Services", "+91 98452 33445", "Ecospace, Bellandur, Bengaluru", 12.9260, 77.6762, 1),
        ("sweet_bakes", "password123", "donor", "Artisan Bakery & Cafe", "Sweet Bakes Ltd", "+91 98453 44556", "Koramangala 4th Block, Bengaluru", 12.9352, 77.6245, 1),

        # NGOs
        ("hope_foundation", "password123", "ngo", "Hope & Care Shelter", "Hope Foundation NGO", "+91 98110 55667", "Shanti Nagar, Bengaluru", 12.9568, 77.5983, 1),
        ("annapurna_trust", "password123", "ngo", "Annapurna Seva Trust", "Annapurna Trust", "+91 98111 66778", "Domlur Village, Bengaluru", 12.9609, 77.6387, 1),
        ("care_for_all", "password123", "ngo", "Care For All Children Home", "Care Foundation", "+91 98112 77889", "HSR Layout Sector 2, Bengaluru", 12.9116, 77.6465, 1),

        # Volunteers
        ("rahul_rider", "password123", "volunteer", "Rahul Sharma", "Student Volunteer (Bike)", "+91 99001 88990", "Indiranagar, Bengaluru", 12.9719, 77.6412, 1),
        ("priya_verma", "password123", "volunteer", "Priya Verma", "Community Volunteer (EV Scooter)", "+91 99002 99001", "Koramangala, Bengaluru", 12.9350, 77.6190, 1),
        ("arun_kumar", "password123", "volunteer", "Arun Kumar", "Rotary Volunteer (Van)", "+91 99003 11224", "Richmond Town, Bengaluru", 12.9634, 77.6012, 1),
    ]

    cursor.executemany("""
    INSERT INTO users (username, password, role, name, organization, phone, address, lat, lng, verified)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, users_data)

    # 2. Food Listings (Supply)
    listings_data = [
        (
            1, "The Grand Palace Hotel", "Surplus Buffet - Rice, Dal & Paneer Curry", "Cooked Meals", 30.0, 90,
            "MG Road, Bengaluru", 12.9716, 77.5946,
            (now + timedelta(hours=2, minutes=30)).strftime("%Y-%m-%d %H:%M:%S"),
            (now - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S"),
            "Prepared for corporate lunch banquet. Kept under warmers. Sealed in 3 food grade vessels.",
            "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=600",
            json.dumps({"is_bulk": True, "confidence": 0.94, "reason": "Large commercial stainless steel catering containers detected.", "detected_items": ["Cooked Rice", "Dal Makhani", "Paneer Sabzi"]}),
            88,
            json.dumps({"temp": 27.5, "humidity": 62, "condition": "Partly Cloudy"}),
            "available"
        ),
        (
            2, "Royal Feast Caterers", "Wedding Surplus - Biryani & Gravy", "Cooked Meals", 45.0, 135,
            "Indiranagar 100ft Rd, Bengaluru", 12.9784, 77.6408,
            (now + timedelta(hours=1, minutes=15)).strftime("%Y-%m-%d %H:%M:%S"),
            (now - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S"),
            "Fresh veg biryani & salan from evening reception. Ready for immediate pickup.",
            "https://images.unsplash.com/photo-1563379091339-03b21ab4a4f8?w=600",
            json.dumps({"is_bulk": True, "confidence": 0.97, "reason": "Bulk degh/biryani handis detected with high portion volume.", "detected_items": ["Vegetable Biryani", "Mirchi Ka Salan"]}),
            94,
            json.dumps({"temp": 26.8, "humidity": 65, "condition": "Clear"}),
            "available"
        ),
        (
            4, "Artisan Bakery & Cafe", "Fresh Bread Loaves, Buns & Tea Cakes", "Bakery Items", 18.0, 54,
            "Koramangala 4th Block, Bengaluru", 12.9352, 77.6245,
            (now + timedelta(hours=6)).strftime("%Y-%m-%d %H:%M:%S"),
            (now - timedelta(hours=3)).strftime("%Y-%m-%d %H:%M:%S"),
            "Day-end surplus packaged artisanal loaves and wheat buns.",
            "https://images.unsplash.com/photo-1509440159596-0249088772ff?w=600",
            json.dumps({"is_bulk": True, "confidence": 0.91, "reason": "Multiple stacked bakery crates and bulk loaf packages.", "detected_items": ["Whole Wheat Loaves", "Dinner Rolls", "Fruit Cakes"]}),
            76,
            json.dumps({"temp": 28.0, "humidity": 58, "condition": "Clear"}),
            "available"
        ),
        (
            3, "Global Tech Park Cafeteria", "Packaged Sandwiches & Fruit Bowls", "Packaged Food", 22.0, 66,
            "Ecospace, Bellandur, Bengaluru", 12.9260, 77.6762,
            (now + timedelta(hours=3, minutes=45)).strftime("%Y-%m-%d %H:%M:%S"),
            (now - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S"),
            "Chilled sealed sandwiches and cut fruit packs from office cafeteria lunch shift.",
            "https://images.unsplash.com/photo-1528735602780-2552fd46c7af?w=600",
            json.dumps({"is_bulk": True, "confidence": 0.93, "reason": "Commercial stacked pre-packaged meal trays with barcode labels.", "detected_items": ["Club Sandwiches", "Melon Bowls"]}),
            82,
            json.dumps({"temp": 27.2, "humidity": 60, "condition": "Partly Cloudy"}),
            "available"
        )
    ]

    cursor.executemany("""
    INSERT INTO listings (
        donor_id, donor_name, title, food_type, quantity_kg, meal_equivalent,
        address, lat, lng, pickup_deadline, prepared_at, notes, image_url,
        ai_verification, quality_score, weather_info, status
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, listings_data)

    # 3. NGO Requirements (Demand)
    requirements_data = [
        (
            5, "Hope & Care Shelter", "Cooked Meals", 70,
            "Shanti Nagar, Bengaluru", 12.9568, 77.5983,
            (now + timedelta(hours=3)).strftime("%Y-%m-%d %H:%M:%S"),
            "Dinner requirement for 70 resident elders & children. Veg preferred.",
            "active"
        ),
        (
            6, "Annapurna Seva Trust", "Cooked Meals", 100,
            "Domlur Village, Bengaluru", 12.9609, 77.6387,
            (now + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S"),
            "Night community food distribution drive near Domlur flyover.",
            "active"
        ),
        (
            7, "Care For All Children Home", "Bakery Items", 50,
            "HSR Layout Sector 2, Bengaluru", 12.9116, 77.6465,
            (now + timedelta(hours=5)).strftime("%Y-%m-%d %H:%M:%S"),
            "Evening snacks for orphanage kids. Bread, buns, cakes welcome.",
            "active"
        )
    ]

    cursor.executemany("""
    INSERT INTO requirements (
        ngo_id, ngo_name, food_type, meals_required, address, lat, lng, deadline, notes, status
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, requirements_data)

    # 4. Historical Past Impact Logs (to populate analytics & leaderboards immediately)
    historical_logs = [
        (1, 1, 5, 8, 35.0, 105, 87.5, 3.2, (now - timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S")),
        (2, 2, 6, 8, 50.0, 150, 125.0, 2.1, (now - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")),
        (3, 4, 7, 9, 25.0, 75, 62.5, 4.5, (now - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")),
        (4, 3, 5, 10, 40.0, 120, 100.0, 8.4, (now - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")),
        (1, 1, 6, 9, 28.0, 84, 70.0, 4.1, (now - timedelta(hours=14)).strftime("%Y-%m-%d %H:%M:%S")),
    ]

    cursor.executemany("""
    INSERT INTO impact_log (
        listing_id, donor_id, ngo_id, volunteer_id, kg_rescued, meal_equivalents, co2_avoided_kg, distance_km, delivered_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, historical_logs)

    # 5. Initial Notifications
    notifications_data = [
        (None, "ngo", "🚨 High Urgency Food Alert", "Royal Feast Caterers posted 45 kg (135 meals) Biryani near Indiranagar with a 75-min pickup window!", "urgent"),
        (None, "volunteer", "🚴 New Food Rescue Task Available", "Pickup needed from MG Road to Shanti Nagar (3.2 km). Estimated transport: ₹75.", "match"),
        (None, "donor", "🌱 Impact Update", "Over 178 kg of food successfully redistributed this week across Bengaluru!", "success")
    ]

    cursor.executemany("""
    INSERT INTO notifications (user_id, target_role, title, message, type)
    VALUES (?, ?, ?, ?, ?)
    """, notifications_data)

    conn.commit()
    conn.close()
    print("[SUCCESS] Database schema created and demo data seeded.")

if __name__ == "__main__":
    init_db()
    seed_data_if_empty()
