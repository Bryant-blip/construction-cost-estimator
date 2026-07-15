"""Construction cost estimation logic.

Cost data and formulas ported from the Self-Storage Analysis Suite's
"Quick Estimate" feature (Real Estate Project repo, git commit cb54ad7).
"""

# ── Property Type Cost Data ──────────────────────────────────────────────────
# Per-SF costs and lump-sum items for each property type.
# Sources: RSMeans 2024/2025 national averages, adjusted by location factor.

PROPERTY_TYPES = {
    "storage_driveup": {
        "label": "Self-Storage: Drive-Up",
        "has_stories": False,
        "per_sf": [
            ("Site Work & Grading",        5.50),
            ("Concrete Slab / Foundation", 8.00),
            ("Steel Structure",           18.00),
            ("Metal Roofing",              5.50),
            ("Electrical & Lighting",      4.00),
            ("Paving & Parking",           4.50),
        ],
        "lump": [
            ("Roll-Up Doors",    "~1 per 125 SF", lambda sf: int(sf / 125) * 1100),
            ("Security System",  "Lump sum",      lambda sf: 30000),
            ("Office Buildout",  "~400 SF",       lambda sf: 400 * 130),
        ],
    },
    "storage_cc": {
        "label": "Self-Storage: Climate Controlled",
        "has_stories": True,
        "per_sf": [
            ("Site Work & Grading",        5.50),
            ("Concrete Slab / Foundation", 9.50),
            ("Steel Structure",           22.00),
            ("Metal Roofing",              5.50),
            ("HVAC System",               12.00),
            ("Insulation",                 4.00),
            ("Interior Corridors",         6.00),
            ("Fire Suppression",           3.50),
            ("Electrical & Lighting",      5.00),
            ("Paving & Parking",           4.50),
        ],
        "lump": [
            ("Roll-Up / Entry Doors", "~1 per 100 SF", lambda sf: int(sf / 100) * 1200),
            ("Elevator",              "If > 20k SF",    lambda sf: 120000 if sf > 20000 else 0),
            ("Security System",       "Lump sum",       lambda sf: 40000),
            ("Office Buildout",       "~400 SF",        lambda sf: 400 * 140),
        ],
    },
    "retail_qsr": {
        "label": "Retail / QSR (Shell)",
        "has_stories": False,
        "per_sf": [
            ("Site Work & Grading",          8.00),
            ("Foundation",                  12.00),
            ("Structural Framing",          18.00),
            ("Exterior Walls & Façade",     22.00),
            ("Roofing",                      8.00),
            ("Storefront / Windows",        10.00),
            ("Electrical & Lighting",        8.00),
            ("Plumbing (Rough)",             6.00),
            ("HVAC (Shell Prep)",            5.00),
            ("Paving & Parking",             6.00),
        ],
        "lump": [
            ("Drive-Thru Infrastructure", "If applicable", lambda sf: 45000 if sf < 4000 else 0),
            ("Grease Trap / Hood Prep",   "QSR standard",  lambda sf: 25000),
            ("Signage Allowance",         "Lump sum",      lambda sf: 15000),
            ("ADA / Restrooms",           "Lump sum",      lambda sf: 20000),
        ],
    },
    "warehouse": {
        "label": "Warehouse / Distribution",
        "has_stories": False,
        "per_sf": [
            ("Site Work & Grading",          4.00),
            ("Concrete Slab / Foundation",  7.50),
            ("Steel Structure (Clear Span)", 16.00),
            ("Metal Roofing & Walls",        6.50),
            ("Dock Doors & Levelers",        3.00),
            ("Electrical & Lighting",        4.50),
            ("Fire Suppression (ESFR)",      3.50),
            ("Paving & Truck Courts",        5.00),
        ],
        "lump": [
            ("Office Buildout",   "~1,000 SF",   lambda sf: 1000 * 130),
            ("Security / Fencing", "Lump sum",   lambda sf: 35000),
        ],
    },
    "medical_office": {
        "label": "Medical Office",
        "has_stories": True,
        "per_sf": [
            ("Site Work & Grading",          6.00),
            ("Foundation",                  12.00),
            ("Structural Framing",          24.00),
            ("Exterior Walls & Façade",     18.00),
            ("Roofing",                      7.00),
            ("Interior Build-Out",          35.00),
            ("HVAC (Medical Grade)",        18.00),
            ("Plumbing (Medical)",          12.00),
            ("Electrical & Lighting",       12.00),
            ("Fire Suppression",             4.00),
            ("Paving & Parking",             5.00),
        ],
        "lump": [
            ("Elevator",           "If multi-story", lambda sf: 150000 if sf > 10000 else 0),
            ("Medical Gas Systems", "Lump sum",      lambda sf: 40000),
            ("ADA Compliance",     "Lump sum",       lambda sf: 25000),
        ],
    },
    "multifamily": {
        "label": "Multifamily — Garden Style",
        "has_stories": True,
        "per_sf": [
            ("Site Work & Grading",          5.50),
            ("Foundation",                  10.00),
            ("Wood / Steel Framing",        22.00),
            ("Exterior Walls & Siding",     14.00),
            ("Roofing",                      6.00),
            ("Windows & Doors",              8.00),
            ("Interior Finishes",           28.00),
            ("HVAC (Per Unit)",             10.00),
            ("Plumbing (Per Unit)",         12.00),
            ("Electrical & Lighting",        8.00),
            ("Fire Suppression",             3.50),
            ("Paving & Parking",             4.00),
        ],
        "lump": [
            ("Elevator",           "If 3+ stories", lambda sf: 160000 if sf > 30000 else 0),
            ("Clubhouse / Amenity", "Lump sum",     lambda sf: 80000),
            ("Landscaping",        "Lump sum",       lambda sf: 50000),
        ],
    },
}

