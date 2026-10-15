"""
FoodBridge - Intelligent Matching Engine
Calculates multi-factor compatibility between surplus food listings (Supply)
and NGO requirements (Demand).
"""

from transport import haversine_distance, estimate_transport

def compute_distance_score(distance_km):
    if distance_km <= 2.0:
        return 100.0
    elif distance_km <= 5.0:
        return 85.0
    elif distance_km <= 10.0:
        return 65.0
    elif distance_km <= 20.0:
        return 40.0
    else:
        return max(10.0, 100.0 - (distance_km * 4.0))

def compute_type_compatibility(listing_type, requirement_type):
    lt = (listing_type or "").strip().lower()
    rt = (requirement_type or "").strip().lower()

    if lt == rt:
        return 100.0
    
    # Semantic compatibility mappings
    if "cooked" in lt and "cooked" in rt:
        return 100.0
    if "bakery" in lt and ("snack" in rt or "bakery" in rt or "bread" in rt):
        return 90.0
    if "produce" in lt or "fruits" in lt or "vegetables" in lt:
        if "produce" in rt or "raw" in rt or "fruits" in rt:
            return 90.0
    if "packaged" in lt and ("packaged" in rt or "dry" in rt or "ration" in rt):
        return 95.0
        
    # General edible fallback
    return 40.0

def compute_quantity_compatibility(listing_meals, required_meals):
    if required_meals <= 0 or listing_meals <= 0:
        return 50.0
        
    ratio = min(listing_meals, required_meals) / max(listing_meals, required_meals)
    if ratio >= 0.75:
        return 100.0
    elif ratio >= 0.50:
        return 85.0
    elif ratio >= 0.30:
        return 65.0
    else:
        return 45.0

def match_listing_with_requirement(listing, requirement):
    """
    Computes match score between a single listing dict and a requirement dict.
    """
    dist_km = haversine_distance(
        listing["lat"], listing["lng"],
        requirement["lat"], requirement["lng"]
    )

    s_dist = compute_distance_score(dist_km)
    s_type = compute_type_compatibility(listing["food_type"], requirement["food_type"])
    s_qty = compute_quantity_compatibility(listing["meal_equivalent"], requirement["meals_required"])
    s_urgency = float(listing.get("quality_score", 80))

    # Weighted aggregate score
    # Distance (35%) + Type (25%) + Quantity (20%) + Urgency (20%)
    total_score = (0.35 * s_dist) + (0.25 * s_type) + (0.20 * s_qty) + (0.20 * s_urgency)
    total_score = round(min(99.0, max(20.0, total_score)), 1)

    transport_info = estimate_transport(dist_km, listing.get("quantity_kg", 20.0))

    return {
        "match_score": total_score,
        "distance_km": dist_km,
        "transport_info": transport_info,
        "breakdown": {
            "distance_score": round(s_dist, 1),
            "type_score": round(s_type, 1),
            "quantity_score": round(s_qty, 1),
            "urgency_score": round(s_urgency, 1)
        },
        "listing": listing,
        "requirement": requirement
    }

def find_best_matches_for_ngo(requirement, available_listings):
    """
    Finds and ranks all suitable available listings for an NGO requirement.
    """
    results = []
    for listing in available_listings:
        if listing.get("status") != "available":
            continue
        res = match_listing_with_requirement(listing, requirement)
        results.append(res)
        
    results.sort(key=lambda x: x["match_score"], reverse=True)
    return results

def find_best_matches_for_listing(listing, active_requirements):
    """
    Finds and ranks all suitable NGO requirements for a given food listing.
    """
    results = []
    for req in active_requirements:
        if req.get("status") != "active":
            continue
        res = match_listing_with_requirement(listing, req)
        results.append(res)

    results.sort(key=lambda x: x["match_score"], reverse=True)
    return results
