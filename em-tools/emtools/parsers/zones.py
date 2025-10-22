from __future__ import annotations
from typing import Dict, Any, List, Optional
from xml.etree import ElementTree as ET
from emtools.parsers.constants import SURFACE_BUCKETS


# -------------------- helpers (namespace-agnostic) --------------------
def _lt(tag: str) -> str:
    return tag.split('}', 1)[-1] if '}' in (tag or '') else (tag or '')


def _child_text_local(node: ET.Element | None, *names: str) -> str | None:
    if node is None:
        return None
    wanted = {n.lower() for n in names}
    for ch in list(node):
        if _lt(getattr(ch, "tag", "")).lower() in wanted:
            txt = (ch.text or "").strip()
            if txt:
                return txt
    return None


def _first_child_local(node: ET.Element | None, *names: str) -> ET.Element | None:
    if node is None:
        return None
    wanted = {n.lower() for n in names}
    for ch in list(node):
        if _lt(getattr(ch, "tag", "")).lower() in wanted:
            return ch
    return None


def _zone_key(zn: ET.Element) -> str:
    # prefer element text children first, then attributes
    name = (_child_text_local(zn, "Name", "ZnName", "ZoneName", "ID", "Id")
            or zn.get("Name") or zn.get("id") or "")
    return name.strip()


def _slug(s: str) -> str:
    import re
    s = (s or "").strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "zone"


def _diag(em: Dict[str, Any], level: str, code: str, message: str, context: Dict[str, Any] | None = None):
    em.setdefault("diagnostics", []).append({
        "level": level, "code": code, "message": message, "context": context or {}
    })


def _to_float(s: str | None) -> float | None:
    if not s: return None
    try:
        return float(str(s).replace(",", "").strip())
    except Exception:
        return None


