# FILE: em-tools/emtools/translators/cibd22_importer.py
# ============================================================================
"""
CIBD22 Text to EMJSON v6 Translator

Main orchestrator for converting CIBD22 text format to EMJSON v6.
CIBD22 uses a proprietary text-based format with indentation, different from
the XML-based CIBD22X format.

Key differences from CIBD22X:
- Text format with indentation vs XML
- ResExtWall, ResWin vs ExtWall, Window
- ResWinType, ResConsAssm vs WindowType, ConstructionType
- Properties embedded in objects vs separate catalogs
"""

from __future__ import annotations
from typing import Dict, Any, List
import sys

from emtools.parsers.cibd22_text_parser import parse_cibd22_file
from emtools.utils.id_registry import IDRegistry

VERSION = "6.0"


def _to_float(val: Any, default: float = 0.0) -> float:
    """Safe float conversion."""
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def _parse_project_and_location(parser, em: Dict[str, Any], id_registry: IDRegistry) -> None:
    """Parse project info and location from Proj and Bldg objects."""
    proj_objs = parser.find_objects(obj_type="Proj")
    bldg_objs = parser.find_objects(obj_type="Bldg")
    
    if proj_objs:
        proj = proj_objs[0]
        props = proj.get("_properties", {})
        
        em["project"]["model_info"].update({
            "project_name": proj.get("_name"),
            "software_version": props.get("SoftwareVersion", ""),
            "geometry_input_type": props.get("GeometryInpType", ""),
        })
        
        # Location info from Proj
        if props.get("City"):
            em["project"]["location"]["city"] = props["City"]
        if props.get("ZipCode"):
            em["project"]["location"]["zip"] = str(props["ZipCode"])
    
    if bldg_objs:
        bldg = bldg_objs[0]
        props = bldg.get("_properties", {})
        
        if props.get("BldgAz"):
            em["project"]["location"]["building_azimuth_deg"] = _to_float(props["BldgAz"])


def _parse_du_types(parser, em: Dict[str, Any], id_registry: IDRegistry) -> Dict[str, str]:
    """Parse DwellUnitType catalog objects."""
    du_types = parser.find_objects(obj_type="DwellUnitType")
    du_list = []
    du_name_to_id = {}
    
    for du in du_types:
        name = du.get("_name", "DU")
        props = du.get("_properties", {})
        
        # Generate stable ID
        du_id = id_registry.generate_id("DU", name, context="", source_format="CIBD22")
        du_name_to_id[name] = du_id
        
        # Convert CondFlrArea from ft² to m²
        floor_area_ft2 = _to_float(props.get("CondFlrArea"))
        floor_area_m2 = floor_area_ft2 * 0.092903 if floor_area_ft2 > 0 else None
        
        item = {
            "id": du_id,
            "name": name,
            "floor_area_m2": floor_area_m2,
            "bedrooms": int(props.get("NumBedrooms", 0)) if props.get("NumBedrooms") else None,
            "annotation": {
                "source_format": "CIBD22",
                "source_name": name,
                "source_area_units": "ft2" if floor_area_ft2 else None,
            }
        }
        
        du_list.append(item)
    
    em["catalogs"]["du_types"] = du_list
    
    if du_list:
        em["diagnostics"].append({
            "level": "info",
            "code": "I-DU-TYPES-PARSED",
            "message": f"Parsed {len(du_list)} dwelling unit types"
        })
    
    return du_name_to_id


def _parse_window_types(parser, em: Dict[str, Any], id_registry: IDRegistry) -> Dict[str, str]:
    """Parse ResWinType catalog objects."""
    win_types = parser.find_objects(obj_type="ResWinType")
    wt_list = []
    wt_name_to_id = {}
    
    for wt in win_types:
        name = wt.get("_name", "WindowType")
        props = wt.get("_properties", {})
        
        # Generate stable ID
        wt_id = id_registry.generate_id("WIN", name, context="", source_format="CIBD22")
        wt_name_to_id[name] = wt_id
        
        item = {
            "id": wt_id,
            "name": name,
            "u_factor_btu_ft2_f": _to_float(props.get("NFRCUfactor")) if props.get("NFRCUfactor") else None,
            "shgc": _to_float(props.get("NFRCSHGC")) if props.get("NFRCSHGC") else None,
            "vt": _to_float(props.get("NFRCVT")) if props.get("NFRCVT") else None,
            "annotation": {
                "source_format": "CIBD22",
                "source_name": name,
            }
        }
        
        wt_list.append(item)
    
    em["catalogs"]["window_types"] = wt_list
    
    if wt_list:
        em["diagnostics"].append({
            "level": "info",
            "code": "I-WIN-TYPES-PARSED",
            "message": f"Parsed {len(wt_list)} window types"
        })
    
    return wt_name_to_id


