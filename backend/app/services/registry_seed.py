"""
Camera registry seed data — assigns representative Gujarat geo-coordinates and
owning departments to cameras so the GIS map (Model 1 foundation) has real pins.

Per the hackathon rules teams supply their own representative/watchlist data; these
are plausible Gujarat locations spread statewide, INCLUDING the border/coastal
districts the problem statement names (Valsad, Dwarka, Somnath, Jamnagar, Dahod, Bhuj).
Swap in the real camera locations if the government feed metadata provides them.
"""
from typing import Any, Dict, List

# cam id -> location metadata. Coordinates are decimal degrees (lat, lon).
GUJARAT_GEO: Dict[str, Dict[str, Any]] = {
    "cam01": {"location": "Ahmedabad",     "district": "Ahmedabad",     "department": "Home Department",         "lat": 23.0225, "lon": 72.5714},
    "cam02": {"location": "Gandhinagar",   "district": "Gandhinagar",   "department": "Home Department",         "lat": 23.2156, "lon": 72.6369},
    "cam03": {"location": "Surat",         "district": "Surat",         "department": "Municipal",               "lat": 21.1702, "lon": 72.8311},
    "cam04": {"location": "Vadodara",      "district": "Vadodara",      "department": "Home Department",         "lat": 22.3072, "lon": 73.1812},
    "cam05": {"location": "Rajkot",        "district": "Rajkot",        "department": "GSRTC",                   "lat": 22.3039, "lon": 70.8022},
    "cam06": {"location": "Bhavnagar",     "district": "Bhavnagar",     "department": "Municipal",               "lat": 21.7645, "lon": 72.1519},
    "cam07": {"location": "Jamnagar",      "district": "Jamnagar",      "department": "Home Department",         "lat": 22.4707, "lon": 70.0577},
    "cam08": {"location": "Junagadh",      "district": "Junagadh",      "department": "Panchayat",               "lat": 21.5222, "lon": 70.4579},
    "cam09": {"location": "Gandhidham",    "district": "Kutch",         "department": "GSRTC",                   "lat": 23.0753, "lon": 70.1337},
    "cam10": {"location": "Anand",         "district": "Anand",         "department": "RTO",                     "lat": 22.5645, "lon": 72.9289},
    "cam11": {"location": "Nadiad",        "district": "Kheda",         "department": "Health",                  "lat": 22.6939, "lon": 72.8618},
    "cam12": {"location": "Mehsana",       "district": "Mehsana",       "department": "Food & Civil Supplies",   "lat": 23.5880, "lon": 72.3693},
    "cam13": {"location": "Morbi",         "district": "Morbi",         "department": "Municipal",               "lat": 22.8173, "lon": 70.8370},
    "cam14": {"location": "Surendranagar", "district": "Surendranagar", "department": "Panchayat",               "lat": 22.7469, "lon": 71.6479},
    "cam15": {"location": "Bharuch",       "district": "Bharuch",       "department": "RTO",                     "lat": 21.7051, "lon": 72.9959},
    "cam16": {"location": "Navsari",       "district": "Navsari",       "department": "Home Department",         "lat": 20.9467, "lon": 72.9520},
    "cam17": {"location": "Valsad",        "district": "Valsad",        "department": "Home Department",         "lat": 20.5992, "lon": 72.9342},
    "cam18": {"location": "Vapi",          "district": "Valsad",        "department": "Municipal",               "lat": 20.3893, "lon": 72.9106},
    "cam19": {"location": "Porbandar",     "district": "Porbandar",     "department": "GSRTC",                   "lat": 21.6417, "lon": 69.6293},
    "cam20": {"location": "Dwarka",        "district": "Devbhoomi Dwarka","department": "Home Department",       "lat": 22.2394, "lon": 68.9678},
    "cam21": {"location": "Somnath",       "district": "Gir Somnath",   "department": "Home Department",         "lat": 20.9159, "lon": 70.3629},
    "cam22": {"location": "Dahod",         "district": "Dahod",         "department": "Home Department",         "lat": 22.8340, "lon": 74.2599},
    "cam23": {"location": "Godhra",        "district": "Panchmahal",    "department": "Panchayat",               "lat": 22.7788, "lon": 73.6143},
    "cam24": {"location": "Palanpur",      "district": "Banaskantha",   "department": "RTO",                     "lat": 24.1719, "lon": 72.4344},
    "cam25": {"location": "Patan",         "district": "Patan",         "department": "Food & Civil Supplies",   "lat": 23.8493, "lon": 72.1266},
    "cam26": {"location": "Bhuj",          "district": "Kutch",         "department": "Home Department",         "lat": 23.2419, "lon": 69.6669},
    "cam27": {"location": "Amreli",        "district": "Amreli",        "department": "Health",                  "lat": 21.6032, "lon": 71.2221},
    "cam28": {"location": "Botad",         "district": "Botad",         "department": "Panchayat",               "lat": 22.1704, "lon": 71.6685},
    "cam29": {"location": "Himatnagar",    "district": "Sabarkantha",   "department": "GSRTC",                   "lat": 23.5966, "lon": 72.9634},
    "cam30": {"location": "Modasa",        "district": "Aravalli",      "department": "Municipal",               "lat": 23.4626, "lon": 73.2985},
}


def seed_registry(cameras: List[Dict[str, Any]]) -> int:
    """Merge catalogue cameras with geo metadata and upsert into the registry.
    Idempotent — safe to run on every startup. Returns number of cameras seeded."""
    from app.services.sighting_repository import sighting_repo

    count = 0
    for cam in cameras:
        cid = cam.get("id")
        if not cid:
            continue
        geo = GUJARAT_GEO.get(cid, {})
        sighting_repo.upsert_camera({
            "id": cid,
            "name": cam.get("name"),
            "location": geo.get("location") or cam.get("location"),
            "district": geo.get("district"),
            "department": geo.get("department"),
            "lat": geo.get("lat"),
            "lon": geo.get("lon"),
            "rtsp_url": cam.get("rtsp_url"),
            "status": cam.get("status", "AVAILABLE"),
        })
        count += 1
    return count