QUALITY_MULT = {"Economy": 0.85, "Average": 1.00, "Premium": 1.15}

SOFT_COSTS = [
    ("Architectural & Engineering",   0.050),
    ("Permits & Impact Fees",         0.025),
    ("Geotechnical / Environmental",  0.008),
    ("Survey & Land Planning",        0.004),
    ("Legal & Closing",               0.008),
    ("Builder's Risk Insurance",      0.007),
    ("Construction Loan Interest",    0.040),
    ("Property Taxes During Const.",  0.008),
    ("Contingency",                   0.075),
]

LOCATION_FACTORS = {
    "new york": 1.42, "manhattan": 1.48, "brooklyn": 1.42, "bronx": 1.42,
    "los angeles": 1.18, "chicago": 1.12, "houston": 0.88, "phoenix": 0.92,
    "philadelphia": 1.15, "san antonio": 0.85, "san diego": 1.15,
    "dallas": 0.90, "austin": 0.92, "fort worth": 0.89,
    "jacksonville": 0.87, "san francisco": 1.38, "san jose": 1.30,
    "columbus": 0.93, "charlotte": 0.88, "indianapolis": 0.92,
    "seattle": 1.15, "denver": 0.96, "nashville": 0.90,
    "atlanta": 0.90, "portland": 1.08, "las vegas": 0.98,
    "memphis": 0.85, "louisville": 0.90, "baltimore": 0.98,
    "milwaukee": 1.02, "albuquerque": 0.90, "tucson": 0.90,
    "fresno": 1.05, "sacramento": 1.12, "miami": 0.95,
    "tampa": 0.90, "orlando": 0.90, "st louis": 0.98,
    "pittsburgh": 1.00, "raleigh": 0.88, "minneapolis": 1.05,
    "cleveland": 0.98, "detroit": 1.00, "boston": 1.25,
    "honolulu": 1.35, "anchorage": 1.28, "kansas city": 0.95,
    "oklahoma city": 0.85, "omaha": 0.90, "virginia beach": 0.90,
    "colorado springs": 0.93, "tulsa": 0.84, "arlington": 0.89,
    "new orleans": 0.88, "bakersfield": 1.05, "boise": 0.92,
    "richmond": 0.90, "des moines": 0.92, "salt lake city": 0.93,
    "birmingham": 0.85, "spokane": 1.00, "rochester": 1.02,
}


def lookup_location_factor(city_text: str) -> tuple[float, str]:
    lower = city_text.lower().strip().rstrip(",").strip()
    for city, factor in LOCATION_FACTORS.items():
        if city in lower:
            return factor, city.title()
    return 1.00, ""


class EstimateError(ValueError):
    pass