def _parse_construction_types(parser, em: Dict[str, Any], id_registry: IDRegistry) -> Dict[str, str]:
    """Parse ResConsAssm catalog objects."""
    cons_types = parser.find_objects(obj_type="ResConsAssm")
    ct_list = []
    ct_name_to_id = {}
    
    for ct in cons_types:
        name = ct.get("_name", "Construction")
        props = ct.get("_properties", {})
        
        # Generate stable ID
        ct_id = id_registry.generate_id("CONS", name, context="", source_format="CIBD22")
        ct_name_to_id[name] = ct_id
        
        item = {
            "id": ct_id,
            "name": name,
            "u_value_btu_ft2_f": _to_float(props.get("UValue")) if props.get("UValue") else None,
            "annotation": {
                "source_format": "CIBD22",
                "source_name": name,
            }
        }
        
        ct_list.append(item)
    
    em["catalogs"]["construction_types"] = ct_list
    
    if ct_list:
        em["diagnostics"].append({
            "level": "info",
            "code": "I-CONS-TYPES-PARSED",
            "message": f"Parsed {len(ct_list)} construction types"
        })
    
    return ct_name_to_id


def _parse_materials(parser, em: Dict[str, Any], id_registry: IDRegistry) -> Dict[str, str]:
    """Parse ResMat and Mat catalog objects (materials library)."""
    res_mats = parser.find_objects(obj_type="ResMat")
    gen_mats = parser.find_objects(obj_type="Mat")
    all_mats = res_mats + gen_mats
    mat_list = []
    mat_name_to_id = {}
    
    for mat in all_mats:
        name = mat.get("_name", "Material")
        props = mat.get("_properties", {})
        mat_type = mat.get("_type", "Mat")
        
        # Generate stable ID
        mat_id = id_registry.generate_id("MAT", name, context="", source_format="CIBD22")
        mat_name_to_id[name] = mat_id
        
        # Parse thermal properties
        # Conductivity: Btu-in/hr-ft²-F → W/m-K conversion
        conductivity_btuin = _to_float(props.get("Conductivity"))
        conductivity_w_mk = None
        if conductivity_btuin and conductivity_btuin > 0:
            # Btu-in/hr-ft²-F × 0.14413 = W/m-K
            conductivity_w_mk = conductivity_btuin * 0.14413
        
        # Density: lb/ft³ → kg/m³ conversion
        density_lbft3 = _to_float(props.get("Density"))
        density_kg_m3 = None
        if density_lbft3 and density_lbft3 > 0:
            # lb/ft³ × 16.0185 = kg/m³
            density_kg_m3 = density_lbft3 * 16.0185
        
        # Specific heat: Btu/lb-F → J/kg-K conversion
        specheat_btu = _to_float(props.get("SpecHeat"))
        specheat_j_kgk = None
        if specheat_btu and specheat_btu > 0:
            # Btu/lb-F × 4186.8 = J/kg-K
            specheat_j_kgk = specheat_btu * 4186.8
        
        item = {
            "id": mat_id,
            "name": name,
            "conductivity_w_mk": conductivity_w_mk,
            "density_kg_m3": density_kg_m3,
            "specific_heat_j_kgk": specheat_j_kgk,
            "thickness_m": _to_float(props.get("Thickness")) * 0.0254 if props.get("Thickness") else None,  # inches to meters
            "annotation": {
                "source_format": "CIBD22",
                "source_name": name,
                "source_type": mat_type,
                "source_units": {
                    "conductivity": "Btu-in/hr-ft2-F",
                    "density": "lb/ft3",
                    "specific_heat": "Btu/lb-F",
                    "thickness": "inches"
                }
            }
        }
        
        mat_list.append(item)
    
    # Add to catalogs under materials key
    if "materials" not in em["catalogs"]:
        em["catalogs"]["materials"] = []
    em["catalogs"]["materials"] = mat_list
    
    if mat_list:
        em["diagnostics"].append({
            "level": "info",
            "code": "I-MATERIALS-PARSED",
            "message": f"Parsed {len(mat_list)} material types"
        })
    
    return mat_name_to_id


