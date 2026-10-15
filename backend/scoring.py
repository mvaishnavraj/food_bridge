"""
FoodBridge - Quality & Urgency Scoring Engine
Calculates dynamic 0-100 priority score based on:
1. Time remaining until pickup deadline
2. Real-time ambient weather (Open-Meteo API: temp & humidity)
3. Food perishability category
4. Quantity volume
5. Freshness & handling indicators
"""

import requests
from datetime import datetime
import json

PERISHABILITY_WEIGHTS = {
    "Cooked Meals": 1.0,
    "Dairy Products": 0.95,
    "Fruits & Vegetables": 0.70,
    "Bakery Items": 0.60,
    "Packaged Food": 0.40,
    "Raw Produce": 0.65
}

MEAL_CONVERSION_FACTORS = {
    "Cooked Meals": 3.0,       # 1 kg = 3 meals
    "Dairy Products": 4.0,     # 1 kg = 4 portions
    "Fruits & Vegetables": 2.5,
    "Bakery Items": 3.0,
    "Packaged Food": 3.0,
    "Raw Produce": 2.5
}

def get_live_weather(lat=12.9716, lng=77.5946):
    """
    Fetches real-time weather from Open-Meteo free API (no API key required).
    """
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lng}&current_weather=true&hourly=relativehumidity_2m"
        res = requests.get(url, timeout=3)
        if res.status_code == 200:
            data = res.json()
            curr = data.get("current_weather", {})
            temp = curr.get("temperature", 27.0)
            # Fetch humidity approximation
            humidity_list = data.get("hourly", {}).get("relativehumidity_2m", [60])
            humidity = humidity_list[0] if humidity_list else 60.0
            
            condition = "Warm & Humid" if temp > 28 and humidity > 65 else ("Sunny" if temp > 26 else "Moderate")
            return {
                "temp": round(temp, 1),
                "humidity": round(humidity, 1),
                "condition": condition,
                "is_live": True
            }
    except Exception as e:
        print(f"[Weather Info] Using default contextual weather ({e})")

    return {
        "temp": 27.5,
        "humidity": 62.0,
        "condition": "Partly Cloudy",
        "is_live": False
    }

def calculate_meal_equivalents(quantity_kg, food_type="Cooked Meals"):
    factor = MEAL_CONVERSION_FACTORS.get(food_type, 3.0)
    return int(round(quantity_kg * factor))

def calculate_co2_avoided(quantity_kg):
    # UNEP average: 1kg food waste avoided saves ~2.5kg CO2 eq
    return round(quantity_kg * 2.5, 1)

def compute_quality_urgency_score(pickup_deadline_str, food_type="Cooked Meals", quantity_kg=10.0, notes="", lat=12.9716, lng=77.5946):
    """
    Returns:
      score: integer between 0 and 100
      priority: 'urgent' (>=85), 'high' (70-84), 'normal' (<70)
      breakdown: dict of contributing weights
      weather: weather info dict
    """
    # 1. Time Factor (0 - 40 pts)
    now = datetime.now()
    try:
        deadline = datetime.strptime(pickup_deadline_str, "%Y-%m-%d %H:%M:%S")
        time_diff_hours = (deadline - now).total_seconds() / 3600.0
    except Exception:
        try:
            deadline = datetime.strptime(pickup_deadline_str, "%Y-%m-%d %H:%M")
            time_diff_hours = (deadline - now).total_seconds() / 3600.0
        except Exception:
            time_diff_hours = 2.0 # Default 2 hours

    if time_diff_hours <= 0:
        time_score = 40.0 # Extreme urgency / past deadline
    elif time_diff_hours <= 1.0:
        time_score = 38.0
    elif time_diff_hours <= 2.0:
        time_score = 32.0
    elif time_diff_hours <= 4.0:
        time_score = 22.0
    elif time_diff_hours <= 6.0:
        time_score = 15.0
    else:
        time_score = 8.0

    # 2. Food Type Perishability (0 - 25 pts)
    p_weight = PERISHABILITY_WEIGHTS.get(food_type, 0.70)
    food_score = p_weight * 25.0

    # 3. Weather Decay Acceleration (0 - 15 pts)
    weather = get_live_weather(lat, lng)
    temp = weather.get("temp", 27.0)
    humidity = weather.get("humidity", 60.0)

    weather_factor = 0.0
    if temp >= 32.0:
        weather_factor += 8.0
    elif temp >= 28.0:
        weather_factor += 5.0
    else:
        weather_factor += 2.0

    if humidity >= 70.0:
        weather_factor += 7.0
    elif humidity >= 50.0:
        weather_factor += 4.0
    else:
        weather_factor += 2.0
    
    # Scale weather impact by perishability
    weather_score = min(15.0, weather_factor * p_weight * 1.2)

    # 4. Quantity Scale Impact (0 - 10 pts)
    if quantity_kg >= 50.0:
        quantity_score = 10.0
    elif quantity_kg >= 25.0:
        quantity_score = 8.0
    elif quantity_kg >= 10.0:
        quantity_score = 6.0
    else:
        quantity_score = 4.0

    # 5. Freshness & Handling Indicators (0 - 10 pts)
    notes_lower = (notes or "").lower()
    freshness_score = 6.0
    if any(k in notes_lower for k in ["warm", "refrigerated", "sealed", "packed", "prepared today"]):
        freshness_score += 4.0
    elif any(k in notes_lower for k in ["urgent", "quick", "immediate"]):
        freshness_score += 3.0

    # Total Score Calculation
    total_score = int(round(time_score + food_score + weather_score + quantity_score + freshness_score))
    total_score = max(10, min(99, total_score)) # Clamp between 10 and 99

    if total_score >= 85:
        priority = "urgent"
        priority_label = "🔴 Urgent Rescue Needed"
    elif total_score >= 70:
        priority = "high"
        priority_label = "🟠 High Priority"
    else:
        priority = "normal"
        priority_label = "🟢 Standard Window"

    breakdown = {
        "time_factor": round(time_score, 1),
        "perishability_factor": round(food_score, 1),
        "weather_factor": round(weather_score, 1),
        "quantity_factor": round(quantity_score, 1),
        "freshness_factor": round(freshness_score, 1),
        "hours_remaining": round(max(0, time_diff_hours), 1)
    }

    return {
        "score": total_score,
        "priority": priority,
        "priority_label": priority_label,
        "breakdown": breakdown,
        "weather": weather
    }

if __name__ == "__main__":
    res = compute_quality_urgency_score("2026-10-03 21:00:00", "Cooked Meals", 30.0, "Kept warm, prepared 1 hr ago")
    print(json.dumps(res, indent=2))