def compute_estimate(building_type, sf, city="", quality="Average",
                      loan_rate=8.5, const_months=12, land_cost=0):
    """Compute a full cost estimate. Returns a dict consumed by both the
    JSON API response and the Excel export."""
    if sf <= 0:
        raise EstimateError("SF must be positive")

    ptype = PROPERTY_TYPES.get(building_type)
    if not ptype:
        raise EstimateError(f"Unknown property type: {building_type}")

    q_mult = QUALITY_MULT.get(quality, 1.0)
    loc_factor, matched_city = lookup_location_factor(city)

    hard_items = []
    total_hard = 0.0

    for name, base_psf in ptype["per_sf"]:
        adj_psf = base_psf * q_mult * loc_factor
        cost = adj_psf * sf
        hard_items.append({"name": name, "note": f"${adj_psf:,.2f}", "psf_raw": adj_psf, "cost_raw": cost})
        total_hard += cost

    for name, note, calc_fn in ptype["lump"]:
        cost = calc_fn(sf) * q_mult * loc_factor
        if cost > 0:
            hard_items.append({"name": name, "note": note, "psf_raw": None, "cost_raw": cost})
            total_hard += cost

    loan_rate = max(0, min(loan_rate, 25))
    const_months = max(1, min(const_months, 48))
    # Average outstanding balance is ~50% of total (draws happen over time)
    loan_interest = total_hard * (loan_rate / 100) * (const_months / 12) * 0.5

    soft_items = []
    total_soft = 0.0
    for name, pct in SOFT_COSTS:
        if name == "Construction Loan Interest":
            soft_items.append({
                "name": f"Construction Loan Interest ({loan_rate:.1f}% × {const_months}mo)",
                "pct_raw": (loan_interest / total_hard) if total_hard > 0 else 0.0,
                "cost_raw": loan_interest,
            })
            total_soft += loan_interest
        else:
            amt = total_hard * pct
            soft_items.append({"name": name, "pct_raw": pct, "cost_raw": amt})
            total_soft += amt

    # ── Land & Acquisition Costs (only when user provides land cost) ──
    land_cost = max(0, land_cost)
    land_items = []
    total_land = 0.0
    if land_cost > 0:
        land_items.append({"name": "Land Purchase Price", "note": "User entered", "cost_raw": land_cost})
        total_land += land_cost

        title_closing = land_cost * 0.015
        land_items.append({"name": "Title & Closing Costs", "note": "~1.5% of land", "cost_raw": title_closing})
        total_land += title_closing

        land_items.append({"name": "Phase I ESA", "note": "Lump sum", "cost_raw": 4000.0})
        total_land += 4000.0

        land_items.append({"name": "ALTA Survey", "note": "Lump sum", "cost_raw": 7500.0})
        total_land += 7500.0

        land_items.append({"name": "Utility Tap / Impact Fees", "note": "Lump sum", "cost_raw": 15000.0})
        total_land += 15000.0

    grand_total = total_hard + total_soft + total_land
    total_psf = grand_total / sf if sf > 0 else 0

    return {
        "building_type": building_type,
        "building_label": ptype["label"],
        "sf": sf,
        "city": city or "National Avg",
        "quality": quality,
        "loan_rate": loan_rate,
        "const_months": const_months,
        "location_factor": loc_factor,
        "matched_city": matched_city,
        "hard_items": hard_items,
        "total_hard": total_hard,
        "soft_items": soft_items,
        "total_soft": total_soft,
        "land_cost_input": land_cost,
        "land_items": land_items,
        "total_land": total_land,
        "grand_total": grand_total,
        "total_psf": total_psf,
    }


def format_for_json(est: dict) -> dict:
    """Shape an estimate dict into the JSON response the frontend expects."""
    return {
        "building_type": est["building_label"],
        "sf": est["sf"],
        "city": est["city"],
        "quality": est["quality"],
        "location_factor": est["location_factor"],
        "matched_city": est["matched_city"],
        "hard_cost_rows": [
            {"name": i["name"], "psf": i["note"], "cost": f"${i['cost_raw']:,.0f}"}
            for i in est["hard_items"]
        ],
        "total_hard": f"${est['total_hard']:,.0f}",
        "soft_cost_rows": [
            {"name": i["name"], "pct": f"{i['pct_raw']:.1%}", "cost": f"${i['cost_raw']:,.0f}"}
            for i in est["soft_items"]
        ],
        "total_soft": f"${est['total_soft']:,.0f}",
        "land_cost_rows": [
            {"name": i["name"], "note": i["note"], "cost": f"${i['cost_raw']:,.0f}"}
            for i in est["land_items"]
        ],
        "total_land": f"${est['total_land']:,.0f}",
        "grand_total": f"${est['grand_total']:,.0f}",
        "total_psf": f"${est['total_psf']:,.2f}",
    }