def _parse_zones(parser, em: Dict[str, Any], id_registry: IDRegistry, 
                 du_name_to_id: Dict[str, str]) -> Dict[str, str]:
    """Parse Spc (Space), ResZn, ResOtherZn, and ThrmlZn (Thermal Zone) objects with enhanced field coverage."""
    # CIBD22 uses multiple zone object types:
    # - Spc: Commercial/residential spaces
    # - ResZn: Residential zones (dwelling units)
    # - ResOtherZn: Unconditioned/other zones
    # - ThrmlZn: Thermal zone metadata (referenced by others)
    spaces = parser.find_objects(obj_type="Spc")
    res_zones = parser.find_objects(obj_type="ResZn")
    other_zones = parser.find_objects(obj_type="ResOtherZn")
    thermal_zones = parser.find_objects(obj_type="ThrmlZn")
    
    # Build thermal zone lookup by name for reference resolution
    thrml_zn_by_name = {}
    for tz in thermal_zones:
        tz_name = tz.get("_name", "")
        thrml_zn_by_name[tz_name] = tz
    
    # Combine all zone objects (all have geometry)
    zones = spaces + res_zones + other_zones
    zone_list = []
    zone_name_to_id = {}
    
    # Build DU type lookup for floor area fallback
    du_id_to_data = {}
    for du_type in em.get("catalogs", {}).get("du_types", []):
        du_id_to_data[du_type["id"]] = du_type
    
    zones_with_du_fallback = 0
    
    for zn in zones:
        name = zn.get("_name", "Zone")
        props = zn.get("_properties", {})
        
        # Generate stable ID
        zone_id = id_registry.generate_id("Z", name, context="", source_format="CIBD22")
        zone_name_to_id[name] = zone_id
        
        # Resolve ThrmlZnRef to get zone type and HVAC info
        thrml_zn_ref = props.get("ThrmlZnRef")
        zone_type = "Conditioned"  # Default
        hvac_system_refs = []
        
        if thrml_zn_ref and thrml_zn_ref in thrml_zn_by_name:
            tz = thrml_zn_by_name[thrml_zn_ref]
            tz_props = tz.get("_properties", {})
            zone_type = tz_props.get("Type", "Conditioned")
            
            # Extract HVAC system references
            for key, val in tz_props.items():
                if "AirCondgSysRef" in key or "ExhSysRef" in key:
                    if isinstance(val, dict):  # Array property
                        hvac_system_refs.extend(val.values())
                    else:
                        hvac_system_refs.append(val)
        
        # Parse volume (ft³ to m³)
        volume_ft3 = _to_float(props.get("Vol")) if props.get("Vol") else None
        volume_m3 = volume_ft3 * 0.0283168 if volume_ft3 and volume_ft3 > 0 else None
        
        # Parse DwellUnit reference (for multifamily projects)
        du_ref = None
        du_count = 1
        children = zn.get("_children", [])
        for child in children:
            if child.get("_type") == "DwellUnit":
                child_props = child.get("_properties", {})
                du_type_ref = child_props.get("DwellUnitTypeRef")
                if du_type_ref and du_type_ref in du_name_to_id:
                    du_ref = du_name_to_id[du_type_ref]
                # Parse DU count if present
                if child_props.get("Count"):
                    du_count = int(_to_float(child_props["Count"]))
                break
        
        # Floor area and height - may not be directly on Spc object
        # These are typically derived from geometry (surfaces)
        floor_area_m2 = None
        ceiling_height_m = None
        floor_height_m = None
        area_source = "geometry_derived"
        
        # Fallback to DU type floor area if available
        if du_ref and du_ref in du_id_to_data:
            du_data = du_id_to_data[du_ref]
            if du_data.get("floor_area_m2"):
                floor_area_m2 = du_data["floor_area_m2"]
                area_source = "du_type_reference"
                zones_with_du_fallback += 1
        
        # Parse number of stories if present
        num_stories = int(_to_float(props.get("NumStories"))) if props.get("NumStories") else None
        
        item = {
            "id": zone_id,
            "name": name,
            "building_type": "MF" if du_ref else "NR",
            "zone_type": zone_type,
            "multiplier": 1,  # CIBD22 uses zone groups differently
            "du_ref": du_ref,
            "du_count": du_count,
            "floor_area_m2": floor_area_m2,
            "ceiling_height_m": ceiling_height_m,
            "floor_height_m": floor_height_m,
            "volume_m3": volume_m3,
            "num_stories": num_stories,
            "served_by": [],
            "surfaces": [],
            "annotation": {
                "source_format": "CIBD22",
                "source_name": name,
                "source_area_units": "ft2",
                "source_height_units": "ft",
                "floor_area_source": area_source,
            }
        }
        
        zone_list.append(item)
    
    em["geometry"]["zones"] = zone_list
    
    if zone_list:
        em["diagnostics"].append({
            "level": "info",
            "code": "I-ZONES-PARSED",
            "message": f"Parsed {len(zone_list)} zones ({zones_with_du_fallback} used DU type floor area)",
            "context": {
                "zone_count": len(zone_list),
                "zones_with_du_fallback": zones_with_du_fallback
            }
        })
    
    return zone_name_to_id


