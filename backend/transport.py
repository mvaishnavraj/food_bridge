"""
FoodBridge - Transport Estimation Engine
Calculates estimated logistics cost, recommended vehicle type,
and transit duration based on Haversine distance and cargo weight.
"""

import math

def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculates the great-circle distance between two GPS coordinates in kilometers.
    """
    R = 6371.0 # Earth radius in km

    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = R * c
    return round(distance, 2)

def estimate_transport(distance_km, quantity_kg=20.0):
    """
    Returns:
      estimated_cost_inr: float (₹)
      vehicle_type: 'Bike / 2-Wheeler', 'Auto-Rickshaw / EV Cargo', 'Delivery Van / Mini Cargo'
      vehicle_icon: '🚴', '🛺', '🚐'
      estimated_duration_mins: integer minutes
      cost_breakdown: dict
    """
    # Ensure minimum distance
    dist = max(0.5, float(distance_km))
    weight = float(quantity_kg)

    if weight <= 15.0:
        vehicle_type = "Bike / EV 2-Wheeler"
        vehicle_icon = "🚴"
        base_fare = 35.0
        per_km_rate = 10.0
    elif weight <= 40.0:
        vehicle_type = "Auto-Rickshaw / EV Cargo"
        vehicle_icon = "🛺"
        base_fare = 55.0
        per_km_rate = 14.0
    else:
        vehicle_type = "Delivery Van / Mini Cargo"
        vehicle_icon = "🚐"
        base_fare = 120.0
        per_km_rate = 22.0

    total_cost = round(base_fare + (dist * per_km_rate), 0)

    # City traffic duration (approx 3.5 mins per km + 10 mins loading)
    duration_mins = int(round(10 + (dist * 3.5)))

    return {
        "distance_km": dist,
        "estimated_cost_inr": total_cost,
        "vehicle_type": vehicle_type,
        "vehicle_icon": vehicle_icon,
        "estimated_duration_mins": duration_mins,
        "cost_breakdown": {
            "base_fare": base_fare,
            "per_km_rate": per_km_rate,
            "distance_charge": round(dist * per_km_rate, 2)
        }
    }

if __name__ == "__main__":
    print(estimate_transport(3.2, 25.0))