# -------------------- zones (ResZn + ComZn) --------------------
def parse_zones(
        root: ET.Element,
        em: Dict[str, Any],
        id_registry: Any,  # IDRegistry instance
        du_index: Dict[str, Dict[str, Any]] | None = None,
        zone_to_group: Dict[str, str] | None = None
) -> List[Dict[str, Any]]:
    """
    Build em['geometry']['zones'] from both ResZn and ComZn.
    - Uses IDRegistry for stable zone IDs
    - Namespace agnostic element/field reads
    - Records zone_multiplier, du_count_in_zone, and effective_multiplier
    - Multiplier metadata includes flat_path for round-tripping
    - Converts units: ft² -> m², ft³ -> m³
    """
    du_index = du_index or {}
    zone_to_group = zone_to_group or {}
    zones: List[Dict[str, Any]] = []
    geom = em.setdefault("geometry", {})
    geom["zones"] = zones

    def _read_zone_multiplier(zn: ET.Element) -> int:
        raw = (_child_text_local(zn, "ZnMult") or _child_text_local(zn, "Mult") or _child_text_local(zn, "Count")
               or zn.get("ZnMult") or zn.get("Mult") or zn.get("Count"))
        try:
            return int(float(raw)) if raw not in (None, "") else 1
        except Exception:
            return 1

    def _read_du_count(zn: ET.Element) -> int:
        du = _first_child_local(zn, "DwellUnit", "DU", "Unit")
        raw = (_child_text_local(du, "Count") or (du.get("Count") if du is not None else None) or "1")
        try:
            return int(float(raw))
        except Exception:
            return 1

    def _du_ref_from_zone(zn: ET.Element) -> str | None:
        ref = (_child_text_local(zn, "DUTypeRef")
               or _child_text_local(_first_child_local(zn, "DwellUnit"), "DwellUnitTypeRef")
               or zn.get("DUTypeRef"))
        if ref:
            key = ref.strip().lower()
            if key in du_index: return du_index[key]["id"]
        # heuristic fallback by zone name
        zname = _zone_key(zn)
        if zname:
            token = zname.split("_", 1)[0].strip()
            guess = f"unit {token}".lower()
            if guess in du_index: return du_index[guess]["id"]
        return None

    have_area = 0
    for zn in (el for el in root.iter() if _lt(el.tag) in ("ResZn", "ComZn")):
        zname = _zone_key(zn)
        if not zname:
            continue

        # Generate stable zone ID using registry
        zone_id = id_registry.generate_id("Z", zname, context="", source_format="CIBD22X")

        # Parse area (convert ft² to m²)
        zfa_ft2 = _to_float(_child_text_local(zn, "FloorArea") or _child_text_local(zn, "ZnFlrArea")
                            or _child_text_local(zn, "Area") or _child_text_local(zn, "GrossArea")
                            or zn.get("FloorArea") or zn.get("ZnFlrArea") or zn.get("Area") or zn.get("GrossArea"))
        zfa_m2 = (zfa_ft2 * 0.092903) if zfa_ft2 is not None else None
        if zfa_m2 is not None:
            have_area += 1

        # Parse volume (convert ft³ to m³)
        vol_ft3 = _to_float(_child_text_local(zn, "Volume") or zn.get("Volume"))
        vol_m3 = (vol_ft3 * 0.0283168) if vol_ft3 is not None else None

        # Multipliers
        z_mult = _read_zone_multiplier(zn)
        du_cnt = _read_du_count(zn) if _lt(zn.tag) == "ResZn" else 1
        eff_mult = int(z_mult) * int(du_cnt)
        du_ref = _du_ref_from_zone(zn) if _lt(zn.tag) == "ResZn" else None
        level_ref = (zone_to_group or {}).get(zname) or None

        tag_prefix = "ResZn" if _lt(zn.tag) == "ResZn" else "ComZn"
        mult_meta = {
            "effective": eff_mult,
            "factors": [
                {"name": "du_count_in_zone", "value": du_cnt,
                 "flat_path": f"{tag_prefix}/DwellUnit/Count"} if tag_prefix == "ResZn" else None,
                {"name": "zone_multiplier", "value": z_mult, "flat_path": f"{tag_prefix}/ZnMult|Mult|Count"},
            ],
            "base_quantity": 1,
            "applies_to": ["counts", "areas"],
        }
        mult_meta["factors"] = [f for f in mult_meta["factors"] if f is not None]

        # EMJSON v6 compliant zone structure
        zones.append({
            "id": zone_id,
            "name": zname,
            "building_type": "MF" if _lt(zn.tag) == "ResZn" else "NR",
            "multiplier": int(z_mult),
            "floor_area_m2": zfa_m2,
            "volume_m3": vol_m3,
            "stories_above": None,  # Could parse from StoryCount if available
            "du_ref": du_ref,
            "served_by": [],  # Populated by HVAC/DHW parsers
            "surfaces": [],  # Populated by parse_surfaces
            "annotation": {
                "xml_tag": _lt(zn.tag),
                "source_id": zn.get("id"),
                "source_area_units": "ft2" if zfa_ft2 is not None else None,
                "source_volume_units": "ft3" if vol_ft3 is not None else None,
                "multiplier_metadata": mult_meta
            }
        })

    _diag(em, "info", "I-ZONES-AREA-COVERAGE", f"{have_area}/{len(zones)} zones have floor_area")
    _diag(em, "info", "I-ZONES-PARSED", f"Parsed {len(zones)} zones", {"zone_count": len(zones)})
    return zones