def _parse_surfaces(parser, em: Dict[str, Any], id_registry: IDRegistry,
                   zone_name_to_id: Dict[str, str], cons_name_to_id: Dict[str, str]) -> None:
    """Parse ResExtWall, Roof, ResSlabFlr objects with robust heuristic resolution."""
    from emtools.parsers.cibd22_name_resolver import CIBD22NameResolver
    
    resolver = CIBD22NameResolver(em["diagnostics"])
    surfaces = {
        "walls": [],
        "roofs": [],
        "floors": []
    }
    
    # Map object types to surface buckets
    type_to_bucket = {
        "ResExtWall": "walls",
        "ResIntWall": "walls",  # Interior walls
        "ComIntWall": "walls",  # Commercial interior walls
        "Roof": "roofs",
        "ResSlabFlr": "floors",
        "ResExtFlr": "floors",
        "ResFlrSeg": "floors",  # Floor segments
        "ComFlrSeg": "floors",  # Commercial floor segments
        "ResCeilg": "roofs",    # Interior ceilings (treated as roofs)
        "ComCeilg": "roofs"     # Commercial ceilings
    }
    
    # Identify interior surface types (have adjacency)
    interior_types = {"ResIntWall", "ComIntWall", "ResIntFlr", "ResFlrSeg", "ComFlrSeg", "ResCeilg", "ComCeilg"}
    
    low_confidence_count = 0
    adjacency_resolved_count = 0
    
    for obj_type, bucket in type_to_bucket.items():
        surf_objs = parser.find_objects(obj_type=obj_type)
        
        for surf in surf_objs:
            name = surf.get("_name", "Surface")
            props = surf.get("_properties", {})
            
            # Use explicit resolver with confidence tracking
            result = resolver.resolve_zone_from_name(name, zone_name_to_id)
            zone_id = result.resolved_id
            
            # Track low confidence resolutions
            if result.confidence < 0.8:
                low_confidence_count += 1
                if result.confidence < 0.5:
                    em["diagnostics"].append({
                        "level": "warning",
                        "code": "W-SURF-RESOLUTION-LOW-CONFIDENCE",
                        "message": f"Low confidence zone resolution for surface: {name}",
                        "context": {
                            "surface_name": name,
                            "confidence": result.confidence,
                            "strategy": result.strategy_used,
                            "warnings": result.warnings
                        }
                    })
            
            # Generate stable ID
            surf_id = id_registry.generate_id("S", name, context=zone_id or "", source_format="CIBD22")
            
            # Convert area from ft² to m²
            area_ft2 = _to_float(props.get("Area"))
            area_m2 = area_ft2 * 0.092903 if area_ft2 > 0 else None
            
            # Resolve construction reference
            cons_ref = props.get("Construction")
            cons_id = cons_name_to_id.get(cons_ref) if cons_ref else None
            
            # Parse adjacent zone for interior surfaces
            adjacent_zone_id = None
            if obj_type in interior_types:
                outside_ref = props.get("Outside")
                if outside_ref:
                    # Outside can be zone name or special values like "Ambient", "Ground"
                    if outside_ref in zone_name_to_id:
                        adjacent_zone_id = zone_name_to_id[outside_ref]
                        adjacency_resolved_count += 1
                    elif outside_ref not in ["Ambient", "Ground", "Adiabatic"]:
                        # Unknown zone reference
                        em["diagnostics"].append({
                            "level": "warning",
                            "code": "W-SURF-ADJACENCY-UNKNOWN",
                            "message": f"Interior surface references unknown adjacent zone: {outside_ref}",
                            "context": {
                                "surface_name": name,
                                "outside_ref": outside_ref
                            }
                        })
            
            item = {
                "id": surf_id,
                "zone_id": zone_id,
                "area_m2": area_m2,
                "construction_ref": cons_id,
                "adjacent_zone_id": adjacent_zone_id,
                "surface_type": "interior" if obj_type in interior_types else "exterior",
                "openings": [],  # Populated by _parse_openings
                "annotation": {
                    "source_format": "CIBD22",
                    "source_name": name,
                    "source_area_units": "ft2" if area_ft2 else None,
                    "orientation": props.get("Orientation"),
                    "outside_ref": props.get("Outside") if obj_type in interior_types else None,
                    "zone_resolution": {
                        "confidence": result.confidence,
                        "strategy": result.strategy_used
                    }
                }
            }
            
            surfaces[bucket].append(item)
    
    em["geometry"]["surfaces"] = surfaces
    
    total_surfs = sum(len(v) for v in surfaces.values())
    if total_surfs > 0:
        em["diagnostics"].append({
            "level": "info",
            "code": "I-SURFACES-PARSED",
            "message": f"Parsed {total_surfs} surfaces ({low_confidence_count} with confidence < 0.8, {adjacency_resolved_count} with adjacency)",
            "context": {
                "low_confidence_count": low_confidence_count,
                "adjacency_resolved_count": adjacency_resolved_count
            }
        })


def _parse_openings(parser, em: Dict[str, Any], id_registry: IDRegistry,
                   wt_name_to_id: Dict[str, str]) -> None:
    """Parse ResWin, Door, Skylight objects with robust heuristic resolution."""
    from emtools.parsers.cibd22_name_resolver import CIBD22NameResolver
    
    resolver = CIBD22NameResolver(em["diagnostics"])
    openings = {
        "windows": [],
        "doors": [],
        "skylights": []
    }
    
    type_to_bucket = {
        "ResWin": "windows",
        "Door": "doors",
        "ResDoor": "doors",  # Residential doors
        "Skylight": "skylights"
    }
    
    # Build surface lookup by name for parent resolution
    surf_name_to_id = {}
    for bucket, surfs in em["geometry"]["surfaces"].items():
        for surf in surfs:
            src_name = surf.get("annotation", {}).get("source_name")
            if src_name:
                surf_name_to_id[src_name] = surf["id"]
    
    low_confidence_count = 0
    orphan_count = 0
    
    for obj_type, bucket in type_to_bucket.items():
        opening_objs = parser.find_objects(obj_type=obj_type)
        
        for opening in opening_objs:
            name = opening.get("_name", "Opening")
            props = opening.get("_properties", {})
            
            # Use explicit resolver with confidence tracking
            result = resolver.resolve_surface_from_opening(name, surf_name_to_id)
            parent_surf_id = result.resolved_id
            
            # Track resolution quality
            if result.confidence < 0.8:
                low_confidence_count += 1
            if parent_surf_id is None:
                orphan_count += 1
                em["diagnostics"].append({
                    "level": "warning",
                    "code": "W-OPENING-NO-PARENT",
                    "message": f"Opening has no parent surface: {name}",
                    "context": {
                        "opening_name": name,
                        "warnings": result.warnings
                    }
                })
            
            # Generate stable ID
            opening_id = id_registry.generate_id("O", name, context=parent_surf_id or "", 
                                                 source_format="CIBD22")
            
            # Convert dimensions from ft to m, area from ft² to m²
            area_ft2 = _to_float(props.get("Area"))
            area_m2 = area_ft2 * 0.092903 if area_ft2 > 0 else None
            
            height_ft = _to_float(props.get("Height"))
            height_m = height_ft * 0.3048 if height_ft > 0 else None
            
            width_ft = _to_float(props.get("Width"))
            width_m = width_ft * 0.3048 if width_ft > 0 else None
            
            # Resolve window type reference
            wt_ref = props.get("WinType")
            wt_id = wt_name_to_id.get(wt_ref) if wt_ref else None
            
            item = {
                "id": opening_id,
                "parent_surface_id": parent_surf_id,
                "area_m2": area_m2,
                "height_m": height_m,
                "width_m": width_m,
                "window_type_ref": wt_id if bucket == "windows" else None,
                "annotation": {
                    "source_format": "CIBD22",
                    "source_name": name,
                    "source_area_units": "ft2" if area_ft2 else None,
                    "surface_resolution": {
                        "confidence": result.confidence,
                        "strategy": result.strategy_used
                    }
                }
            }
            
            openings[bucket].append(item)
            
            # Add to parent surface's openings list
            if parent_surf_id:
                for surfs in em["geometry"]["surfaces"].values():
                    for surf in surfs:
                        if surf["id"] == parent_surf_id:
                            surf["openings"].append(opening_id)
    
    em["geometry"]["openings"] = openings
    
    total_openings = sum(len(v) for v in openings.values())
    if total_openings > 0:
        em["diagnostics"].append({
            "level": "info",
            "code": "I-OPENINGS-PARSED",
            "message": f"Parsed {total_openings} openings ({low_confidence_count} with confidence < 0.8, {orphan_count} orphaned)",
            "context": {
                "low_confidence_count": low_confidence_count,
                "orphan_count": orphan_count
            }
        })