# -------------------- surfaces --------------------
def parse_surfaces(
        root: ET.Element,
        em: Dict[str, Any],
        id_registry: Any  # IDRegistry instance
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Parse surfaces with proper zone references and stable IDs.
    - Converts areas ft² -> m²
    - Determines adjacency/boundary conditions
    - Links surfaces to parent zones
    """
    zones = em.get("geometry", {}).get("zones", [])
    zone_name_to_id = {z["name"]: z["id"] for z in zones}

    walls: List[Dict[str, Any]] = []
    roofs: List[Dict[str, Any]] = []
    floors: List[Dict[str, Any]] = []

    def _determine_adjacency(surf_elem: ET.Element) -> str:
        """Determine surface adjacency from BoundaryCondition or tag."""
        bc = _child_text_local(surf_elem, "BoundaryCondition") or surf_elem.get("BoundaryCondition")

        if bc:
            bc_lower = bc.lower()
            if "outdoor" in bc_lower or "exterior" in bc_lower:
                return "exterior"
            elif "ground" in bc_lower:
                return "ground"
            elif "adiabatic" in bc_lower:
                return "adiabatic"
            elif "adjacent" in bc_lower:
                # Parse adjacent zone reference
                adj_zone_ref = _child_text_local(surf_elem, "AdjacentZoneRef") or surf_elem.get("AdjacentZoneRef")
                if adj_zone_ref:
                    adj_zone_id = zone_name_to_id.get(adj_zone_ref)
                    if adj_zone_id:
                        return f"zone:{adj_zone_id}"
                return "adiabatic"

        # Fallback based on surface tag
        tag = _lt(surf_elem.tag).lower()
        if "party" in tag:
            return "adiabatic"
        elif "int" in tag or "interior" in tag:
            return "adiabatic"
        elif "underground" in tag:
            return "ground"

        return "exterior"

    def _parse_orientation(surf_elem: ET.Element) -> tuple[float | None, float | None]:
        """Parse tilt and azimuth from orientation or explicit fields."""
        # Try explicit tilt/azimuth first
        tilt = _to_float(_child_text_local(surf_elem, "Tilt") or surf_elem.get("Tilt"))
        azimuth = _to_float(_child_text_local(surf_elem, "Azimuth") or _child_text_local(surf_elem, "Az")
                            or surf_elem.get("Azimuth") or surf_elem.get("Az"))

        # Parse orientation string (e.g., "North", "South", etc.)
        if azimuth is None:
            orientation = (_child_text_local(surf_elem, "Orientation") or surf_elem.get("Orientation") or "").lower()
            orientation_map = {
                "north": 0.0, "n": 0.0,
                "northeast": 45.0, "ne": 45.0,
                "east": 90.0, "e": 90.0,
                "southeast": 135.0, "se": 135.0,
                "south": 180.0, "s": 180.0,
                "southwest": 225.0, "sw": 225.0,
                "west": 270.0, "w": 270.0,
                "northwest": 315.0, "nw": 315.0
            }
            azimuth = orientation_map.get(orientation)

        return tilt, azimuth

    def _default_tilt(category: str) -> float:
        """Get default tilt for surface category."""
        if category == "wall":
            return 90.0
        elif category == "roof":
            return 0.0  # Flat roof default
        elif category == "floor":
            return 180.0
        return 90.0

    # Iterate through zones and their surfaces
    for zn in (el for el in root.iter() if _lt(el.tag) in ("ResZn", "ComZn")):
        zname = _zone_key(zn)
        zone_id = zone_name_to_id.get(zname)

        if not zone_id:
            continue

        # Parse walls
        for tag in SURFACE_BUCKETS["walls"]:
            for surf_elem in zn.iterfind(f".//{tag}"):
                surf_name = _child_text_local(surf_elem, "Name") or surf_elem.get("Name") or tag

                # Generate stable surface ID
                surf_id = id_registry.generate_id("S", surf_name, context=zname, source_format="CIBD22X")

                # Parse area (convert ft² to m²)
                area_ft2 = _to_float(_child_text_local(surf_elem, "Area") or surf_elem.get("Area"))
                area_m2 = (area_ft2 * 0.092903) if area_ft2 is not None else None

                # Parse orientation
                tilt, azimuth = _parse_orientation(surf_elem)
                if tilt is None:
                    tilt = _default_tilt("wall")

                # Parse construction reference
                const_ref = (_child_text_local(surf_elem, "ConstructionRef") or _child_text_local(surf_elem, "ConsRef")
                             or surf_elem.get("ConstructionRef") or surf_elem.get("ConsRef"))

                surface = {
                    "id": surf_id,
                    "zone_id": zone_id,
                    "type": "wall",
                    "geometry_mode": "simplified",  # CIBD22X uses simplified geometry
                    "tilt_deg": tilt,
                    "azimuth_deg": azimuth,
                    "area_m2": area_m2,
                    "construction_ref": const_ref,
                    "adjacency": _determine_adjacency(surf_elem),
                    "openings": [],  # Populated by parse_openings
                    "annotation": {
                        "xml_tag": tag,
                        "source_id": surf_elem.get("id"),
                        "source_area_units": "ft2" if area_ft2 is not None else None
                    }
                }

                walls.append(surface)

                # Add surface ID to zone's surface list
                zone = next((z for z in zones if z["id"] == zone_id), None)
                if zone:
                    zone["surfaces"].append(surf_id)

        # Parse roofs
        for tag in SURFACE_BUCKETS["roofs"]:
            for surf_elem in zn.iterfind(f".//{tag}"):
                surf_name = _child_text_local(surf_elem, "Name") or surf_elem.get("Name") or tag
                surf_id = id_registry.generate_id("S", surf_name, context=zname, source_format="CIBD22X")

                area_ft2 = _to_float(_child_text_local(surf_elem, "Area") or surf_elem.get("Area"))
                area_m2 = (area_ft2 * 0.092903) if area_ft2 is not None else None

                tilt, azimuth = _parse_orientation(surf_elem)
                if tilt is None:
                    tilt = _default_tilt("roof")

                const_ref = (_child_text_local(surf_elem, "ConstructionRef") or _child_text_local(surf_elem, "ConsRef")
                             or surf_elem.get("ConstructionRef") or surf_elem.get("ConsRef"))

                surface = {
                    "id": surf_id,
                    "zone_id": zone_id,
                    "type": "roof",
                    "geometry_mode": "simplified",
                    "tilt_deg": tilt,
                    "azimuth_deg": azimuth,
                    "area_m2": area_m2,
                    "construction_ref": const_ref,
                    "adjacency": _determine_adjacency(surf_elem),
                    "openings": [],
                    "annotation": {
                        "xml_tag": tag,
                        "source_id": surf_elem.get("id"),
                        "source_area_units": "ft2" if area_ft2 is not None else None
                    }
                }

                roofs.append(surface)

                zone = next((z for z in zones if z["id"] == zone_id), None)
                if zone:
                    zone["surfaces"].append(surf_id)

        # Parse floors
        for tag in SURFACE_BUCKETS["floors"]:
            for surf_elem in zn.iterfind(f".//{tag}"):
                surf_name = _child_text_local(surf_elem, "Name") or surf_elem.get("Name") or tag
                surf_id = id_registry.generate_id("S", surf_name, context=zname, source_format="CIBD22X")

                area_ft2 = _to_float(_child_text_local(surf_elem, "Area") or surf_elem.get("Area"))
                area_m2 = (area_ft2 * 0.092903) if area_ft2 is not None else None

                tilt, azimuth = _parse_orientation(surf_elem)
                if tilt is None:
                    tilt = _default_tilt("floor")

                const_ref = (_child_text_local(surf_elem, "ConstructionRef") or _child_text_local(surf_elem, "ConsRef")
                             or surf_elem.get("ConstructionRef") or surf_elem.get("ConsRef"))

                surface = {
                    "id": surf_id,
                    "zone_id": zone_id,
                    "type": "floor" if "raised" in tag.lower() else "slab",
                    "geometry_mode": "simplified",
                    "tilt_deg": tilt,
                    "azimuth_deg": azimuth,
                    "area_m2": area_m2,
                    "construction_ref": const_ref,
                    "adjacency": _determine_adjacency(surf_elem),
                    "openings": [],
                    "annotation": {
                        "xml_tag": tag,
                        "source_id": surf_elem.get("id"),
                        "source_area_units": "ft2" if area_ft2 is not None else None
                    }
                }

                floors.append(surface)

                zone = next((z for z in zones if z["id"] == zone_id), None)
                if zone:
                    zone["surfaces"].append(surf_id)

    # Store in EMJSON structure
    em.setdefault("geometry", {}).setdefault("surfaces", {})["walls"] = walls
    em["geometry"]["surfaces"]["roofs"] = roofs
    em["geometry"]["surfaces"]["floors"] = floors

    _diag(em, "info", "I-SURF-COUNTS",
          f"walls={len(walls)}, roofs={len(roofs)}, floors={len(floors)}",
          {"walls": len(walls), "roofs": len(roofs), "floors": len(floors)})

    return {"walls": walls, "roofs": roofs, "floors": floors}


# -------------------- openings --------------------
def parse_openings(
        root: ET.Element,
        em: Dict[str, Any],
        id_registry: Any  # IDRegistry instance
) -> None:
    """
    Parse openings (windows, doors, skylights) with proper surface references.
    - Converts areas ft² -> m² and dimensions ft -> m
    - Links openings to parent surfaces
    - Extracts window type references
    """
    surfaces_dict = em.get("geometry", {}).get("surfaces", {})
    all_surfaces = (
            surfaces_dict.get("walls", []) +
            surfaces_dict.get("roofs", []) +
            surfaces_dict.get("floors", [])
    )

    # Build lookup: zone_id + surface element -> surface_id
    # We'll need to match surfaces by zone and name during iteration
    zones = em.get("geometry", {}).get("zones", [])
    zone_name_to_id = {z["name"]: z["id"] for z in zones}

    windows: List[Dict[str, Any]] = []
    doors: List[Dict[str, Any]] = []
    skylights: List[Dict[str, Any]] = []

    orphaned_openings = 0

    _SURF_TAGS = SURFACE_BUCKETS["walls"] + SURFACE_BUCKETS["roofs"] + SURFACE_BUCKETS["floors"]

    for zn in (el for el in root.iter() if _lt(el.tag) in ("ResZn", "ComZn")):
        zone_name = _zone_key(zn)
        zone_id = zone_name_to_id.get(zone_name)
        if not zone_id:
            continue

        # Find all surfaces in this zone
        for surf_tag in _SURF_TAGS:
            for surf_elem in zn.iterfind(f".//{surf_tag}"):
                surf_name = _child_text_local(surf_elem, "Name") or surf_elem.get("Name") or surf_tag

                # Find matching EMJSON surface by regenerating its ID
                surf_id = id_registry.generate_id("S", surf_name, context=zone_name, source_format="CIBD22X")

                # Verify this surface exists
                surf_obj = next((s for s in all_surfaces if s["id"] == surf_id), None)
                if not surf_obj:
                    _diag(em, "warn", "W-SURFACE-NOT-FOUND",
                          f"Could not find surface {surf_name} in zone {zone_name} for openings")
                    continue

                # Find openings under this surface
                for opening_elem in surf_elem.iterfind(".//*"):
                    otag = _lt(opening_elem.tag).lower()

                    if otag not in ("reswin", "comwin", "window", "door", "skylight"):
                        continue

                    oname = _child_text_local(opening_elem, "Name") or opening_elem.get("Name") or "opening"

                    # Generate stable opening ID
                    opening_id = id_registry.generate_id(
                        "O",
                        oname,
                        context=f"{zone_name}:{surf_name}",
                        source_format="CIBD22X"
                    )

                    # Parse dimensions and area
                    area_ft2 = _to_float(_child_text_local(opening_elem, "Area") or opening_elem.get("Area"))
                    height_ft = _to_float(
                        _child_text_local(opening_elem, "Height") or _child_text_local(opening_elem, "Hgt")
                        or opening_elem.get("Height") or opening_elem.get("Hgt"))
                    width_ft = _to_float(
                        _child_text_local(opening_elem, "Width") or _child_text_local(opening_elem, "Wdth")
                        or opening_elem.get("Width") or opening_elem.get("Wdth"))

                    # Convert to metric
                    area_m2 = (area_ft2 * 0.092903) if area_ft2 is not None else None
                    height_m = (height_ft * 0.3048) if height_ft is not None else None
                    width_m = (width_ft * 0.3048) if width_ft is not None else None

                    # Parse window type reference
                    win_type_ref = (_child_text_local(opening_elem, "WindowTypeRef") or _child_text_local(opening_elem,
                                                                                                          "TypeRef")
                                    or opening_elem.get("WindowTypeRef") or opening_elem.get("TypeRef"))

                    # Parse fenestration properties if directly specified
                    u_factor = _to_float(_child_text_local(opening_elem, "UFactor") or opening_elem.get("UFactor"))
                    shgc = _to_float(_child_text_local(opening_elem, "SHGC") or opening_elem.get("SHGC"))
                    vt = _to_float(
                        _child_text_local(opening_elem, "VT") or _child_text_local(opening_elem, "VisibleTransmittance")
                        or opening_elem.get("VT") or opening_elem.get("VisibleTransmittance"))

                    # Convert U-factor from IP to SI if present (Btu/h·ft²·°F to W/m²·K)
                    u_factor_si = (u_factor * 5.678263) if u_factor is not None else None

                    # Parse frame type
                    frame_type = (
                                _child_text_local(opening_elem, "FrameType") or _child_text_local(opening_elem, "Frame")
                                or opening_elem.get("FrameType") or opening_elem.get("Frame"))

                    # Determine opening type
                    opening_type = "window"
                    if "door" in otag:
                        opening_type = "door"
                    elif "skylight" in otag or "sky" in otag:
                        opening_type = "skylight"

                    opening = {
                        "id": opening_id,
                        "parent_surface_id": surf_id,
                        "type": opening_type,
                        "area_m2": area_m2,
                        "height_m": height_m,
                        "width_m": width_m,
                        "tilt_deg": None,  # Could be derived from parent surface
                        "azimuth_deg": None,  # Could be derived from parent surface
                        "window_type_ref": win_type_ref,
                        "frame_type": frame_type,
                        "u_factor_SI": u_factor_si,
                        "shgc": shgc,
                        "vt": vt,
                        "annotation": {
                            "xml_tag": _lt(opening_elem.tag),
"source_id": opening_elem.get("id"),
"source_area_units": "ft2" if area_ft2 is not None else None,
"source_dimension_units": "ft" if (height_ft is not None or width_ft is not None) else None
}
}
                    # Add to appropriate list
                    if opening_type == "window":
                        windows.append(opening)
                    elif opening_type == "door":
                        doors.append(opening)
                    elif opening_type == "skylight":
                        skylights.append(opening)

                    # Add opening ID to surface's openings list
                    surf_obj["openings"].append(opening_id)

                # Store in EMJSON structure
                em.setdefault("geometry", {}).setdefault("openings", {})["windows"] = windows
                em["geometry"]["openings"]["doors"] = doors
                em["geometry"]["openings"]["skylights"] = skylights

                _diag(em, "info", "I-OPENINGS-PARSED",
                      f"windows={len(windows)}, doors={len(doors)}, skylights={len(skylights)}",
                      {"windows": len(windows), "doors": len(doors), "skylights": len(skylights)})

                if orphaned_openings > 0:
                    _diag(em, "warn", "W-OPENINGS-ORPHANED",
                          f"{orphaned_openings} openings could not be linked to surfaces")