def _parse_hvac_systems(parser, em: Dict[str, Any], id_registry: IDRegistry) -> None:
    """Parse ResHVACSys objects (basic implementation)."""
    hvac_objs = parser.find_objects(obj_type="ResHVACSys")
    hvac_list = []
    
    for hvac in hvac_objs:
        name = hvac.get("_name", "HVAC")
        props = hvac.get("_properties", {})
        
        # Generate stable ID
        hvac_id = id_registry.generate_id("HVAC", name, context="", source_format="CIBD22")
        
        item = {
            "id": hvac_id,
            "name": name,
            "type": props.get("Type", "unknown"),
            "fuel": props.get("FuelType"),
            "efficiency": _to_float(props.get("HSPF")) if props.get("HSPF") else None,
            "capacity_btu_h": _to_float(props.get("CapRtd")),
            "zone_refs": [],  # Would need zone linking logic
            "annotation": {
                "source_format": "CIBD22",
                "source_name": name,
            }
        }
        
        hvac_list.append(item)
    
    em["systems"]["hvac"] = hvac_list
    
    if hvac_list:
        em["diagnostics"].append({
            "level": "info",
            "code": "I-HVAC-PARSED",
            "message": f"Parsed {len(hvac_list)} HVAC systems (basic)",
            "context": {"hvac_count": len(hvac_list)}
        })


def _parse_dhw_systems(parser, em: Dict[str, Any], id_registry: IDRegistry) -> None:
    """Parse ResWtrHtr objects (basic implementation)."""
    dhw_objs = parser.find_objects(obj_type="ResWtrHtr")
    dhw_list = []
    
    for dhw in dhw_objs:
        name = dhw.get("_name", "DHW")
        props = dhw.get("_properties", {})
        
        # Generate stable ID
        dhw_id = id_registry.generate_id("DHW", name, context="", source_format="CIBD22")
        
        item = {
            "id": dhw_id,
            "name": name,
            "type": props.get("Type", "unknown"),
            "fuel": props.get("FuelType"),
            "energy_factor": _to_float(props.get("EnergyFactor")),
            "capacity_gal": _to_float(props.get("TankVol")),
            "annotation": {
                "source_format": "CIBD22",
                "source_name": name,
            }
        }
        
        dhw_list.append(item)
    
    em["systems"]["dhw"] = dhw_list
    
    if dhw_list:
        em["diagnostics"].append({
            "level": "info",
            "code": "I-DHW-PARSED",
            "message": f"Parsed {len(dhw_list)} DHW systems (basic)",
            "context": {"dhw_count": len(dhw_list)}
        })


def translate_cibd22_to_v6(file_path: str) -> Dict[str, Any]:
    """
    Translate CIBD22 text format to EMJSON v6.
    
    Args:
        file_path: Path to CIBD22 file
        
    Returns:
        EMJSON v6 dictionary with full schema compliance
        
    Example:
        >>> emjson = translate_cibd22_to_v6("model.cibd22")
        >>> print(f"Zones: {len(emjson['geometry']['zones'])}")
    """
    # Parse CIBD22 text format
    parser = parse_cibd22_file(file_path)
    
    # Initialize EMJSON v6 structure
    em: Dict[str, Any] = {
        "schema_version": VERSION,
        "project": {
            "model_info": {
                "source_format": "CIBD22",
                "source_version": "unknown",
                "translator_version": VERSION
            },
            "location": {}
        },
        "geometry": {
            "zones": [],
            "surfaces": {
                "walls": [],
                "roofs": [],
                "floors": []
            },
            "openings": {
                "windows": [],
                "doors": [],
                "skylights": []
            }
        },
        "catalogs": {
            "window_types": [],
            "construction_types": [],
            "du_types": []
        },
        "systems": {
            "hvac": [],
            "dhw": [],
            "pv": []
        },
        "energy": {
            "schedules": [],
            "loads": []
        },
        "results": {},
        "diagnostics": []
    }
    
    # Create ID registry for stable IDs
    id_registry = IDRegistry()
    
    # Parse in order: catalogs first, then geometry, then systems
    _parse_project_and_location(parser, em, id_registry)
    du_name_to_id = _parse_du_types(parser, em, id_registry)
    wt_name_to_id = _parse_window_types(parser, em, id_registry)
    cons_name_to_id = _parse_construction_types(parser, em, id_registry)
    mat_name_to_id = _parse_materials(parser, em, id_registry)
    
    zone_name_to_id = _parse_zones(parser, em, id_registry, du_name_to_id)
    _parse_surfaces(parser, em, id_registry, zone_name_to_id, cons_name_to_id)
    _parse_openings(parser, em, id_registry, wt_name_to_id)
    
    # Parse systems
    _parse_hvac_systems(parser, em, id_registry)
    _parse_dhw_systems(parser, em, id_registry)
    
    # Store ID registry in metadata
    em["_metadata"] = {
        "id_registry": id_registry.export_registry(),
        "translator_version": VERSION,
        "source_format": "CIBD22",
        "source_file": file_path
    }
    
    # Summary diagnostic
    materials_count = len(em['catalogs'].get('materials', []))
    em["diagnostics"].append({
        "level": "info",
        "code": "I-TRANSLATION-COMPLETE",
        "message": f"Translation complete: {len(em['geometry']['zones'])} zones, "
                   f"{sum(len(v) for v in em['geometry']['surfaces'].values())} surfaces, "
                   f"{sum(len(v) for v in em['geometry']['openings'].values())} openings, "
                   f"{materials_count} materials",
        "context": {
            "zones": len(em['geometry']['zones']),
            "surfaces": sum(len(v) for v in em['geometry']['surfaces'].values()),
            "openings": sum(len(v) for v in em['geometry']['openings'].values()),
            "materials": materials_count
        }
    })
    
    return em


def main(argv=None):
    """Command-line interface for translator."""
    import json
    
    argv = argv or sys.argv[1:]
    if not argv:
        print("Usage: python -m emtools.translators.cibd22_importer <input.cibd22> [output.emjson]")
        return 2
    
    out = argv[1] if len(argv) > 1 else argv[0].rsplit('.', 1)[0] + ".emjson"
    em = translate_cibd22_to_v6(argv[0])
    
    with open(out, "w", encoding="utf-8") as f:
        json.dump(em, f, indent=2)
    
    print(f"✓ Wrote {out}")
    print(f"  - {len(em['geometry']['zones'])} zones")
    print(f"  - {sum(len(v) for v in em['geometry']['surfaces'].values())} surfaces")
    print(f"  - {sum(len(v) for v in em['geometry']['openings'].values())} openings")
    print(f"  - {len(em['diagnostics'])} diagnostics")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
